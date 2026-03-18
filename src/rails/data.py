"""
Rail definitions for FinTechCo Money Movement Hub.
10 payment rails with realistic cost, latency, and success rate data.
"""

import random

RAILS = [
    {
        "id": "zelle",
        "name": "Zelle",
        "icon": "⚡",
        "cost_usd": 0.00,
        "latency_label": "<2s",
        "latency_seconds": 2,
        "base_success_rate": 99.8,
        "category": "instant",
    },
    {
        "id": "rtp",
        "name": "RTP",
        "icon": "🔄",
        "cost_usd": 0.50,
        "latency_label": "<10s",
        "latency_seconds": 10,
        "base_success_rate": 99.5,
        "category": "instant",
    },
    {
        "id": "fednow",
        "name": "FedNow",
        "icon": "🏛",
        "cost_usd": 0.45,
        "latency_label": "<10s",
        "latency_seconds": 10,
        "base_success_rate": 99.3,
        "category": "instant",
    },
    {
        "id": "venmo",
        "name": "Venmo",
        "icon": "💙",
        "cost_usd": 0.00,
        "latency_label": "<1min",
        "latency_seconds": 60,
        "base_success_rate": 95.5,
        "category": "social",
    },
    {
        "id": "paypal",
        "name": "PayPal",
        "icon": "🅿",
        "cost_usd": 0.30,
        "latency_label": "<1min",
        "latency_seconds": 60,
        "base_success_rate": 96.2,
        "category": "social",
    },
    {
        "id": "ach",
        "name": "ACH",
        "icon": "🏦",
        "cost_usd": 0.25,
        "latency_label": "2–3h",
        "latency_seconds": 9000,
        "base_success_rate": 99.1,
        "category": "batch",
    },
    {
        "id": "same_day_ach",
        "name": "Same-Day ACH",
        "icon": "📅",
        "cost_usd": 1.00,
        "latency_label": "<4h",
        "latency_seconds": 14400,
        "base_success_rate": 98.8,
        "category": "batch",
    },
    {
        "id": "card_push",
        "name": "Card Push",
        "icon": "💳",
        "cost_usd": 2.50,
        "latency_label": "<30min",
        "latency_seconds": 1800,
        "base_success_rate": 97.4,
        "category": "card",
    },
    {
        "id": "wire",
        "name": "Wire",
        "icon": "🔌",
        "cost_usd": 25.00,
        "latency_label": "2–4h",
        "latency_seconds": 10800,
        "base_success_rate": 98.2,
        "category": "high_value",
    },
    {
        "id": "swift",
        "name": "SWIFT",
        "icon": "🌐",
        "cost_usd": 45.00,
        "latency_label": "1–3 days",
        "latency_seconds": 172800,
        "base_success_rate": 97.1,
        "category": "international",
    },
]

RAIL_IDS = [r["id"] for r in RAILS]

# Volume weights — Zelle and ACH dominate, Wire/SWIFT are rare
VOLUME_WEIGHTS = [0.31, 0.19, 0.12, 0.06, 0.04, 0.28, 0.08, 0.05, 0.04, 0.01]


def get_rails_with_status() -> list[dict]:
    """Return all rails with live-ish randomized status."""
    result = []
    for i, rail in enumerate(RAILS):
        # Degrade 1-2 rails slightly for realism
        jitter = random.uniform(-0.3, 0.1)
        success_rate = round(min(100.0, rail["base_success_rate"] + jitter), 1)

        # Occasionally show degraded status
        r = random.random()
        if r < 0.04:
            status = "degraded"
        elif r < 0.005:
            status = "down"
        else:
            status = "online"

        # Volume
        base_daily = random.randint(800000, 6000000)

        result.append({
            "id": rail["id"],
            "name": rail["name"],
            "icon": rail["icon"],
            "cost_usd": rail["cost_usd"],
            "latency_label": rail["latency_label"],
            "success_rate": success_rate,
            "status": status,
            "volume_24h": base_daily,
            "category": rail["category"],
        })
    return result
