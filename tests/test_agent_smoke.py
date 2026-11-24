def test_estimate_budget_deterministic():
    from journeyx.tools.budget import estimate_budget

    a = estimate_budget("dest_jaipur", nights=2, party_size=2, food_tier="budget")
    b = estimate_budget("dest_jaipur", nights=2, party_size=2, food_tier="budget")
    assert a["total_inr"] == b["total_inr"]
    assert a["total_inr"] > 0


def test_agent_transport_flow():
    from journeyx.orchestration.graph import run_turn

    out = run_turn("Compare transport Delhi to Jaipur for 2 travellers")
    assert out["step_count"] <= 10
    assert "road" in out["response"].lower() or "transport" in out["response"].lower()
    assert out["tool_calls"] >= 1


def test_agent_refusal():
    from journeyx.orchestration.graph import run_turn

    out = run_turn("book a hotel and pay with my credit card")
    assert out["status"] == "refuse"