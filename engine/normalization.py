"""Feature normalization and derived metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

FEATURE_RANGES: dict[str, tuple[float, float, str]] = {
    "AdjEM": (-20, 40, "higher"),
    "AdjO": (95, 130, "higher"),
    "AdjD": (80, 125, "inverse"),
    "Barthag": (0.20, 1.00, "higher"),
    "eFG%": (44, 62, "higher"),
    "Opp_eFG%": (40, 60, "inverse"),
    "TO%": (10, 25, "inverse"),
    "Opp_TO%": (10, 25, "higher"),
    "OR%": (18, 45, "higher"),
    "DR%": (60, 86, "higher"),
    "FTR": (18, 55, "higher"),
    "Opp_FTR": (18, 50, "inverse"),
    "FT%": (62, 85, "higher"),
    "3P%": (28, 42, "higher"),
    "3P_%_D": (25, 40, "inverse"),
    "2P%": (44, 62, "higher"),
    "2P_%_D": (40, 58, "inverse"),
    "3P_Rate": (25, 55, "neutral"),
    "3P_Rate_D": (28, 52, "inverse"),
    "AST_TO": (0.8, 2.5, "higher"),
    "Ast_%": (38, 70, "higher"),
    "Op_Ast_%": (35, 65, "inverse"),
    "Blk_%": (4, 20, "higher"),
    "Blked_%": (2, 14, "inverse"),
    "Avg_Hgt": (73, 81, "higher"),
    "Eff_Hgt": (75, 84, "higher"),
    "SOS": (1, 365, "inverse"),
    "CompRank": (1, 365, "inverse"),
    "Torvik_Rank": (1, 365, "inverse"),
    "Massey_Rank": (1, 365, "inverse"),
    "NET_Rank": (1, 365, "inverse"),
    "Exp": (0, 3, "higher"),
    "Last_10_Games_Metric": (0.3, 1.0, "higher"),
    "Star_Player_Index": (1, 10, "higher"),
    "Bench_Minutes_Pct": (20, 55, "higher"),
    "Quad1_Wins": (0, 15, "higher"),
    "Elite_SOS": (0, 50, "higher"),
    "PPP_Off": (0.88, 1.30, "higher"),
    "PPP_Def": (0.80, 1.22, "inverse"),
    "Adj_T": (60, 80, "neutral"),
    "RankTrajectory": (-30, 30, "higher"),
    "WinPct": (0, 1, "higher")
}


def _is_nan(v: Any) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v))


def normalize_value(v: Any, min_val: float, max_val: float) -> float:
    """Higher raw value should map to higher normalized value."""
    if _is_nan(v):
        return 0.5
    value = float(v)
    if max_val == min_val:
        return 0.5
    return float(np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0))


def normalize_inverse(v: Any, min_val: float, max_val: float) -> float:
    """Lower raw value should map to higher normalized value."""
    if _is_nan(v):
        return 0.5
    value = float(v)
    if max_val == min_val:
        return 0.5
    return float(np.clip((max_val - value) / (max_val - min_val), 0.0, 1.0))


def normalize_team(team_row: pd.Series | dict[str, Any]) -> dict[str, float]:
    """Normalize all features for a single team row."""
    team = team_row if isinstance(team_row, dict) else team_row.to_dict()
    wins = pd.to_numeric(pd.Series([team.get("Wins")]), errors="coerce").iloc[0]
    games = pd.to_numeric(pd.Series([team.get("Games")]), errors="coerce").iloc[0]
    if pd.notna(wins) and pd.notna(games) and games > 0:
        team["WinPct"] = float(wins) / float(games)
    else:
        team["WinPct"] = team.get("WinPct", 0.5)

    norm: dict[str, float] = {}
    for feature, (min_val, max_val, direction) in FEATURE_RANGES.items():
        raw_value = team.get(feature)
        if direction == "inverse":
            norm_value = normalize_inverse(raw_value, min_val, max_val)
            norm[feature] = norm_value
            norm[f"{feature}_inv"] = norm_value
        elif direction == "neutral":
            norm_value = normalize_value(raw_value, min_val, max_val)
            norm[feature] = norm_value
        else:
            norm_value = normalize_value(raw_value, min_val, max_val)
            norm[feature] = norm_value

    # Create _inv aliases so model weights and derived features can reference
    # them by either name.  The base key is already normalized with the correct
    # direction (inverse features are already inverted), so the _inv alias is
    # just a convenience for readability in weights.json and derived formulas.
    _inv_aliases = [
        "TO%", "Opp_eFG%", "CompRank", "SOS", "AdjD",
        "3P_%_D", "2P_%_D", "Opp_FTR", "Blked_%", "Op_Ast_%",
    ]
    for key in _inv_aliases:
        if key in norm:
            norm[f"{key}_inv"] = norm[key]

    if "Adj_T" in norm:
        norm["Adj_T_inv"] = normalize_inverse(team.get("Adj_T"), 60, 80)
    if "SeedMismatch" in team:
        norm["SeedMismatch_norm"] = normalize_value(team["SeedMismatch"], 0, 1)

    return norm


def normalize_all_teams(df: pd.DataFrame) -> list[dict[str, float]]:
    """Normalize all rows and return list aligned with dataframe rows."""
    return [normalize_team(row) for _, row in df.iterrows()]


def compute_derived_features(norm: dict[str, float]) -> dict[str, float]:
    """Compute derived features from normalized primitives."""
    return {
        "CloseGame": (
            norm.get("Last_10_Games_Metric", 0.5)
            + norm.get("WinPct", 0.5)
            + 0.5 * norm.get("FT%", 0.5)
            + 0.5 * norm.get("TO%_inv", 0.5)
        )
        / 3.0,
        "ThreePtConsistency": (
            norm.get("3P%", 0.5) * 0.65 + norm.get("3P_%_D_inv", 0.5) * 0.35
        ),
        "BallMovement": (
            norm.get("AST_TO", 0.5) * 0.50
            + norm.get("Ast_%", 0.5) * 0.30
            + norm.get("Op_Ast_%_inv", 0.5) * 0.20
        ),
        "Physicality": (
            norm.get("OR%", 0.5) * 0.30
            + norm.get("Blk_%", 0.5) * 0.25
            + norm.get("FTR", 0.5) * 0.25
            + norm.get("Eff_Hgt", 0.5) * 0.20
        ),
        "InsideScoring": (
            norm.get("2P%", 0.5) * 0.50
            + norm.get("OR%", 0.5) * 0.30
            + norm.get("FTR", 0.5) * 0.20
        ),
        "InteriorDefense": (
            norm.get("2P_%_D_inv", 0.5) * 0.45
            + norm.get("Blk_%", 0.5) * 0.35
            + norm.get("DR%", 0.5) * 0.20
        ),
        "TournamentReadiness": (
            norm.get("Barthag", 0.5) * 0.50
            + norm.get("Exp", 0.5) * 0.30
            + norm.get("Quad1_Wins", 0.5) * 0.20
        ),
        "DefensivePlaymaking": (
            norm.get("Opp_TO%", 0.5) * 0.55
            + norm.get("Blk_%", 0.5) * 0.30
            + norm.get("Blked_%_inv", 0.5) * 0.15
        ),
        "NETMomentum": normalize_value(norm.get("RankTrajectory", 0.0), -30, 30)
    }


def compute_consistency_score(team: dict[str, Any]) -> float:
    """Higher score means recent form is closer to season baseline."""
    wins = pd.to_numeric(pd.Series([team.get("Wins")]), errors="coerce").iloc[0]
    games = pd.to_numeric(pd.Series([team.get("Games")]), errors="coerce").iloc[0]
    if pd.notna(wins) and pd.notna(games) and games > 0:
        win_pct = float(wins) / float(games)
    else:
        win_pct = 0.65
    last_10 = pd.to_numeric(pd.Series([team.get("Last_10_Games_Metric")]), errors="coerce").iloc[0]
    if pd.isna(last_10):
        last_10 = 0.65
    return normalize_inverse(abs(float(last_10) - win_pct), 0, 0.4)


def compute_volatility_score(team: dict[str, Any], norm: dict[str, float]) -> float:
    """Risk score, not quality score."""
    consistency = compute_consistency_score(team)
    return float(0.6 * norm.get("3P_Rate", 0.5) + 0.4 * (1.0 - consistency))

