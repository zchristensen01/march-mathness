"""Win probability and matchup utilities."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

NATIONAL_AVG_TEMPO = 68.0
BASE_GAME_STD = 11.0
BARTHAG_LOG5_WEIGHT = 0.15

HISTORICAL_FIRST_ROUND_RATES: dict[tuple[int, int], float] = {
    (1, 16): 0.988,
    (2, 15): 0.931,
    (3, 14): 0.856,
    (4, 13): 0.794,
    (5, 12): 0.644,
    (6, 11): 0.613,
    (7, 10): 0.613,
    (8, 9): 0.481,
}

HISTORICAL_ADVANCEMENT_RATES: dict[int, dict[str, float]] = {
    1: {
        "R32": 0.988,
        "S16": 0.850,
        "E8": 0.669,
        "F4": 0.413,
        "Championship": 0.256,
        "Champion": 0.163,
    },
    2: {
        "R32": 0.931,
        "S16": 0.644,
        "E8": 0.394,
        "F4": 0.200,
        "Champion": 0.113,
    },
    10: {"R32": 0.388, "S16": 0.150, "E8": 0.056, "F4": 0.006},
    11: {"R32": 0.388, "S16": 0.169, "E8": 0.063, "F4": 0.038},
    12: {"R32": 0.356, "S16": 0.138, "E8": 0.013, "F4": 0.000},
    13: {"R32": 0.206, "S16": 0.038, "E8": 0.000, "F4": 0.000},
    14: {"R32": 0.144, "S16": 0.013, "E8": 0.000, "F4": 0.000},
    15: {"R32": 0.069, "S16": 0.025, "E8": 0.006, "F4": 0.000},
    16: {"R32": 0.013, "S16": 0.000, "E8": 0.000, "F4": 0.000},
}


def _clip_probability(prob: float) -> float:
    return float(np.clip(prob, 0.03, 0.97))


def _as_float(value: Any, default: float) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(out):
        return default
    return out


def expected_possessions(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """KenPom-style multiplicative neutral-court tempo estimate."""
    tempo_a = _as_float(team_a.get("Adj_T"), NATIONAL_AVG_TEMPO)
    tempo_b = _as_float(team_b.get("Adj_T"), NATIONAL_AVG_TEMPO)
    possessions = (tempo_a * tempo_b) / NATIONAL_AVG_TEMPO
    return max(50.0, min(85.0, possessions))


def _tempo_adjusted_game_std(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """Scale point spread variance by pace to avoid over-amplifying tempo effects."""
    pace_factor = np.sqrt(expected_possessions(team_a, team_b) / NATIONAL_AVG_TEMPO)
    return BASE_GAME_STD * float(pace_factor)


def predicted_spread(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """Expected point differential for team_a."""
    possessions = expected_possessions(team_a, team_b)
    adjem_diff = _as_float(team_a.get("AdjEM"), 0.0) - _as_float(team_b.get("AdjEM"), 0.0)
    return float(adjem_diff * possessions / 100.0)


def win_probability(team_a: dict[str, Any], team_b: dict[str, Any], game_std: float = 11.0) -> float:
    """Normal-CDF-based neutral-court win probability."""
    spread = predicted_spread(team_a, team_b)
    std = _tempo_adjusted_game_std(team_a, team_b) if abs(game_std - BASE_GAME_STD) < 1e-6 else max(1e-6, game_std)
    prob = norm.cdf(spread / std)
    return _clip_probability(float(prob))


def win_probability_elo_style(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """FiveThirtyEight-style Elo logistic mapping from AdjEM difference."""
    diff = _as_float(team_a.get("AdjEM", 0.0), 0.0) - _as_float(team_b.get("AdjEM", 0.0), 0.0)
    prob = 1.0 / (1.0 + 10 ** (-diff * 30.464 / 400.0))
    return _clip_probability(float(prob))


def blended_win_probability(team_a: dict[str, Any], team_b: dict[str, Any]) -> float:
    """Primary blend: 60% normal CDF + 40% Elo style."""
    p_normal = win_probability(team_a, team_b)
    p_elo = win_probability_elo_style(team_a, team_b)
    blended = 0.60 * p_normal + 0.40 * p_elo
    p_log5 = barthag_log5_probability(team_a, team_b)
    if p_log5 is not None:
        blended = (1.0 - BARTHAG_LOG5_WEIGHT) * blended + BARTHAG_LOG5_WEIGHT * p_log5
    return _clip_probability(blended)


def barthag_log5_probability(team_a: dict[str, Any], team_b: dict[str, Any]) -> float | None:
    """Optional BartTorvik-style Log5 adjustment when both Barthag values exist."""
    p_a = _as_float(team_a.get("Barthag"), -1.0)
    p_b = _as_float(team_b.get("Barthag"), -1.0)
    if not (0.0 < p_a < 1.0 and 0.0 < p_b < 1.0):
        return None
    denom = p_a + p_b - 2.0 * p_a * p_b
    if abs(denom) < 1e-9:
        return None
    return _clip_probability((p_a - p_a * p_b) / denom)


def apply_historical_seed_prior(
    model_prob_a: float,
    seed_a: int,
    seed_b: int,
    prior_weight: float = 0.15
) -> float:
    """Calibrate model probability with historical seed matchup priors."""
    fav_seed = min(seed_a, seed_b)
    dog_seed = max(seed_a, seed_b)
    key = (fav_seed, dog_seed)

    # First-round canonical matchup types (seeds sum to 17) are anchored
    # directly to historical win rates while preserving team-specific signal.
    if key in HISTORICAL_FIRST_ROUND_RATES:
        historical_fav_rate = HISTORICAL_FIRST_ROUND_RATES[key]
        historical_a_rate = historical_fav_rate if seed_a == fav_seed else 1.0 - historical_fav_rate
        dampening = 0.5
        calibrated = historical_a_rate + (model_prob_a - historical_a_rate) * dampening
        return _clip_probability(calibrated)

    # For later-round/non-canonical matchups, apply a light seed-gap prior.
    seed_gap = max(0, dog_seed - fav_seed)
    fav_prior = min(0.95, 0.5 + seed_gap * 0.032)
    prior_for_a = fav_prior if seed_a == fav_seed else 1.0 - fav_prior
    blended = (1.0 - prior_weight) * model_prob_a + prior_weight * prior_for_a
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
    with_seed_prior = apply_historical_seed_prior(
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

