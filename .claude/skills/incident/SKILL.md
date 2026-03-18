---
name: incident
description: Diagnose a production incident from CloudWatch errors, trace root cause, fix, test, and open a PR
---

# /incident

Diagnose and fix a production incident in the FinTechCo payment routing system.

## Steps

1. **Get the error context.** Ask the user what they're seeing. If they paste a CloudWatch error or log snippet, use that. If they say "costs are spiking" or something general, check `lambda/sync_handler.py` for the error flow and `scripts/watch-cloudwatch.sh` for how errors surface.

2. **Trace the root cause.** Read the file and line referenced in the error. The most common incident points to `src/routing/router.py:17` — the hardcoded `cost_weight = 0.5` in `score_rail()`. Read the function, understand what it does, and explain the bug clearly:
   - What the code does now (equal 0.5/0.5 weighting regardless of amount)
   - What it should do (weight success_rate higher for large transfers, cost higher for small ones)
   - The business impact (Wire at $25/tx winning over RTP at $0.50/tx for large transfers)

3. **Quantify the impact.** Reference the numbers from the sync handler logs:
   - 847 Wire transactions over 71 hours when RTP would have been optimal
   - Excess cost: $20,768
   - Feature store age: 71 hours stale

4. **Write the fix.** Edit `src/routing/router.py` to make `score_rail()` use dynamic weighting based on amount:
   - Large transfers ($10k+): `success_weight = 0.8`, `cost_weight = 0.2`
   - Small transfers (<$500): `success_weight = 0.2`, `cost_weight = 0.8`
   - Mid-range: `success_weight = 0.5`, `cost_weight = 0.5`

5. **Update tests.** Read `tests/test_router.py`. The existing tests `test_large_transfer_avoids_wire` and `test_wire_scores_lower_than_rtp_for_large` should now pass. Run them to confirm:
   ```
   pytest tests/test_router.py -v
   ```
   If any test still fails, adjust the fix until all 4 tests pass.

6. **Open a PR.** Create a branch `fix/routing-cost-weight`, commit the changes, push, and open a PR with:
   - Title: "Fix Wire over-selection on large transfers"
   - Body: Plain-language explanation of the bug, impact ($20,768 excess cost), and fix
