"""
Auto-fix Lambda — triggered by CloudWatch alarm.
Reads the error logs, calls Claude API to diagnose, creates a PR on GitHub.
"""

import base64
import json
import logging
import os
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = "allierays/fintechco"
LOG_GROUP = "/aws/lambda/fintechco-sync"


def handler(event, context):
    logger.info("auto_fix triggered: %s", json.dumps(event, default=str))

    # Step 1: Read recent errors from CloudWatch
    errors = get_cloudwatch_errors()
    if not errors:
        logger.info("No errors found, exiting")
        return {"status": "no_errors"}

    logger.info("Found %d error(s), fetching source code", len(errors))

    # Step 2: Fetch current router.py from GitHub
    source_code = github_get_file("src/routing/router.py")

    # Step 3: Fetch current tests from GitHub
    existing_tests = github_get_file("tests/test_router.py")

    # Step 4: Call Claude API to diagnose and fix
    fix = call_claude_fix(errors, source_code)

    # Step 5: Call Claude API to write a regression test
    regression_test = call_claude_regression_test(errors, source_code, fix, existing_tests)

    # Step 6: Call Claude API to write a clear PR description
    pr_body = call_claude_pr_description(errors, source_code, fix)

    # Step 7: Create branch, commit fix + test, open PR
    pr_url = create_pr(fix, regression_test, pr_body)

    logger.info("PR created: %s", pr_url)
    return {"status": "pr_created", "pr_url": pr_url}


def get_cloudwatch_errors():
    """Read recent errors from CloudWatch using boto3."""
    import boto3
    import time

    client = boto3.client("logs", region_name="us-east-1")
    now = int(time.time() * 1000)
    start = now - (24 * 60 * 60 * 1000)  # last 24 hours

    resp = client.filter_log_events(
        logGroupName=LOG_GROUP,
        startTime=start,
        endTime=now,
        filterPattern="ERROR",
        limit=10,
    )
    return [e["message"] for e in resp.get("events", [])]


def github_get_file(path):
    """Fetch a file from the GitHub repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    return base64.b64decode(data["content"]).decode("utf-8")


def _claude_request(prompt, max_tokens=2048):
    """Make a Claude API request and return the text response."""
    body = json.dumps({
        "model": "claude-3-haiku-20240307",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        resp = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error("Claude API error %d: %s", e.code, error_body)
        raise RuntimeError(f"Claude API {e.code}: {error_body}")
    data = json.loads(resp.read())
    return data["content"][0]["text"]


def call_claude_fix(errors, source_code):
    """Call Claude API to diagnose the error and return fixed code."""
    error_text = "\n".join(errors)
    prompt = f"""CloudWatch errors from our payment routing service:

{error_text}

Current source code of src/routing/router.py:

```python
{source_code}
```

Diagnose the root cause and return ONLY the fixed version of the entire file.
Return the code inside ```python``` markers, nothing else."""

    text = _claude_request(prompt)
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    return text.strip()


def call_claude_regression_test(errors, source_code, fixed_code, existing_tests):
    """Call Claude API to write a regression test for the fix."""
    error_text = "\n".join(errors)
    prompt = f"""A bug was found and fixed in our payment routing system.

CloudWatch errors:
{error_text}

Original buggy code:
```python
{source_code}
```

Fixed code:
```python
{fixed_code}
```

Existing test file (tests/test_router.py):
```python
{existing_tests}
```

Add a regression test to the EXISTING test file that specifically tests the bug that was fixed.
The test should verify that the exact scenario from the CloudWatch error cannot happen again.
Keep the same style as the existing tests. Add 1-2 focused test functions.

Return the COMPLETE updated test file inside ```python``` markers, nothing else.
Include all existing tests plus the new regression test(s)."""

    text = _claude_request(prompt)
    if "```python" in text:
        return text.split("```python")[1].split("```")[0].strip()
    return text.strip()


def call_claude_pr_description(errors, source_code, fixed_code):
    """Call Claude API to write a clear, non-technical PR description."""
    error_text = "\n".join(errors)
    prompt = f"""You are writing a GitHub pull request description for a non-technical audience.
A CloudWatch alarm fired and an automated system diagnosed and fixed the issue.

Here are the CloudWatch errors:
{error_text}

Here is the original code that had the bug:
```python
{source_code}
```

Here is the fixed code:
```python
{fixed_code}
```

Write a GitHub PR body in markdown. Keep it short, clear, and easy to understand.
Use this structure:
1. **What happened** — one sentence explaining the problem in plain language
2. **What was wrong** — one sentence explaining the root cause without jargon
3. **What this fix does** — one sentence explaining the change
4. **Business impact** — the dollar amounts involved

Also mention that an automated regression test was added to prevent this from happening again.

End with a note that this PR was created automatically by Claude after a CloudWatch alarm.
Do NOT use code blocks, variable names, or technical jargon. Write it so a VP of Engineering would understand it in 10 seconds."""

    return _claude_request(prompt, max_tokens=512)


def create_pr(fixed_code, regression_test, pr_body):
    """Create a branch, commit the fix and regression test, and open a PR on GitHub."""
    branch_name = "fix/routing-cost-weight"

    # Get main branch SHA
    main_ref = github_api("GET", f"/repos/{GITHUB_REPO}/git/ref/heads/main")
    main_sha = main_ref["object"]["sha"]

    # Delete branch if it exists (from a previous demo run)
    try:
        github_api("DELETE", f"/repos/{GITHUB_REPO}/git/refs/heads/{branch_name}")
    except Exception:
        pass

    # Create branch
    github_api("POST", f"/repos/{GITHUB_REPO}/git/refs", {
        "ref": f"refs/heads/{branch_name}",
        "sha": main_sha,
    })

    # Get current file SHA
    file_info = github_api("GET", f"/repos/{GITHUB_REPO}/contents/src/routing/router.py?ref={branch_name}")
    file_sha = file_info["sha"]

    # Commit the fix
    github_api("PUT", f"/repos/{GITHUB_REPO}/contents/src/routing/router.py", {
        "message": "Fix routing cost_weight to use dynamic amount-based weighting",
        "content": base64.b64encode(fixed_code.encode()).decode(),
        "sha": file_sha,
        "branch": branch_name,
    })

    # Commit regression test
    test_info = github_api("GET", f"/repos/{GITHUB_REPO}/contents/tests/test_router.py?ref={branch_name}")
    github_api("PUT", f"/repos/{GITHUB_REPO}/contents/tests/test_router.py", {
        "message": "Add regression test for Wire over-selection bug",
        "content": base64.b64encode(regression_test.encode()).decode(),
        "sha": test_info["sha"],
        "branch": branch_name,
    })

    # Close any existing PR for this branch
    existing = github_api("GET", f"/repos/{GITHUB_REPO}/pulls?head=allierays:{branch_name}&state=open")
    for pr in existing:
        github_api("PATCH", f"/repos/{GITHUB_REPO}/pulls/{pr['number']}", {"state": "closed"})

    # Open PR
    pr = github_api("POST", f"/repos/{GITHUB_REPO}/pulls", {
        "title": "Fix Wire over-selection on large transfers",
        "body": pr_body,
        "head": branch_name,
        "base": "main",
    })

    return pr["html_url"]


def github_api(method, path, body=None):
    """Make a GitHub API request."""
    url = f"https://api.github.com{path}" if path.startswith("/") else f"https://api.github.com/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()) if resp.status != 204 else {}
    except urllib.error.HTTPError as e:
        if method == "DELETE" and e.code == 422:
            return {}
        raise
