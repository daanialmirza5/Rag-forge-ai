from app.services.usage_service import estimate_llm_cost_usd


def test_known_model_computes_input_and_output_cost():
    cost = estimate_llm_cost_usd(model="claude-sonnet-5", tokens_input=1_000_000, tokens_output=1_000_000)
    assert cost == 3.00 + 15.00


def test_zero_tokens_costs_nothing():
    assert estimate_llm_cost_usd(model="claude-opus-4-8", tokens_input=0, tokens_output=0) == 0.0


def test_unknown_model_falls_back_to_zero_rather_than_guessing():
    cost = estimate_llm_cost_usd(model="some-future-model", tokens_input=1_000_000, tokens_output=1_000_000)
    assert cost == 0.0


def test_partial_token_counts_scale_linearly():
    cost = estimate_llm_cost_usd(model="claude-haiku-4-5", tokens_input=500_000, tokens_output=0)
    assert cost == 0.50
