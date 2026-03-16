from engine.win_probability import apply_historical_seed_prior, production_win_probability, win_probability


def test_probability_clipping() -> None:
    p_high = win_probability({"AdjEM": 50, "Adj_T": 68}, {"AdjEM": -20, "Adj_T": 68})
    p_low = win_probability({"AdjEM": -20, "Adj_T": 68}, {"AdjEM": 50, "Adj_T": 68})
    assert p_high <= 0.97
    assert p_low >= 0.03


def test_historical_prior_lowers_6_seed_edge() -> None:
    raw = win_probability({"AdjEM": 16, "Adj_T": 68, "Seed": 6}, {"AdjEM": 10, "Adj_T": 68, "Seed": 11})
    adjusted = apply_historical_seed_prior(raw, 6, 11)
    assert adjusted < raw


def test_production_probability_reasonable() -> None:
    prob = production_win_probability({"AdjEM": 14, "Adj_T": 68, "Seed": 8}, {"AdjEM": 13, "Adj_T": 68, "Seed": 9})
    assert 0.03 <= prob <= 0.97

