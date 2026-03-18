---
name: security-audit
description: Review the codebase for fintech security concerns including injection, data exposure, CORS, secrets, and PCI patterns
---

# /security-audit

Run a security review of the FinTechCo codebase focused on fintech-specific risks.

## Steps

1. **Read all source files.** This is a read-only audit. Read every file:
   - `api/app.py`
   - `src/payments/generator.py`
   - `src/rails/data.py`
   - `src/routing/router.py`, `runner.py`, `generator.py`
   - `lambda/sync_handler.py`, `auto_fix.py`
   - `scripts/watch-cloudwatch.sh`
   - `dashboard.html`
   - `requirements.txt`

2. **Check each category** and report findings:

   **Injection & Input Validation**
   - Are any API inputs used in queries, file paths, or shell commands without sanitization?
   - Does the POST `/api/sync-routing-model` endpoint accept and use any user input?
   - Are there any eval(), exec(), or subprocess calls with user-controlled strings?

   **Data Exposure**
   - Do API responses leak internal IDs, stack traces, or system paths?
   - Does the dashboard expose sensitive data in the DOM or console?
   - Are payment amounts, account numbers, or PII visible in logs?

   **CORS & Headers**
   - Is CORS configured? If not, flag it.
   - Are security headers set (X-Content-Type-Options, X-Frame-Options, CSP)?
   - Is HTTPS enforced?

   **Secrets Management**
   - Are API keys, tokens, or credentials hardcoded anywhere?
   - Check `auto_fix.py` for Anthropic API key handling and GitHub token handling
   - Check `watch-cloudwatch.sh` for AWS credential handling
   - Is there a `.env` file committed or referenced without `.gitignore` protection?

   **PCI & Financial Data Patterns**
   - Are payment amounts logged in a way that could violate PCI DSS?
   - Is there any card data (PAN, CVV) anywhere, even in test fixtures?
   - Are transaction IDs sequential and predictable?

   **Dependency Risks**
   - Check `requirements.txt` for known-vulnerable versions
   - Are dependencies pinned to exact versions or using ranges?

   **Logging Hygiene**
   - Does the JSON logger accidentally serialize sensitive fields?
   - Are error messages too detailed for production (leaking file paths, line numbers)?

3. **Produce a report.** For each finding:
   - **Severity**: Critical / High / Medium / Low / Info
   - **File + line**: Where the issue is
   - **What**: Description of the concern
   - **Fix**: Recommended remediation

4. **Do not make any changes.** This is an audit only. Present findings to the user and let them decide what to fix.
