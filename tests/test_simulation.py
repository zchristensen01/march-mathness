from engine.simulation import simulate_bracket
from engine.win_probability import production_win_probability


def _team(name: str, seed: int, adjem: float, slot: int) -> dict:
    return {"Team": name, "Seed": seed, "AdjEM": adjem, "Adj_T": 68, "slot": slot}


def test_simulation_probabilities_sum_to_one_like() -> None:
    bracket = {
        "East": [_team(f"E{i}", i if i <= 16 else 16, 20 - i, i) for i in range(1, 17)],
        "West": [_team(f"W{i}", i if i <= 16 else 16, 20 - i, i) for i in range(1, 17)],
        "South": [_team(f"S{i}", i if i <= 16 else 16, 20 - i, i) for i in range(1, 17)],
        "Midwest": [_team(f"M{i}", i if i <= 16 else 16, 20 - i, i) for i in range(1, 17)]
    }
    results = simulate_bracket(bracket, production_win_probability, n_sims=100, seed=42)
    champion_total = sum(team_rounds.get("Champion", 0.0) for team_rounds in results.values())
    assert abs(champion_total - 1.0) < 0.05

