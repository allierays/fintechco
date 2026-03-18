"""
Routing pipeline runner — orchestrates the 3-step routing model sync.
Each step is logged so CloudWatch captures the full trace.
"""

import logging
import time

from src.routing.generator import generate_payment_batch, compute_rail_weight_summary
from src.routing.router import compute_routing_accuracy, compute_cost_savings_rate

logger = logging.getLogger("routing_pipeline")


def run_sync_pipeline() -> dict:
    """
    Run the full routing model sync pipeline:
      1. Pull payment batch
      2. Recompute rail weights
      3. Recalibrate thresholds

    Returns pipeline result with updated routing metrics.
    """
    start = time.time()
    steps = []

    # ── Step 1: Pull payment batch ───────────────────────────────────────────
    logger.info("pipeline.step1.start: pulling payment batch")
    t0 = time.time()
    payments = generate_payment_batch(count=5000)
    duration_ms = round((time.time() - t0) * 1000)
    reroutes = sum(1 for p in payments if p["rerouted"])
    logger.info(
        "pipeline.step1.complete: %d payments pulled, %d reroutes in %dms",
        len(payments), reroutes, duration_ms,
    )
    steps.append({
        "step": 1,
        "name": "Pull payment batch",
        "status": "ok",
        "detail": f"{len(payments):,} payments pulled · {reroutes} reroutes detected",
        "duration_ms": duration_ms,
    })

    # ── Step 2: Recompute rail weights ───────────────────────────────────────
    logger.info("pipeline.step2.start: recomputing rail weights")
    t0 = time.time()
    weight_summary = compute_rail_weight_summary(payments)
    duration_ms = round((time.time() - t0) * 1000)
    total_failures = weight_summary["total_failures"]
    logger.info(
        "pipeline.step2.complete: %d rails scored, %d failures, %d reroutes in %dms",
        len(weight_summary["rail_weights"]),
        total_failures,
        weight_summary["total_reroutes"],
        duration_ms,
    )
    steps.append({
        "step": 2,
        "name": "Recompute rail weights",
        "status": "ok",
        "detail": (
            f"{len(weight_summary['rail_weights'])} rails scored · "
            f"{total_failures} failures · "
            f"{weight_summary['total_reroutes']} reroutes"
        ),
        "duration_ms": duration_ms,
    })

    # ── Step 3: Recalibrate thresholds ───────────────────────────────────────
    logger.info("pipeline.step3.start: recalibrating routing thresholds")
    t0 = time.time()
    accuracy = compute_routing_accuracy(weight_summary["rail_weights"])
    savings_rate = compute_cost_savings_rate(weight_summary["rail_weights"])
    duration_ms = round((time.time() - t0) * 1000)
    logger.info(
        "pipeline.step3.complete: routing accuracy %.1f%%, cost savings rate %.1f%% in %dms",
        accuracy, savings_rate, duration_ms,
    )
    steps.append({
        "step": 3,
        "name": "Recalibrate thresholds",
        "status": "ok",
        "detail": f"Routing accuracy {accuracy}% · Cost savings rate {savings_rate}%",
        "duration_ms": duration_ms,
    })

    total_ms = round((time.time() - start) * 1000)
    logger.info("pipeline.complete: all 3 steps succeeded in %dms", total_ms)

    return {
        "status": "ok",
        "steps": steps,
        "routing": {
            "accuracy": accuracy,
            "cost_savings_rate": savings_rate,
            "reroute_count": weight_summary["total_reroutes"],
            "feature_store_age_hours": 0,
            "champion_model": "routing-model-v3.1.2",
            "challenger_model": "routing-model-v3.2.0-beta",
        },
        "total_duration_ms": total_ms,
    }
