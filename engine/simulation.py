"""Monte Carlo tournament simulation."""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Any, Callable

import numpy as np

from engine import FIRST_ROUND_MATCHUPS, ROUND_NAMES
from engine.win_probability import HISTORICAL_ADVANCEMENT_RATES

log = logging.getLogger(__name__)


def _play_game(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    reach_count: dict[str, dict[str, int]],
    next_round: str
) -> dict[str, Any]:
    """Simulate a single game and update winner's advancement count."""
    p_a = float(win_prob_fn(team_a, team_b))
    winner = team_a if random.random() < p_a else team_b
    winner_name = str(winner.get("Team", winner.get("team")))
    reach_count[winner_name][next_round] += 1
    return winner


def _normalize_team_key(team: dict[str, Any]) -> dict[str, Any]:
    out = dict(team)
    if "Team" not in out and "team" in out:
        out["Team"] = out["team"]
    if "team" not in out and "Team" in out:
        out["team"] = out["Team"]
    return out


def _log_historical_diagnostics(
    normalized_bracket: dict[str, list[dict[str, Any]]],
    reach_count: dict[str, dict[str, int]],
    n_sims: int,
    total_first_round_upsets: int,
    total_number_1_seeds_in_final_four: int
) -> None:
    """Log aggregate simulation diagnostics against historical references."""
    if n_sims <= 0:
        return

    team_seed_lookup: dict[str, int] = {}
    seed_entry_counts: dict[int, int] = defaultdict(int)
    for teams in normalized_bracket.values():
        for team in teams:
            name = str(team.get("Team", ""))
            seed = int(team.get("Seed", 16))
            team_seed_lookup[name] = seed
            seed_entry_counts[seed] += 1

    def seed_round_rate(seed: int, round_name: str) -> float:
        entrants = seed_entry_counts.get(seed, 0)
        if entrants == 0:
            return 0.0
        total_advancements = 0
        for team_name, team_seed in team_seed_lookup.items():
            if team_seed != seed:
                continue
            total_advancements += int(reach_count.get(team_name, {}).get(round_name, 0))
        return float(total_advancements) / float(entrants * n_sims)

    avg_first_round_upsets = float(total_first_round_upsets) / float(n_sims)
    avg_number_1_seeds_in_final_four = float(total_number_1_seeds_in_final_four) / float(n_sims)

    log.info(
        "Historical calibration diagnostics: "
        "R64 upsets(seeds10-16)=%.2f (target 6.50), "
        "avg #1 seeds in F4=%.2f (target 1.65)",
        avg_first_round_upsets,
        avg_number_1_seeds_in_final_four,
    )

    for seed in (1, 2, 10, 11, 12, 13, 14, 15, 16):
        historical = HISTORICAL_ADVANCEMENT_RATES.get(seed)
        if not historical:
            continue
        comparisons = []
        for round_name in ("R32", "S16", "E8", "F4", "Championship", "Champion"):
            if round_name not in historical:
                continue
            sim_rate = seed_round_rate(seed, round_name)
            comparisons.append(f"{round_name}={sim_rate:.3f} (target {historical[round_name]:.3f})")
        log.info("Seed %s advancement diagnostics: %s", seed, ", ".join(comparisons))


def simulate_bracket(
    bracket: dict[str, list[dict[str, Any]]],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    n_sims: int = 10000,
    seed: int = 42
) -> dict[str, dict[str, float]]:
    """Run full tournament simulation and return advancement probabilities."""
    random.seed(seed)
    np.random.seed(seed)

    regions = list(bracket.keys())
    normalized_bracket = {
        region: [_normalize_team_key(team) for team in teams] for region, teams in bracket.items()
    }

    reach_count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_first_round_upsets = 0
    total_number_1_seeds_in_final_four = 0

    for _ in range(n_sims):
        region_winners: list[dict[str, Any]] = []
        for region in regions:
            teams = list(normalized_bracket[region])

            r32_teams = []
            for slot_a, slot_b in FIRST_ROUND_MATCHUPS:
                winner = _play_game(teams[slot_a], teams[slot_b], win_prob_fn, reach_count, "R32")
                r32_teams.append(winner)
                if int(winner.get("Seed", 16)) >= 10:
                    total_first_round_upsets += 1

            s16_teams = []
            for i in range(0, len(r32_teams), 2):
                winner = _play_game(r32_teams[i], r32_teams[i + 1], win_prob_fn, reach_count, "S16")
                s16_teams.append(winner)

            e8_teams = []
            for i in range(0, len(s16_teams), 2):
                winner = _play_game(s16_teams[i], s16_teams[i + 1], win_prob_fn, reach_count, "E8")
                e8_teams.append(winner)

            region_winner = _play_game(e8_teams[0], e8_teams[1], win_prob_fn, reach_count, "F4")
            region_winners.append(region_winner)

        total_number_1_seeds_in_final_four += sum(
            1 for team in region_winners if int(team.get("Seed", 16)) == 1
        )

        f4_winner_1 = _play_game(region_winners[0], region_winners[1], win_prob_fn, reach_count, "Championship")
        f4_winner_2 = _play_game(region_winners[2], region_winners[3], win_prob_fn, reach_count, "Championship")
        _play_game(f4_winner_1, f4_winner_2, win_prob_fn, reach_count, "Champion")

    for teams in normalized_bracket.values():
        for team in teams:
            reach_count[str(team.get("Team"))]["R64"] = n_sims

    _log_historical_diagnostics(
        normalized_bracket,
        reach_count,
        n_sims,
        total_first_round_upsets,
        total_number_1_seeds_in_final_four,
    )

    result: dict[str, dict[str, float]] = {}
    for team_name, rounds in reach_count.items():
        team_result = {round_name: 0.0 for round_name in ROUND_NAMES}
        for round_name, count in rounds.items():
            team_result[round_name] = float(count) / float(n_sims)
        result[team_name] = team_result
    return result


def generate_modal_bracket(
    simulation_results: dict[str, dict[str, float]],
    bracket: dict[str, list[dict[str, Any]]],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Generate deterministic modal bracket by always taking higher win probability."""
    regions = list(bracket.keys())
    normalized = {r: [_normalize_team_key(t) for t in teams] for r, teams in bracket.items()}
    modal: dict[str, dict[str, list[dict[str, Any]]]] = {}

    region_winners: list[dict[str, Any]] = []
    for region in regions:
        modal[region] = {"R64": [], "R32": [], "S16": [], "E8": []}
        teams = normalized[region]

        r32_teams = []
        for slot_a, slot_b in FIRST_ROUND_MATCHUPS:
            a, b = teams[slot_a], teams[slot_b]
            p_a = float(win_prob_fn(a, b))
            winner = a if p_a >= 0.5 else b
            modal[region]["R64"].append({"team_a": a["Team"], "team_b": b["Team"], "winner": winner["Team"], "prob": max(p_a, 1 - p_a)})
            r32_teams.append(winner)

        s16_teams = []
        for i in range(0, len(r32_teams), 2):
            a, b = r32_teams[i], r32_teams[i + 1]
            p_a = float(win_prob_fn(a, b))
            winner = a if p_a >= 0.5 else b
            modal[region]["R32"].append({"team_a": a["Team"], "team_b": b["Team"], "winner": winner["Team"], "prob": max(p_a, 1 - p_a)})
            s16_teams.append(winner)

        e8_teams = []
        for i in range(0, len(s16_teams), 2):
            a, b = s16_teams[i], s16_teams[i + 1]
            p_a = float(win_prob_fn(a, b))
            winner = a if p_a >= 0.5 else b
            modal[region]["S16"].append({"team_a": a["Team"], "team_b": b["Team"], "winner": winner["Team"], "prob": max(p_a, 1 - p_a)})
            e8_teams.append(winner)

        a, b = e8_teams[0], e8_teams[1]
        p_a = float(win_prob_fn(a, b))
        winner = a if p_a >= 0.5 else b
        modal[region]["E8"].append({"team_a": a["Team"], "team_b": b["Team"], "winner": winner["Team"], "prob": max(p_a, 1 - p_a)})
        region_winners.append(winner)

    p_a = float(win_prob_fn(region_winners[0], region_winners[1]))
    winner_ff1 = region_winners[0] if p_a >= 0.5 else region_winners[1]
    p_b = float(win_prob_fn(region_winners[2], region_winners[3]))
    winner_ff2 = region_winners[2] if p_b >= 0.5 else region_winners[3]
    p_c = float(win_prob_fn(winner_ff1, winner_ff2))
    champion = winner_ff1 if p_c >= 0.5 else winner_ff2

    return {
        "regions": modal,
        "final_four": [winner_ff1["Team"], winner_ff2["Team"]],
        "champion": champion["Team"],
        "simulation_results": simulation_results
    }

