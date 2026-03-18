---
name: load-test
description: Generate an async load test script with configurable concurrency, duration, and latency percentiles
---

# /load-test

Generate a load test script for the FinTechCo API.

## Steps

1. **Get test parameters.** Ask the user for (with defaults):
   - **Target URL**: default `http://localhost:8000`
   - **Endpoints to test**: default all GET endpoints (`/health`, `/api/metrics`, `/api/rails`, `/api/payments`, `/api/model-health`, `/api/chart-data`)
   - **Concurrency**: default `50` concurrent requests
   - **Duration**: default `30` seconds
   - **Include POST /api/sync-routing-model?**: default no (it's slow, ~1.5s)

2. **Generate the script.** Write `scripts/load_test.py` using `httpx.AsyncClient`:

   ```python
   import asyncio
   import httpx
   import time
   import statistics
   import argparse
   ```

   The script should:
   - Accept CLI args for base_url, concurrency, duration, and endpoints
   - Use `httpx.AsyncClient` with connection pooling
   - Run concurrent requests using `asyncio.Semaphore` for concurrency control
   - Collect per-request latency, status code, and endpoint
   - Run for the specified duration, then stop gracefully

3. **Include a results report.** After the run completes, print:
   - Total requests sent
   - Requests per second (throughput)
   - Success rate (2xx vs errors)
   - Latency percentiles: p50, p90, p95, p99
   - Per-endpoint breakdown (avg latency, error rate)
   - Slowest endpoint identification

4. **Add error handling.**
   - Connection refused → clear message to start the server first
   - Timeout tracking (flag requests >2s)
   - Graceful Ctrl+C handling

5. **Make it runnable.**
   ```bash
   # Basic run
   python scripts/load_test.py

   # Custom settings
   python scripts/load_test.py --concurrency 100 --duration 60 --url http://localhost:8000
   ```

6. **Report back.** Show the user how to run the script and what output to expect. Note that `httpx` is already in `requirements.txt`.
