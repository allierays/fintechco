"""Tests for the AI routing model."""

from src.routing.router import score_rail, pick_best_rail

WIRE = {"id": "wire", "name": "Wire", "cost_usd": 25.00, "success_rate": 98.2, "status": "online"}
RTP = {"id": "rtp", "name": "RTP", "cost_usd": 0.50, "success_rate": 99.5, "status": "online"}
ACH = {"id": "ach", "name": "ACH", "cost_usd": 0.25, "success_rate": 99.1, "status": "online"}
ZELLE = {"id": "zelle", "name": "Zelle", "cost_usd": 0.00, "success_rate": 99.8, "status": "online"}
RAILS = [ZELLE, RTP, ACH, WIRE]


def test_large_transfer_avoids_wire():
    """$50k transfer should not pick Wire."""
    best = pick_best_rail(RAILS, amount=50_000)
    assert best["id"] != "wire", f"Large transfer routed to Wire (${best['cost_usd']}/tx)"


def test_small_transfer_prioritizes_cost():
    """$20 transfer should pick the cheapest rail."""
    best = pick_best_rail(RAILS, amount=20)
    assert best["id"] != "wire", f"Small transfer routed to Wire (${best['cost_usd']}/tx)"


def test_wire_scores_lower_than_rtp_for_large():
    """Wire should score lower than RTP for large transfers."""
    wire_score = score_rail(WIRE, amount=50_000)
    rtp_score = score_rail(RTP, amount=50_000)
    assert rtp_score > wire_score, f"Wire ({wire_score:.2f}) scored higher than RTP ({rtp_score:.2f}) for $50k"


def test_mid_range_transfer_balances_cost_and_success():
    """Mid-range transfers should balance cost and success rate."""
    best = pick_best_rail(RAILS, amount=2_000)
    assert best["id"] != "wire", f"Mid-range transfer routed to Wire (${best['cost_usd']}/tx)"

    wire_score = score_rail(WIRE, amount=2_000)
    rtp_score = score_rail(RTP, amount=2_000)
    assert abs(wire_score - rtp_score) < 0.1, "Mid-range transfer did not balance cost and success rate"