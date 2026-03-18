---
name: add-rail
description: Add a new payment rail end-to-end with data, routing, tests, and dashboard support
---

# /add-rail

Add a new payment rail to the FinTechCo routing system.

## Steps

1. **Get rail details.** Ask the user for:
   - Rail ID (snake_case, e.g. `apple_pay`)
   - Display name (e.g. "Apple Pay")
   - Cost per transaction in USD
   - Speed label (e.g. "<5s", "1–2 days")
   - Base success rate (percentage)
   - Category: `instant`, `social`, `batch`, `card`, `high_value`, or `international`

2. **Add the rail definition.** Edit `src/rails/data.py`:
   - Add a new dict to the `RAILS` list following the existing format:
     ```python
     {"id": "rail_id", "name": "Display Name", "cost_usd": 0.00, "speed": "<5s", "success_rate": 99.0, "category": "instant"}
     ```
   - Add a corresponding entry to `VOLUME_WEIGHTS`. The weights must sum to 1.0 — reduce existing weights proportionally to make room.

3. **Verify routing picks it up.** Read `src/routing/router.py` to confirm `score_rail()` works with any rail dict (it does — no rail-specific logic). Read `src/routing/generator.py` to confirm `generate_payment_batch()` pulls from `data.py` dynamically (it does).

4. **Verify dashboard picks it up.** Read `src/payments/generator.py` to confirm `generate_rails()` calls `get_rails_with_status()` from `data.py` (it does). The dashboard renders whatever `/api/rails` returns, so no HTML changes needed.

5. **Add tests.** Edit `tests/test_router.py`:
   - Add a fixture for the new rail matching the format of WIRE, RTP, ACH, ZELLE
   - Add the new rail to the `RAILS` list fixture
   - Add at least one test that verifies the new rail scores correctly for its intended use case

6. **Run tests.** Confirm all tests pass:
   ```
   pytest tests/test_router.py -v
   ```
   Note: `test_large_transfer_avoids_wire` and `test_wire_scores_lower_than_rtp_for_large` may fail due to the intentional bug. That's expected — don't fix the bug as part of this skill.

7. **Report back.** Summarize what was added and confirm the rail appears in the API by explaining the data flow: `data.py` → `generator.py` → `app.py` → dashboard.
