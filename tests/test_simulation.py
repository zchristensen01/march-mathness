from engine.simulation import generate_modal_bracket, simulate_bracket
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


def test_modal_bracket_uses_slot_order_for_round_of_64() -> None:
    def deterministic_prob(_a: dict, _b: dict) -> float:
        return 1.0

    # Intentionally shuffled input order to verify slot-based ordering.
    east = [
        {"Team": "Slot5", "Seed": 5, "AdjEM": 0.0, "Adj_T": 68, "slot": 5},
        {"Team": "Slot1", "Seed": 1, "AdjEM": 0.0, "Adj_T": 68, "slot": 1},
        {"Team": "Slot2", "Seed": 16, "AdjEM": 0.0, "Adj_T": 68, "slot": 2},
        {"Team": "Slot6", "Seed": 12, "AdjEM": 0.0, "Adj_T": 68, "slot": 6},
        {"Team": "Slot3", "Seed": 8, "AdjEM": 0.0, "Adj_T": 68, "slot": 3},
        {"Team": "Slot4", "Seed": 9, "AdjEM": 0.0, "Adj_T": 68, "slot": 4},
        {"Team": "Slot7", "Seed": 4, "AdjEM": 0.0, "Adj_T": 68, "slot": 7},
        {"Team": "Slot8", "Seed": 13, "AdjEM": 0.0, "Adj_T": 68, "slot": 8},
        {"Team": "Slot9", "Seed": 6, "AdjEM": 0.0, "Adj_T": 68, "slot": 9},
        {"Team": "Slot10", "Seed": 11, "AdjEM": 0.0, "Adj_T": 68, "slot": 10},
        {"Team": "Slot11", "Seed": 3, "AdjEM": 0.0, "Adj_T": 68, "slot": 11},
        {"Team": "Slot12", "Seed": 14, "AdjEM": 0.0, "Adj_T": 68, "slot": 12},
        {"Team": "Slot13", "Seed": 7, "AdjEM": 0.0, "Adj_T": 68, "slot": 13},
        {"Team": "Slot14", "Seed": 10, "AdjEM": 0.0, "Adj_T": 68, "slot": 14},
        {"Team": "Slot15", "Seed": 2, "AdjEM": 0.0, "Adj_T": 68, "slot": 15},
        {"Team": "Slot16", "Seed": 15, "AdjEM": 0.0, "Adj_T": 68, "slot": 16},
    ]
    filler = [_team(f"X{i}", i, 1.0, i) for i in range(1, 17)]
    bracket = {"East": east, "West": filler, "South": filler, "Midwest": filler}

    modal = generate_modal_bracket({}, bracket, deterministic_prob)
    first_game = modal["regions"]["East"]["R64"][0]
    assert first_game["team_a"] == "Slot1"
    assert first_game["team_b"] == "Slot2"


def test_simulation_uses_canonical_final_four_pairings() -> None:
    def ff_pairing_sensitive_prob(team_a: dict, team_b: dict) -> float:
        a = str(team_a["Team"])
        b = str(team_b["Team"])
        winners = {
            ("East Champ", "West Champ"): "West Champ",
            ("West Champ", "East Champ"): "West Champ",
            ("South Champ", "Midwest Champ"): "South Champ",
            ("Midwest Champ", "South Champ"): "South Champ",
            ("West Champ", "South Champ"): "South Champ",
            ("South Champ", "West Champ"): "South Champ",
        }
        winner = winners.get((a, b), a)
        return 1.0 if a == winner else 0.0

    def make_region(champion_name: str, seed_base: int) -> list[dict]:
        teams = []
        for slot in range(1, 17):
            team_name = champion_name if slot == 1 else f"{champion_name} Team {slot}"
            teams.append({"Team": team_name, "Seed": max(1, min(16, seed_base + slot - 1)), "AdjEM": 0.0, "Adj_T": 68, "slot": slot})
        return teams

    # Deliberately non-canonical insertion order. Pairing logic should still do
    # East vs West and South vs Midwest.
    bracket = {
        "East": make_region("East Champ", 1),
        "South": make_region("South Champ", 2),
        "West": make_region("West Champ", 3),
        "Midwest": make_region("Midwest Champ", 4),
    }

    results = simulate_bracket(bracket, ff_pairing_sensitive_prob, n_sims=1, seed=7)
    assert results["South Champ"]["Champion"] == 1.0

