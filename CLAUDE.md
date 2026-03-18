# FinTechCo Money Movement Hub

AI-powered payment routing system that optimizes transaction costs across 10 payment rails. FastAPI backend serves a real-time dashboard showing KPIs, rail health, and model performance. Includes a CloudWatch → Lambda → Claude auto-fix pipeline that detects routing anomalies, diagnoses the root cause, and opens a PR with a fix.

## Architecture

- **Python 3.12**, FastAPI, single-file HTML dashboard
- **Backend**: `api/app.py` — FastAPI with JSON logging to stdout
- **Frontend**: `dashboard.html` — vanilla HTML/CSS/JS, Chart.js, polls API on load
- **Lambda**: `lambda/sync_handler.py` (routing sync), `lambda/auto_fix.py` (Claude-powered auto-fix)
- **Monitoring**: CloudWatch log group `/aws/lambda/fintechco-sync`, polled by `scripts/watch-cloudwatch.sh`
- **Data**: Synthetic generators, no database

## Key Directories

```
api/
  app.py                  # FastAPI server, all endpoints, JSON logger
src/
  payments/
    generator.py          # Dashboard data: metrics, payments, charts, model health
  rails/
    data.py               # 10 payment rail definitions + get_rails_with_status()
  routing/
    router.py             # score_rail() — rail scoring model (has intentional bug)
    runner.py             # run_sync_pipeline() — 3-step routing sync
    generator.py          # generate_payment_batch(), compute_rail_weight_summary()
lambda/
  sync_handler.py         # Sync Lambda — logs intentional ERROR pointing to bug
  auto_fix.py             # Auto-fix Lambda — calls Claude API to diagnose + open PR
scripts/
  watch-cloudwatch.sh     # Polls CloudWatch, triggers Claude Code on errors
tests/
  test_router.py          # Router tests (4 tests, 2 should fail due to the bug)
dashboard.html            # Single-page dashboard (vanilla HTML/CSS/JS)
```

## Payment Rails

| Rail ID | Name | Cost | Speed | Success Rate | Category |
|---------|------|------|-------|--------------|----------|
| `zelle` | Zelle | $0.00 | <2s | 99.8% | instant |
| `rtp` | RTP | $0.50 | <10s | 99.5% | instant |
| `fednow` | FedNow | $0.45 | <10s | 99.3% | instant |
| `venmo` | Venmo | $0.00 | <1min | 95.5% | social |
| `paypal` | PayPal | $0.30 | <1min | 96.2% | social |
| `ach` | ACH | $0.25 | 2–3h | 99.1% | batch |
| `same_day_ach` | Same-Day ACH | $1.00 | <4h | 98.8% | batch |
| `card_push` | Card Push | $2.50 | <30min | 97.4% | card |
| `wire` | Wire | $25.00 | 2–4h | 98.2% | high_value |
| `swift` | SWIFT | $45.00 | 1–3 days | 97.1% | international |

Rails are defined in `src/rails/data.py`. Volume weights: Zelle (31%) and ACH (28%) dominate.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves `dashboard.html` |
| GET | `/health` | Health check → `{"status": "healthy"}` |
| GET | `/api/metrics` | KPI summary (payments_24h, avg_routing_cost, cost_savings_24h, success_rate, reroutes_24h) |
| GET | `/api/rails` | Rail status with live jitter (degraded/down states) |
| GET | `/api/payments` | 20 recent synthetic transactions |
| GET | `/api/model-health` | Routing model metrics (accuracy, cost/decision, champion/challenger) |
| GET | `/api/chart-data` | Hourly volume + cost chart data |
| POST | `/api/sync-routing-model` | Triggers 3-step routing sync pipeline |

## Conventions

- **Logging**: JSON to stdout via `_JsonFormatter` in `app.py`. Logger names: `"api"` (server), `"routing_pipeline"` (sync steps). Pipeline logs use `pipeline.step{N}.start` / `pipeline.step{N}.complete` pattern.
- **Generators**: All data is synthetic. `src/payments/generator.py` feeds the dashboard API. `src/routing/generator.py` feeds the sync pipeline. Both use `src/rails/data.py` as the source of truth for rails.
- **Tests**: pytest, in `tests/`. Test fixtures define rail dicts inline (WIRE, RTP, ACH, ZELLE). Tests import from `src.routing.router`.
- **New rails**: Add to `RAILS` list in `data.py` with matching entry in `VOLUME_WEIGHTS`. Generators pick it up automatically.
- **New endpoints**: Add route in `app.py`, generator function in `src/payments/generator.py`.

## The Intentional Bug

`src/routing/router.py:13-20` — `score_rail()` hardcodes `cost_weight = 0.5` and `success_weight = 0.5` regardless of transfer amount. For large transfers ($10k+), success_rate should dominate; for small transfers (<$500), cost should dominate. The bug causes Wire ($25/tx) to win over RTP ($0.50/tx) on large transfers, spiking avg_cost_per_txn.

**This bug exists on purpose.** It powers the CloudWatch → Lambda → Claude auto-fix demo. Don't fix it unless explicitly asked.

Two tests in `test_router.py` are designed to fail because of this bug:
- `test_large_transfer_avoids_wire`
- `test_wire_scores_lower_than_rtp_for_large`

## Skills

| Skill | Description |
|-------|-------------|
| `/incident` | Diagnose a production incident from CloudWatch errors, trace root cause, fix, test, open PR |
| `/add-rail` | Add a new payment rail end-to-end: data, routing, tests, dashboard picks it up |
| `/add-endpoint` | Scaffold a new FastAPI endpoint with logging, generator, and tests |
| `/security-audit` | Review the codebase for fintech security concerns: injection, data exposure, CORS, secrets, PCI, logging |
| `/cost-analysis` | Analyze routing costs, compute actual vs optimal, surface optimization opportunities with $ estimates |
| `/load-test` | Generate an async load test script with configurable concurrency, duration, and latency percentiles |
| `/onboard` | Walk a new engineer through the codebase: architecture tour, data flow, where to make changes |

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run
uvicorn api.app:app --reload --port 8000

# Test
pytest tests/ -v

# CloudWatch polling (requires AWS CLI configured)
./scripts/watch-cloudwatch.sh          # poll every 30s
./scripts/watch-cloudwatch.sh --once   # check once and exit
```
