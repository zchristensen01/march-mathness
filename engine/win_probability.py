"""Win probability and matchup utilities."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

ERA_SEED_PRIOR_FOR_UNDERDOG: dict[tuple[int, int], float] = {
    (6, 11): 0.52,
    (7, 10): 0.41,
    (8, 9): 0.625
}


def _clip_probability(prob: float) -> float:
    return float(np.clip(prob, 0.03, 0.97))


def predicted_spread(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """Expected point differential for team_a."""
    tempo_avg = (float(team_a.get("Adj_T", 68.0)) + float(team_b.get("Adj_T", 68.0))) / 2.0
    return float((float(team_a.get("AdjEM", 0.0)) - float(team_b.get("AdjEM", 0.0))) * tempo_avg / 100.0)


def win_probability(team_a: dict[str, Any], team_b: dict[str, Any], game_std: float = 11.0) -> float:
    """Normal-CDF-based neutral-court win probability."""
    spread = predicted_spread(team_a, team_b)
    prob = norm.cdf(spread / game_std)
    return _clip_probability(float(prob))


def win_probability_elo_style(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """FiveThirtyEight-style Elo logistic mapping from AdjEM difference."""
    diff = float(team_a.get("AdjEM", 0.0)) - float(team_b.get("AdjEM", 0.0))
    prob = 1.0 / (1.0 + 10 ** (-diff * 30.464 / 400.0))
    return _clip_probability(float(prob))


def blended_win_probability(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """Primary blend: 60% normal CDF + 40% Elo style."""
    p_normal = win_probability(team_a, team_b)
    p_elo = win_probability_elo_style(team_a, team_b)
    return _clip_probability(0.60 * p_normal + 0.40 * p_elo)


def apply_era_seed_prior(
    model_prob_a: float,
    seed_a: int,
    seed_b: int,
    prior_weight: float = 0.15
) -> float:
    """Blend model probability with era-adjusted historical seed priors."""
    fav_seed = min(seed_a, seed_b)
    dog_seed = max(seed_a, seed_b)
    key = (fav_seed, dog_seed)
    if key not in ERA_SEED_PRIOR_FOR_UNDERDOG:
        return _clip_probability(model_prob_a)
    era_prior_fav = 1.0 - ERA_SEED_PRIOR_FOR_UNDERDOG[key]
    era_prior_a = era_prior_fav if seed_a == fav_seed else 1.0 - era_prior_fav
    blended = (1.0 - prior_weight) * model_prob_a + prior_weight * era_prior_a
    return _clip_probability(blended)


def apply_play_in_boost(
    base_prob: float,
    team: dict[str, Any],
    opponent: dict[str, Any],
    round_number: int
) -> float:
    """Apply +/-3% first-round boost for play-in winners."""
    if round_number != 1:
        return _clip_probability(base_prob)
    team_play_in = int(team.get("Won_Play_In", 0))
    opp_play_in = int(opponent.get("Won_Play_In", 0))
    if team_play_in and not opp_play_in:
        return _clip_probability(base_prob + 0.03)
    if opp_play_in and not team_play_in:
        return _clip_probability(base_prob - 0.03)
    return _clip_probability(base_prob)


def production_win_probability(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    round_number: int = 1
) -> float:
    """Production probability path used by simulation and bracket generation."""
    base = blended_win_probability(team_a, team_b)
    with_seed_prior = apply_era_seed_prior(
        base,
        int(team_a.get("Seed", 8)),
        int(team_b.get("Seed", 8))
    )
    with_play_in = apply_play_in_boost(with_seed_prior, team_a, team_b, round_number)
    return _clip_probability(with_play_in)


def confidence_tier(prob: float) -> str:
    """Human-readable confidence tier."""
    if prob >= 0.85:
        return "Strong Favorite"
    if prob >= 0.70:
        return "Moderate Favorite"
    if prob >= 0.55:
        return "Slight Favorite"
    if prob >= 0.45:
        return "Toss-Up"
    return "Underdog"


def apply_fraud_adjustment(win_prob: float, favorite: dict[str, Any], strategy: str) -> float:
    """Reduce favorite probability in upset-seeking strategies."""
    if strategy not in {"upsets", "cinderella", "analytics"}:
        return _clip_probability(win_prob)
    fraud_score = float(favorite.get("FraudScore") or 0.0)
    reduction = fraud_score * 0.08
    return _clip_probability(win_prob - reduction)


def all_matchup_probabilities(teams: list[dict[str, Any]]) -> pd.DataFrame:
    """Return matrix of P(row team beats col team)."""
    names = [str(team.get("Team", team.get("team"))) for team in teams]
    matrix = np.zeros((len(teams), len(teams)))
    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if i == j:
                matrix[i, j] = 0.5
            else:
                matrix[i, j] = production_win_probability(team_a, team_b)
    return pd.DataFrame(matrix, index=names, columns=names)

