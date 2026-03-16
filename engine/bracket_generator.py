"""Deterministic bracket generation across model strategies."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

import numpy as np

from engine import FIRST_ROUND_MATCHUPS, order_final_four_regions
from engine.scoring import load_strategy_configs
from engine.win_probability import apply_fraud_adjustment


def _team_name(team: dict[str, Any]) -> str:
    return str(team.get("Team", team.get("team")))


def strategy_win_prob(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    strategy: dict[str, Any],
    model_scores: dict[str, dict[str, float]],
    base_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> float:
    """Calculate strategy-adjusted probability that team_a wins.

    Adds a model-score ratio adjustment (±20% max) on top of the
    AdjEM-based win probability. The ratio measures which team the
    strategy's blended model prefers; the ±20% cap keeps extreme
    seed mismatches safe while giving strategies real influence over
    outcomes across multiple bracket rounds.
    """
    base_prob = float(base_prob_fn(team_a, team_b))
    blends = strategy.get("model_blends", {})

    name_a = _team_name(team_a)
    name_b = _team_name(team_b)
    score_a = sum(float(weight) * float(model_scores.get(name_a, {}).get(model, 50.0)) for model, weight in blends.items())
    score_b = sum(float(weight) * float(model_scores.get(name_b, {}).get(model, 50.0)) for model, weight in blends.items())

    if score_a + score_b > 0:
        ratio_adj = (score_a / (score_a + score_b) - 0.5) * 1.0
        ratio_adj = float(np.clip(ratio_adj, -0.20, 0.20))
    else:
        ratio_adj = 0.0

    adjusted = float(np.clip(base_prob + ratio_adj, 0.03, 0.97))

    if "cinderella_boost" in strategy:
        boost = float(strategy["cinderella_boost"])
        seed_a = int(team_a.get("Seed", 16))
        seed_b = int(team_b.get("Seed", 16))
        cind_a = float(team_a.get("CinderellaScore") or 0.0)
        cind_b = float(team_b.get("CinderellaScore") or 0.0)
        if cind_b > 0.50 and seed_b > seed_a:
            adjusted = float(np.clip(adjusted - boost, 0.03, 0.97))
        elif cind_a > 0.50 and seed_a > seed_b:
            adjusted = float(np.clip(adjusted + boost, 0.03, 0.97))

    favorite = team_a if int(team_a.get("Seed", 16)) <= int(team_b.get("Seed", 16)) else team_b
    if _team_name(favorite) == _team_name(team_a):
        adjusted = apply_fraud_adjustment(adjusted, favorite, strategy.get("name", "standard"))
    else:
        adjusted = 1.0 - apply_fraud_adjustment(1.0 - adjusted, favorite, strategy.get("name", "standard"))
    return float(np.clip(adjusted, 0.03, 0.97))


def simulate_matchup_strategy(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    strategy: dict[str, Any],
    model_scores: dict[str, dict[str, float]],
    base_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> dict[str, Any]:
    """Resolve a deterministic matchup for a strategy."""
    prob_a = strategy_win_prob(team_a, team_b, strategy, model_scores, base_prob_fn)
    favorite = team_a if int(team_a.get("Seed", 16)) <= int(team_b.get("Seed", 16)) else team_b
    underdog = team_b if _team_name(favorite) == _team_name(team_a) else team_a
    fav_prob = prob_a if _team_name(favorite) == _team_name(team_a) else 1.0 - prob_a

    threshold = float(strategy.get("upset_threshold", 0.4))
    is_upset = (1.0 - fav_prob) > threshold
    if int(underdog.get("Seed", 16)) == 16 and int(favorite.get("Seed", 1)) == 1:
        is_upset = False

    winner = underdog if is_upset else favorite
    winner_prob = (1.0 - fav_prob) if is_upset else fav_prob
    return {
        "winner": winner,
        "winner_prob": round(float(winner_prob), 3),
        "is_upset": bool(is_upset),
        "team_a_prob": round(float(prob_a), 3)
    }


def _play_round(
    teams: list[dict[str, Any]],
    strategy: dict[str, Any],
    model_scores: dict[str, dict[str, float]],
    base_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    games: list[dict[str, Any]] = []
    winners: list[dict[str, Any]] = []
    for i in range(0, len(teams), 2):
        team_a, team_b = teams[i], teams[i + 1]
        result = simulate_matchup_strategy(team_a, team_b, strategy, model_scores, base_prob_fn)
        winner = result["winner"]
        winners.append(winner)
        games.append(
            {
                "higher_seed_team": _team_name(team_a if int(team_a.get("Seed", 16)) <= int(team_b.get("Seed", 16)) else team_b),
                "lower_seed_team": _team_name(team_b if int(team_a.get("Seed", 16)) <= int(team_b.get("Seed", 16)) else team_a),
                "higher_seed_seed": int(min(team_a.get("Seed", 16), team_b.get("Seed", 16))),
                "lower_seed_seed": int(max(team_a.get("Seed", 16), team_b.get("Seed", 16))),
                "predicted_winner": _team_name(winner),
                "win_probability": result["winner_prob"],
                "is_upset": result["is_upset"],
                "upset_flag": "⚡" if result["is_upset"] else None,
                "fraud_flag": "💀" if float(winner.get("FraudScore") or 0.0) >= 0.4 else None,
                "cinderella_flag": "🔴" if float(winner.get("CinderellaScore") or 0.0) >= 0.55 else None
            }
        )
    return winners, games


def generate_bracket(
    teams_by_region: dict[str, list[dict[str, Any]]],
    strategy_name: str,
    strategy_config: dict[str, Any],
    model_scores: dict[str, dict[str, float]],
    base_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> dict[str, Any]:
    """Generate full deterministic bracket for one strategy."""
    strategy = {**strategy_config, "name": strategy_name}
    rounds: dict[str, dict[str, list[dict[str, Any]]]] = {}
    region_winners: dict[str, dict[str, Any]] = {}
    region_order = list(teams_by_region.keys())
    final_four_regions = order_final_four_regions(region_order)
    for region, teams in teams_by_region.items():
        region_teams = sorted(teams, key=lambda t: int(t.get("slot", 99)))
        ordered_first_round = []
        for a, b in FIRST_ROUND_MATCHUPS:
            ordered_first_round.extend([region_teams[a], region_teams[b]])
        r32_winners, r64_games = _play_round(ordered_first_round, strategy, model_scores, base_prob_fn)
        s16_winners, r32_games = _play_round(r32_winners, strategy, model_scores, base_prob_fn)
        e8_winners, s16_games = _play_round(s16_winners, strategy, model_scores, base_prob_fn)
        regional_winner_list, e8_games = _play_round(e8_winners, strategy, model_scores, base_prob_fn)
        region_winner = regional_winner_list[0]
        region_winners[region] = region_winner
        rounds[region] = {"R64": r64_games, "R32": r32_games, "S16": s16_games, "E8": e8_games}

    final_four_teams = [region_winners[region] for region in final_four_regions]
    ff_winners, ff_games = _play_round(final_four_teams, strategy, model_scores, base_prob_fn)
    champion_list, championship_game = _play_round(ff_winners, strategy, model_scores, base_prob_fn)
    champion = champion_list[0]

    return {
        "strategy": strategy_name,
        "description": strategy.get("description", ""),
        "champion": _team_name(champion),
        "runner_up": (championship_game[0]["lower_seed_team"]
                      if _team_name(champion) == championship_game[0]["higher_seed_team"]
                      else championship_game[0]["higher_seed_team"]),
        "final_four": [_team_name(region_winners[region]) for region in final_four_regions],
        "rounds": rounds,
        "final_four_games": ff_games,
        "championship_game": championship_game
    }


def generate_all_brackets(
    teams_by_region: dict[str, list[dict[str, Any]]],
    model_scores: dict[str, dict[str, float]],
    simulation_results: dict[str, dict[str, float]],
    base_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float]
) -> dict[str, dict[str, Any]]:
    """Generate all strategy brackets from config file."""
    strategy_configs = load_strategy_configs()
    results: dict[str, dict[str, Any]] = {}
    for strategy_name, strategy in strategy_configs.items():
        bracket = generate_bracket(teams_by_region, strategy_name, strategy, model_scores, base_prob_fn)
        bracket["simulation_results"] = simulation_results
        results[strategy_name] = bracket
    return results


def generate_bracket_summary(all_brackets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute strategy consensus summary."""
    champion_counter = Counter()
    final_four_counter = Counter()
    for bracket in all_brackets.values():
        champion = bracket.get("champion")
        if champion:
            champion_counter[champion] += 1
        for team in bracket.get("final_four", []):
            final_four_counter[team] += 1
    champion_consensus = champion_counter.most_common(1)[0][0] if champion_counter else ""
    final_four_consensus = [team for team, _ in final_four_counter.most_common(4)]
    return {
        "champion_consensus": champion_consensus,
        "champion_counts": dict(champion_counter),
        "final_four_consensus": final_four_consensus,
        "final_four_counts": dict(final_four_counter),
        "n_strategies": len(all_brackets)
    }

