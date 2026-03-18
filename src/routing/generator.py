"""
Synthetic data generator for the routing pipeline.
Generates payment batches and rail weight summaries.
"""

import random
from datetime import datetime, timedelta

from src.rails.data import RAILS, RAIL_IDS, VOLUME_WEIGHTS

DESTINATION_TYPES = [
    ("house closing", 45000, 500000),
    ("payroll", 1000, 50000),
    ("vendor payment", 500, 25000),
    ("insurance premium", 200, 5000),
    ("rent", 800, 8000),
    ("pizza", 15, 80),
    ("subscription", 10, 200),
    ("refund", 50, 2000),
    ("p2p transfer", 20, 5000),
    ("international wire", 1000, 100000),
]


def generate_payment_batch(count: int = 5000) -> list[dict]:
    """Generate a synthetic batch of payments for routing analysis."""
    now = datetime.utcnow()
    payments = []

    for i in range(count):
        dest_type, min_amt, max_amt = random.choice(DESTINATION_TYPES)
        amount = round(random.uniform(min_amt, max_amt), 2)
        minutes_ago = random.randint(0, 1440)

        # Pick rail weighted by volume
        rail_id = random.choices(RAIL_IDS, weights=VOLUME_WEIGHTS, k=1)[0]
        rail = next(r for r in RAILS if r["id"] == rail_id)

        # Determine outcome
        r = random.random()
        success_threshold = rail["base_success_rate"] / 100
        if r < success_threshold:
            status = "success"
            rerouted = False
        elif r < success_threshold + 0.015:
            status = "rerouted"
            rerouted = True
        else:
            status = "failed"
            rerouted = False

        payments.append({
            "payment_id": f"PMT-{2000000 + i}",
            "timestamp": (now - timedelta(minutes=minutes_ago)).isoformat(),
            "amount": amount,
            "destination_type": dest_type,
            "rail_id": rail_id,
            "rail_name": rail["name"],
            "cost_usd": rail["cost_usd"],
            "status": status,
            "rerouted": rerouted,
            "urgency": "high" if amount > 10000 else "normal",
        })

    return sorted(payments, key=lambda x: x["timestamp"], reverse=True)


def compute_rail_weight_summary(payments: list[dict]) -> dict:
    """Count successes, failures, and reroutes per rail. Return updated weight scores."""
    stats = {r["id"]: {"success": 0, "failed": 0, "rerouted": 0, "total": 0} for r in RAILS}

    for p in payments:
        rid = p["rail_id"]
        if rid not in stats:
            continue
        stats[rid]["total"] += 1
        stats[rid][p["status"]] += 1

    weights = {}
    for rid, s in stats.items():
        if s["total"] == 0:
            weights[rid] = 1.0
            continue
        sr = s["success"] / s["total"]
        weights[rid] = round(sr, 4)

    return {
        "rail_weights": weights,
        "total_payments": len(payments),
        "total_reroutes": sum(s["rerouted"] for s in stats.values()),
        "total_failures": sum(s["failed"] for s in stats.values()),
    }
