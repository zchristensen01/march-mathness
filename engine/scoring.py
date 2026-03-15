"""Scoring engine for rankings, Cinderella, and Fraud models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from engine.normalization import normalize_inverse, normalize_value

PROGRAM_PRESTIGE: dict[str, int] = {
    "Kansas": 10,
    "Kentucky": 10,
    "Duke": 10,
    "North Carolina": 9,
    "Connecticut": 9,
    "Gonzaga": 8,
    "Michigan State": 8,
    "Arizona": 8,
    "UCLA": 8,
    "Villanova": 8
}

SEED_TO_RANK_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 5),
    2: (5, 10),
    3: (10, 16),
    4: (16, 26),
    5: (26, 36),
    6: (36, 50),
    7: (50, 65),
    8: (65, 80),
    9: (80, 100),
    10: (100, 125),
    11: (125, 155),
    12: (155, 185),
    13: (185, 225),
    14: (225, 275),
    15: (275, 330),
    16: (330, 365)
}

FRAUD_CONFERENCE_PENALTIES: dict[str, float] = {
    "B10": 0.65,
    "ACC": 0.25,
    "BE": 0.20,
    "MWC": 0.30,
    "Big12": 0.00,
    "SEC": 0.00
}

MODEL_NAME_TO_COLUMN: dict[str, str] = {
    "default": "PowerScore",
    "defensive": "DefensiveScore",
    "offensive": "OffensiveScore",
    "momentum": "MomentumScore",
    "giant_killer": "GiantKillerScore",
    "cinderella_tournament": "CinderellaTournamentScore",
    "favorites": "FavoritesScore",
    "analytics": "AnalyticsScore",
    "experience": "ExperienceScore"
}

RANKING_COLUMN_ORDER: list[str] = [
    "Rank",
    "Team",
    "Seed",
    "Conference",
    "Record",
    "PowerScore",
    "ModelScore",
    "AdjEM",
    "AdjO",
    "AdjD",
    "Barthag",
    "eFG%",
    "Opp_eFG%",
    "TO%",
    "Opp_TO%",
    "OR%",
    "DR%",
    "FTR",
    "FT%",
    "SOS",
    "Adj_T",
    "WAB",
    "Torvik_Rank",
    "NET_Rank",
    "CompRank",
    "AP_Poll_Rank",
    "Exp",
    "Coach_Tourney_Experience",
    "Program_Prestige",
    "Last_10_Games_Metric",
    "Luck",
    "CinderellaScore",
    "CinderellaAlertLevel",
    "SeedMismatch",
    "FraudScore",
    "FraudLevel",
    "FraudExplanation",
    "Consistency_Score",
    "Volatility_Score",
    "CSI",
    "CSI_multiplier",
    "Strengths",
    "OverrideActive"
]


def load_weights(path: str = "models/weights.json") -> dict[str, dict[str, float]]:
    """Load model weights from JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Weights file not found: {path}")
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("models", {})


def load_strategy_configs(path: str = "models/weights.json") -> dict[str, dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Weights file not found: {path}")
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("strategies", {})


def implied_seed(comp_rank: int) -> int:
    """Return implied seed from composite ranking."""
    for seed, (lo, hi) in SEED_TO_RANK_RANGES.items():
        if lo <= comp_rank < hi:
            return seed
    return 16


def seed_mismatch(actual_seed: int, comp_rank: int) -> float:
    """Positive means underseeded."""
    implied = implied_seed(comp_rank)
    raw = actual_seed - implied
    return float(np.clip(raw / 10.0, 0.0, 1.0))


def score_team(
    norm: dict[str, float],
    derived: dict[str, float],
    weights: dict[str, float],
    csi_multiplier: float
) -> float:
    """Calculate weighted score in [0, 100] then apply CSI."""
    score = 0.0
    for feature, weight in weights.items():
        if feature in norm:
            score += weight * norm[feature]
        elif feature in derived:
            score += weight * derived[feature]
        else:
            score += weight * 0.5
    score *= 100.0
    score *= csi_multiplier
    return round(float(score), 1)


def score_all_teams(
    df: pd.DataFrame,
    norms: list[dict[str, float]],
    deriveds: list[dict[str, float]],
    csi_multipliers: list[float],
    model_name: str,
    weights_lookup: dict[str, dict[str, float]] | None = None
) -> pd.Series:
    """Score all teams with a chosen model."""
    models = weights_lookup if weights_lookup is not None else load_weights()
    weights = models[model_name]
    scores = [
        score_team(norms[i], deriveds[i], weights, float(csi_multipliers[i]))
        for i in range(len(df))
    ]
    return pd.Series(scores, index=df.index)


def compute_cinderella_score(team: dict[str, Any], norm: dict[str, float]) -> dict[str, Any]:
    """Compute 6-component Cinderella score for seeds >= 9."""
    seed = int(team.get("Seed", 16))
    if seed < 9:
        return {"CinderellaScore": None, "CinderellaAlertLevel": ""}

    comp_rank = int(team.get("CompRank") or team.get("Torvik_Rank") or 200)
    seed_mis = seed_mismatch(seed, comp_rank)

    defensive_proxy_rank = int(team.get("Torvik_Rank", 200))
    if defensive_proxy_rank <= 40:
        defense_signal = 1.0
    elif defensive_proxy_rank <= 80:
        defense_signal = 0.65
    elif defensive_proxy_rank <= 120:
        defense_signal = 0.35
    else:
        defense_signal = 0.0
    if comp_rank <= 40 and defense_signal < 0.65:
        defense_signal = 0.65

    tov_margin_score = norm.get("Opp_TO%", 0.5) * 0.6 + norm.get("TO%_inv", 0.5) * 0.4
    exp_score = norm.get("Exp", 0.5)
    tempo_score = normalize_inverse(float(team.get("Adj_T", 68.0)), 60, 80)
    reb_score = norm.get("OR%", 0.5)

    cinderella_score = (
        0.30 * seed_mis
        + 0.25 * defense_signal
        + 0.20 * tov_margin_score
        + 0.10 * exp_score
        + 0.08 * tempo_score
        + 0.07 * reb_score
    )

    if cinderella_score >= 0.55:
        alert = "HIGH"
    elif cinderella_score >= 0.40:
        alert = "WATCH"
    else:
        alert = ""

    return {
        "CinderellaScore": round(float(cinderella_score), 3),
        "CinderellaAlertLevel": alert,
        "C_SeedMismatch": round(float(seed_mis), 3),
        "C_Defense": round(float(defense_signal), 3),
        "C_Turnover": round(float(tov_margin_score), 3),
        "C_Experience": round(float(exp_score), 3),
        "C_Tempo": round(float(tempo_score), 3),
        "C_Rebounding": round(float(reb_score), 3)
    }


def compute_fraud_score(team: dict[str, Any], norm: dict[str, float]) -> dict[str, Any]:
    """Compute 7-component Fraud score for seeds <= 6."""
    seed = int(team.get("Seed", 16))
    if seed > 6:
        return {"FraudScore": None, "FraudLevel": ""}

    comp_rank = int(team.get("CompRank") or team.get("Torvik_Rank") or 50)
    implied = implied_seed(comp_rank)
    overseeded_gap = implied - seed
    seed_deviation_score = float(np.clip(overseeded_gap / 4.0, 0.0, 1.0))

    adj_o = norm.get("AdjO", 0.5)
    adj_d = norm.get("AdjD_inv", norm.get("AdjD", 0.5))
    imbalance = max(0.0, adj_o - adj_d)
    imbalance_score = min(1.0, imbalance / 0.35)
    if int(team.get("Torvik_Rank", 50)) > 40:
        imbalance_score = max(imbalance_score, 0.70)

    wins = float(team.get("Wins", 20))
    games = max(float(team.get("Games", 30)), 1.0)
    season_winpct = wins / games
    recent_form = float(team.get("Last_10_Games_Metric", season_winpct))
    form_drop = max(0.0, season_winpct - recent_form)
    form_collapse_score = min(1.0, form_drop / 0.25)

    luck = float(team.get("Luck", 0.0))
    luck_score = normalize_value(luck, -0.05, 0.10)

    three_pt_rate = norm.get("3P_Rate", 0.5)
    consistency = norm.get("Consistency_Score", 0.5)
    variance_score = 0.6 * three_pt_rate + 0.4 * (1.0 - consistency)

    star = float(team.get("Star_Player_Index", 5.0))
    bench = float(team.get("Bench_Minutes_Pct", 30.0))
    star_norm = normalize_value(star, 1, 10)
    bench_norm = normalize_value(bench, 20, 55)
    dependence_score = min(1.0, max(0.0, star_norm - bench_norm * 0.7))

    conf = str(team.get("Conference", "Unknown"))
    conf_fraud = FRAUD_CONFERENCE_PENALTIES.get(conf, 0.15)

    if float(team.get("Adj_T", 68.0)) < 65.0 and seed <= 4:
        imbalance_score = min(1.0, imbalance_score + 0.10)

    fraud_score = (
        0.25 * seed_deviation_score
        + 0.25 * imbalance_score
        + 0.15 * form_collapse_score
        + 0.15 * luck_score
        + 0.10 * variance_score
        + 0.05 * dependence_score
        + 0.05 * conf_fraud
    )

    if fraud_score >= 0.60:
        level = "HIGH"
    elif fraud_score >= 0.40:
        level = "MEDIUM"
    elif fraud_score >= 0.25:
        level = "LOW"
    else:
        level = ""

    return {
        "FraudScore": round(float(fraud_score), 3),
        "FraudLevel": level,
        "F_SeedDeviation": round(float(seed_deviation_score), 3),
        "F_Imbalance": round(float(imbalance_score), 3),
        "F_FormCollapse": round(float(form_collapse_score), 3),
        "F_Luck": round(float(luck_score), 3),
        "F_Variance": round(float(variance_score), 3),
        "F_StarDependence": round(float(dependence_score), 3),
        "F_Conference": round(float(conf_fraud), 3)
    }


def get_fraud_explanation(team: dict[str, Any], fraud_result: dict[str, Any]) -> str:
    """Build plain-language fraud explanation."""
    if fraud_result.get("FraudScore") is None:
        return ""
    reasons: list[str] = []
    if fraud_result.get("F_SeedDeviation", 0) >= 0.50:
        reasons.append("overseeded versus composite rank")
    if fraud_result.get("F_Imbalance", 0) >= 0.60:
        reasons.append("offense-defense imbalance")
    if fraud_result.get("F_FormCollapse", 0) >= 0.50:
        reasons.append("late-season form collapse")
    if fraud_result.get("F_Luck", 0) >= 0.55:
        reasons.append("positive luck likely to regress")
    if fraud_result.get("F_Variance", 0) >= 0.60:
        reasons.append("high-variance style")
    if fraud_result.get("F_Conference", 0) >= 0.55:
        reasons.append(f"{team.get('Conference', 'conference')} historical underperformance")
    if fraud_result.get("F_StarDependence", 0) >= 0.60:
        reasons.append("single-player dependence")
    if not reasons:
        return "Mild concerns, no single major red flag."
    return "Fraud risk: " + "; ".join(reasons) + "."


def get_team_strengths(team: dict[str, Any]) -> list[str]:
    """Return up to 4 readable team strength labels."""
    strengths: list[str] = []
    if float(team.get("eFG%", 0)) >= 56:
        strengths.append("elite shooting efficiency")
    elif float(team.get("eFG%", 0)) >= 53:
        strengths.append("above-avg shooting")
    if float(team.get("3P%", 0)) >= 38:
        strengths.append("elite 3-point shooting")
    if float(team.get("AdjO", 0)) >= 120:
        strengths.append("elite offense")
    if float(team.get("OR%", 0)) >= 35:
        strengths.append("dominant offensive rebounding")
    if float(team.get("FT%", 0)) >= 78:
        strengths.append("excellent free throw shooting")
    if float(team.get("AST_TO", 0)) >= 1.8:
        strengths.append("exceptional ball movement")
    if float(team.get("AdjD", 999)) <= 92:
        strengths.append("elite defense")
    elif float(team.get("AdjD", 999)) <= 96:
        strengths.append("above-avg defense")
    if float(team.get("Opp_eFG%", 100)) <= 46:
        strengths.append("stifling perimeter defense")
    if float(team.get("Opp_TO%", 0)) >= 22:
        strengths.append("forces turnovers")
    if float(team.get("Blk_%", 0)) >= 12:
        strengths.append("shot-blocking presence")
    if float(team.get("Last_10_Games_Metric", 0)) >= 0.85:
        strengths.append("red-hot form")
    if float(team.get("Exp", 0)) >= 2.3:
        strengths.append("veteran squad")
    if float(team.get("Quad1_Wins", 0)) >= 8:
        strengths.append("battle-tested (Q1 wins)")
    if float(team.get("Eff_Hgt", 0)) >= 82:
        strengths.append("size advantage")
    if float(team.get("SOS", 365)) <= 30:
        strengths.append("elite SOS")
    return strengths[:4]


def generate_ranking(
    df: pd.DataFrame,
    norms: list[dict[str, float]],
    deriveds: list[dict[str, float]],
    csi_mults: list[float],
    model_name: str,
    min_seed: int | None = None,
    max_seed: int | None = None
) -> pd.DataFrame:
    """Generate a ranking dataframe for one model."""
    work = df.copy().reset_index(drop=True)
    weights_lookup = load_weights()
    scores = score_all_teams(work, norms, deriveds, csi_mults, model_name, weights_lookup)
    score_column = MODEL_NAME_TO_COLUMN.get(model_name, "ModelScore")
    work[score_column] = scores
    if "PowerScore" not in work.columns:
        power = score_all_teams(work, norms, deriveds, csi_mults, "default", weights_lookup)
        work["PowerScore"] = power

    cinderella_values = []
    fraud_values = []
    strengths = []
    for i, (_, row) in enumerate(work.iterrows()):
        row_dict = row.to_dict()
        row_norm = dict(norms[i])
        row_norm["Consistency_Score"] = float(row_dict.get("Consistency_Score", row_norm.get("Consistency_Score", 0.5)))
        c_result = compute_cinderella_score(row_dict, row_norm)
        f_result = compute_fraud_score(row_dict, row_norm)
        cinderella_values.append(c_result)
        fraud_values.append(f_result)
        strengths.append(", ".join(get_team_strengths(row_dict)))

    c_df = pd.DataFrame(cinderella_values)
    f_df = pd.DataFrame(fraud_values)
    for col in c_df.columns:
        work[col] = c_df[col].values
    for col in f_df.columns:
        work[col] = f_df[col].values
    work["FraudExplanation"] = [
        get_fraud_explanation(work.iloc[i].to_dict(), fraud_values[i]) for i in range(len(work))
    ]
    work["Strengths"] = strengths
    work["SeedMismatch"] = [
        float(seed_mismatch(int(work.at[i, "Seed"]), int(work.at[i, "CompRank"])))
        if pd.notna(work.at[i, "Seed"]) and pd.notna(work.at[i, "CompRank"])
        else 0.0
        for i in range(len(work))
    ]

    work = work.sort_values(score_column, ascending=False).reset_index(drop=True)
    work["Rank"] = np.arange(1, len(work) + 1)
    work["ModelScore"] = work[score_column]

    if min_seed is not None:
        work = work[pd.to_numeric(work["Seed"], errors="coerce") >= min_seed]
    if max_seed is not None:
        work = work[pd.to_numeric(work["Seed"], errors="coerce") <= max_seed]
    work = work.reset_index(drop=True)

    cols = [c for c in RANKING_COLUMN_ORDER if c in work.columns]
    extra_cols = [c for c in work.columns if c not in cols]
    return work[cols + extra_cols]


def generate_all_rankings(
    df: pd.DataFrame,
    norms: list[dict[str, float]],
    deriveds: list[dict[str, float]],
    csi_mults: list[float]
) -> dict[str, pd.DataFrame]:
    """Generate all required ranking views."""
    rankings: dict[str, pd.DataFrame] = {}
    rankings["power"] = generate_ranking(df, norms, deriveds, csi_mults, "default")
    rankings["defensive"] = generate_ranking(df, norms, deriveds, csi_mults, "defensive")
    rankings["offensive"] = generate_ranking(df, norms, deriveds, csi_mults, "offensive")
    rankings["momentum"] = generate_ranking(df, norms, deriveds, csi_mults, "momentum")
    rankings["cinderella"] = generate_ranking(df, norms, deriveds, csi_mults, "cinderella_tournament", min_seed=9)
    rankings["giant_killer"] = generate_ranking(df, norms, deriveds, csi_mults, "giant_killer", min_seed=6)
    return rankings


def generate_bracket_summary(all_brackets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build consensus summary across strategy brackets."""
    if not all_brackets:
        return {"champion_consensus": "", "final_four_consensus": [], "contested_games": []}
    champions = [b.get("champion") for b in all_brackets.values() if b.get("champion")]
    champion_counts = pd.Series(champions).value_counts() if champions else pd.Series(dtype=int)
    final_fours: list[str] = []
    for bracket in all_brackets.values():
        final_fours.extend(bracket.get("final_four", []))
    ff_counts = pd.Series(final_fours).value_counts() if final_fours else pd.Series(dtype=int)
    return {
        "champion_consensus": champion_counts.index[0] if not champion_counts.empty else "",
        "champion_counts": champion_counts.to_dict(),
        "final_four_consensus": ff_counts.head(4).index.tolist(),
        "final_four_counts": ff_counts.to_dict(),
        "n_strategies": len(all_brackets)
    }

