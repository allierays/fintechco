---
name: onboard
description: Walk a new engineer through the codebase with an architecture tour, data flow, and where to make changes
---

# /onboard

Give a new engineer a guided tour of the FinTechCo codebase.

## Steps

1. **Start with the big picture.** Explain what FinTechCo does in one paragraph:
   - AI-powered payment routing across 10 rails
   - Optimizes for cost vs speed vs success rate
   - Real-time dashboard, Lambda-based monitoring, Claude-powered auto-fix

2. **Walk the directory structure.** Read and explain each directory's purpose:
   - `api/` — FastAPI server (single file, 7 endpoints)
   - `src/rails/` — Payment rail definitions (the source of truth)
   - `src/routing/` — Routing model, sync pipeline, payment batch generator
   - `src/payments/` — Dashboard data generators
   - `lambda/` — AWS Lambda handlers (sync + auto-fix)
   - `scripts/` — CloudWatch polling
   - `tests/` — pytest suite
   - `dashboard.html` — Single-page dashboard

3. **Trace a request end-to-end.** Walk through what happens when:
   - A user loads the dashboard → `GET /` serves HTML → JS fetches `/api/metrics`, `/api/rails`, `/api/payments`, `/api/chart-data`, `/api/model-health`
   - A user clicks "Sync Routing Model" → `POST /api/sync-routing-model` → `run_sync_pipeline()` in `runner.py` → 3 steps (pull batch, compute weights, recalibrate)

4. **Explain the data flow.** Show how rails flow through the system:
   ```
   data.py (10 rails) → generator.py (synthetic payments) → router.py (scoring) → runner.py (pipeline) → app.py (API) → dashboard.html
   ```

5. **Point out the intentional bug.** Explain:
   - Where: `src/routing/router.py:17` — `cost_weight = 0.5` hardcoded
   - What it does: Wire wins over RTP for large transfers
   - Why it exists: Powers the auto-fix demo (don't fix it unless asked)
   - Which tests fail because of it

6. **Show where to make common changes:**
   - **Add a payment rail** → `src/rails/data.py` (add to `RAILS` + `VOLUME_WEIGHTS`)
   - **Add an API endpoint** → `api/app.py` + `src/payments/generator.py`
   - **Change routing logic** → `src/routing/router.py`
   - **Update dashboard** → `dashboard.html` (vanilla JS, no build step)
   - **Add tests** → `tests/test_router.py`

7. **Cover the tooling.** Show how to:
   ```bash
   # Setup
   python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

   # Run the server
   uvicorn api.app:app --reload --port 8000

   # Run tests
   pytest tests/ -v

   # Available skills
   # /incident, /add-rail, /add-endpoint, /security-audit, /cost-analysis, /load-test
   ```

8. **Ask if they have questions.** Offer to dive deeper into any area, or suggest they try `/add-rail` or `/cost-analysis` to get hands-on.
