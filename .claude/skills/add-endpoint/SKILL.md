---
name: add-endpoint
description: Scaffold a new FastAPI endpoint with logging, generator function, and tests
---

# /add-endpoint

Add a new API endpoint to the FinTechCo FastAPI server.

## Steps

1. **Get endpoint details.** Ask the user for:
   - HTTP method (GET or POST)
   - Path (e.g. `/api/alerts`)
   - What it should return (description of the data)

2. **Add the generator function.** Edit `src/payments/generator.py` to add a function that produces the data. Follow the existing pattern:
   - Function name: `generate_{resource}()` (e.g. `generate_alerts`)
   - Return a dict or list of dicts with synthetic data
   - Use `random` and `datetime` for realistic variation, matching the style of `generate_metrics()` and `generate_payments()`

3. **Add the endpoint.** Edit `api/app.py`:
   - Import the new generator at the top with the existing imports from `src.payments.generator`
   - Add the route following the existing pattern:
     ```python
     @app.get("/api/alerts")
     async def get_alerts():
         logger.info("alerts.request")
         return {"alerts": generate_alerts()}
     ```
   - Use the `logger` for request logging (JSON format, follows existing convention)

4. **Add tests.** Create or edit a test file in `tests/`:
   - Test the generator function directly (does it return the right shape?)
   - Test the endpoint via FastAPI's `TestClient` if the user wants integration tests:
     ```python
     from fastapi.testclient import TestClient
     from api.app import app
     client = TestClient(app)
     ```

5. **Run tests.**
   ```
   pytest tests/ -v
   ```

6. **Report back.** Show the user the endpoint URL, example response shape, and confirm it works with the dashboard (if the user wants to wire it into the dashboard HTML, that's a separate step).
