"""
Synthetic data generator for the Money Movement Hub dashboard.
Produces KPIs, payment feed, chart data, and rail statuses.
"""

import random
from datetime import datetime, timedelta

from src.rails.data import RAILS, RAIL_IDS, VOLUME_WEIGHTS, get_rails_with_status

DESTINATION_TYPES = [
    "house closing",
    "payroll run",
    "vendor payment",
    "insurance premium",
    "rent",
    "pizza order",
    "subscription",
    "refund",
    "p2p transfer",
    "international wire",
    "mortgage payment",
    "healthcare claim",
    "tax payment",
    "contractor invoice",
    "utility bill",
]


def generate_metrics() -> dict:
    return {
        "payments_24h": random.randint(4000000, 4500000),
        "avg_routing_cost": round(random.uniform(1.75, 1.95), 2),
        "cost_savings_24h": round(random.uniform(1900000, 2300000), 0),
        "success_rate": round(random.uniform(99.1, 99.5), 1),
        "reroutes_24h": random.randint(1100, 1400),
    }


def generate_payments(count: int = 20) -> list[dict]:
    now = datetime.utcnow()
    result = []

    for i in range(count):
        dest = random.choice(DESTINATION_TYPES)
        rail_id = random.choices(RAIL_IDS, weights=VOLUME_WEIGHTS, k=1)[0]
        rail = next(r for r in RAILS if r["id"] == rail_id)

        # Amount varies by destination type
        if "house" in dest or "mortgage" in dest:
            amount = round(random.uniform(50000, 850000), 2)
        elif "payroll" in dest:
            amount = round(random.uniform(5000, 80000), 2)
        elif "pizza" in dest or "subscription" in dest:
            amount = round(random.uniform(10, 150), 2)
        else:
            amount = round(random.uniform(100, 15000), 2)

        seconds_ago = random.randint(0, 3600)

        r = random.random()
        success_threshold = rail["base_success_rate"] / 100
        if r < success_threshold:
            status = "success"
        elif r < success_threshold + 0.015:
            status = "rerouted"
        else:
            status = "failed"

        # Flag large Wire transactions as suboptimal routing
        overpay_note = None
        if rail["name"] == "Wire" and amount >= 10000 and status != "failed":
            overpay_note = "Wire (suboptimal) — should be RTP · +$24.50"

        result.append({
            "payment_id": f"PMT-{3000000 + i}",
            "timestamp": (now - timedelta(seconds=seconds_ago)).isoformat(),
            "amount": amount,
            "destination_type": dest,
            "rail_id": rail_id,
            "rail_name": rail["name"],
            "cost_usd": rail["cost_usd"],
            "latency_label": rail["latency_label"],
            "status": status,
            "seconds_ago": seconds_ago,
            "overpay_note": overpay_note,
        })

    return sorted(result, key=lambda x: x["timestamp"], reverse=True)


def generate_model_health() -> dict:
    return {
        "routing_accuracy": 94.1,
        "avg_cost_per_decision": round(random.uniform(1.75, 1.95), 2),
        "cost_savings_rate": 87.3,
        "feature_store_age_hours": 71,
        "feature_store_stale": True,
        "champion_model": "routing-model-v3.1.2",
        "challenger_model": "routing-model-v3.2.0-beta",
    }


def generate_chart_data() -> dict:
    now = datetime.utcnow()
    hours = []
    volumes = []
    avg_costs = []

    for i in range(23, -1, -1):
        hour = now - timedelta(hours=i)
        hours.append(hour.strftime("%-I%p").lower())
        volumes.append(random.randint(150000, 220000))
        avg_costs.append(round(random.uniform(1.60, 2.10), 2))

    # Rail usage breakdown (donut) — matches VOLUME_WEIGHTS roughly
    rail_names = [r["name"] for r in RAILS]
    base_counts = [int(w * 10000) + random.randint(-200, 200) for w in VOLUME_WEIGHTS]

    return {
        "hours": hours,
        "volumes": volumes,
        "avg_costs": avg_costs,
        "rail_names": rail_names,
        "rail_counts": base_counts,
    }


def generate_rails() -> list[dict]:
    return get_rails_with_status()
