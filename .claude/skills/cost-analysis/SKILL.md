---
name: cost-analysis
description: Analyze routing costs, compute actual vs optimal, and surface optimization opportunities with dollar estimates
---

# /cost-analysis

Analyze the FinTechCo routing system's cost efficiency and identify savings opportunities.

## Steps

1. **Read the data sources.**
   - `src/rails/data.py` — rail costs and volume weights
   - `src/routing/router.py` — `score_rail()` logic and the cost_weight bug
   - `src/routing/generator.py` — `generate_payment_batch()` for transaction distribution
   - `src/payments/generator.py` — `generate_metrics()` for current KPIs

2. **Compute current cost profile.** Using the 10 rails, their costs, and volume weights:
   - Calculate weighted average cost per transaction
   - Calculate daily cost at ~4.2M transactions/day (from `generate_metrics()`)
   - Break down cost by rail (volume × cost)
   - Identify the top 3 cost drivers

3. **Compute optimal routing.** For each destination type and amount range in `generate_payment_batch()`:
   - Determine the optimal rail (cheapest that meets speed/success requirements)
   - Compare to what the current `score_rail()` would pick
   - Quantify the gap

4. **Analyze the Wire over-selection bug.** Using the data from `lambda/sync_handler.py`:
   - 847 Wire transactions in 71 hours that should have been RTP
   - Cost per Wire: $25.00 vs RTP: $0.50 = $24.50 overpay per transaction
   - Total excess: $20,768 over 71 hours
   - Annualized: project the excess cost over a year

5. **Surface optimization opportunities.** Present a table:

   | Opportunity | Current Cost | Optimal Cost | Annual Savings |
   |-------------|-------------|--------------|----------------|
   | Fix Wire over-selection (router.py bug) | ... | ... | ... |
   | Shift ACH batch to Same-Day ACH where speed allows | ... | ... | ... |
   | Increase Zelle routing for small P2P | ... | ... | ... |

6. **Recommend next steps.** Prioritize by dollar impact:
   - Which fix saves the most money?
   - Which is easiest to implement?
   - Are there any trade-offs (speed vs cost)?

7. **Do not make code changes.** This is an analysis. Present findings and let the user decide what to act on. If they want to fix the router bug, suggest running `/incident`.
