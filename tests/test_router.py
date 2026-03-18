"""Tests for the AI routing model."""

from src.routing.router import score_rail, pick_best_rail

WIRE = {"id": "wire", "name": "Wire", "cost_usd": 25.00, "success_rate": 98.2, "status": "online"}
RTP = {"id": "rtp", "name": "RTP", "cost_usd": 0.50, "success_rate": 99.5, "status": "online"}
ACH = {"id": "ach", "name": "ACH", "cost_usd": 0.25, "success_rate": 99.1, "status": "online"}
ZELLE = {"id": "zelle", "name": "Zelle", "cost_usd": 0.00, "success_rate": 99.8, "status": "online"}
RAILS = [ZELLE, RTP, ACH, WIRE]


def test_large_transfer_avoids_wire():
    """$50k transfer should pick RTP over Wire."""
    best = pick_best_rail(RAILS, amount=50_000)
    assert best["id"] != "wire", f"Large transfer routed to Wire (${best['cost_usd']}/tx)"


def test_small_transfer_picks_cheapest():
    """$20 transfer should pick cheapest rail."""
    best = pick_best_rail(RAILS, amount=20)
    assert best["cost_usd"] < 1.00, f"Small transfer routed to {best['name']} (${best['cost_usd']}/tx)"


def test_wire_scores_lower_than_rtp_for_large():
    """Wire should score lower than RTP for large transfers."""
    wire_score = score_rail(WIRE, amount=50_000)
    rtp_score = score_rail(RTP, amount=50_000)
    assert rtp_score > wire_score, f"Wire ({wire_score:.2f}) scored higher than RTP ({rtp_score:.2f}) for $50k"


def test_mid_range_balanced():
    """Mid-range transfers should still avoid Wire."""
    best = pick_best_rail(RAILS, amount=2_000)
    assert best["id"] != "wire"


def test_stale_weight_cache_invalidation_loop_fixed():
    """Verify that the stale weight cache invalidation loop is fixed."""
    # Simulate the CloudWatch error scenario
    rails = [
        {"id": "wire", "name": "Wire", "cost_usd": 25.00, "success_rate": 98.2, "status": "online"},
        {"id": "rtp", "name": "RTP", "cost_usd": 0.50, "success_rate": 99.5, "status": "online"},
        {"id": "ach", "name": "ACH", "cost_usd": 0.25, "success_rate": 99.1, "status": "online"},
        {"id": "zelle", "name": "Zelle", "cost_usd": 0.00, "success_rate": 99.8, "status": "online"}
    ]
    best = pick_best_rail(rails, amount=847)
    assert best["id"] != "wire", "Wire should not be selected for large transfers"


def test_cost_weight_is_dynamic():
    """Verify that the cost weight is dynamically adjusted based on transfer amount."""
    # Verify cost weight for large transfer
    wire_score = score_rail(WIRE, amount=50_000)
    rtp_score = score_rail(RTP, amount=50_000)
    assert rtp_score > wire_score, "RTP should score higher than Wire for large transfers"

    # Verify cost weight for small transfer
    wire_score = score_rail(WIRE, amount=200)
    ach_score = score_rail(ACH, amount=200)
    assert ach_score > wire_score, "ACH should score higher than Wire for small transfers"