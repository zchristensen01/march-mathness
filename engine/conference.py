"""Conference strength index (CSI) calculations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import optimize


def load_conference_weights(path: str = "models/conference_weights.json") -> dict[str, float]:
    """Load conference multiplier overrides from JSON."""
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return {k: float(v) for k, v in payload.items() if not k.startswith("_")}


def win50_rating(adjems: list[float]) -> float:
    """Find rating R where expected conference round-robin win rate is .500."""
    values = [float(v) for v in adjems if not pd.isna(v)]
    if not values:
        return 0.0
    n = len(values)

    def expected_wins(rating: float) -> float:
        wins = sum(1.0 / (1.0 + 10 ** ((r_j - rating) * 30.464 / 400.0)) for r_j in values)
        return wins - n / 2.0

    return float(optimize.brentq(expected_wins, -50, 50, xtol=1e-6))


def nonconf_calibration(conf_teams: list[dict[str, Any]], _all_adjems: dict[str, float]) -> float:
    """Estimate conference over/under-performance via Q1 wins proxy."""
    total_actual = 0.0
    total_expected = 0.0
    count = 0
    for team in conf_teams:
        rank = float(team.get("CompRank") or team.get("Torvik_Rank") or 180)
        expected_q1 = max(0.0, (350.0 - rank) / 350.0 * 12.0)
        actual_q1 = float(team.get("Quad1_Wins", 3))
        total_actual += actual_q1
        total_expected += expected_q1
        count += 1
    if count == 0 or total_expected == 0:
        return 0.0
    return float((total_actual - total_expected) / total_expected)


def compute_csi(conf_teams: list[dict[str, Any]]) -> dict[str, float]:
    """Compute conference strength index and multiplier."""
    adjems = [float(t.get("AdjEM", 0.0)) for t in conf_teams]
    win50 = win50_rating(adjems)
    nonconf_adj = nonconf_calibration(conf_teams, {})
    raw_csi = 0.75 * win50 + 0.25 * (win50 * (1 + nonconf_adj))
    csi_z = (raw_csi - 0.0) / 8.0
    csi_multiplier = float(np.clip(1.0 + 0.04 * csi_z, 0.75, 1.05))
    return {
        "win50": float(win50),
        "nonconf_adj": float(nonconf_adj),
        "raw_csi": float(raw_csi),
        "multiplier": csi_multiplier
    }


def compute_all_conference_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """Build one-row-per-conference CSI table."""
    if "Conference" not in df.columns:
        return pd.DataFrame(columns=["Conference", "CSI", "CSI_multiplier", "WIN50", "NonConfAdj"])
    rows: list[dict[str, float | str]] = []
    conf_weights = load_conference_weights()
    grouped = df.groupby("Conference", dropna=False)
    for conference, group in grouped:
        teams = group.to_dict("records")
        csi = compute_csi(teams)
        weight_override = conf_weights.get(str(conference), np.nan)
        multiplier = csi["multiplier"]
        if not pd.isna(weight_override):
            multiplier = float(np.clip(max(multiplier, float(weight_override)), 0.75, 1.05))
        rows.append(
            {
                "Conference": str(conference),
                "WIN50": csi["win50"],
                "NonConfAdj": csi["nonconf_adj"],
                "CSI": csi["raw_csi"],
                "CSI_multiplier": multiplier,
                "Teams": int(len(group)),
                "Avg_AdjEM": float(pd.to_numeric(group["AdjEM"], errors="coerce").mean())
            }
        )
    result = pd.DataFrame(rows).sort_values("CSI_multiplier", ascending=False).reset_index(drop=True)
    return result


def apply_csi_to_teams(df: pd.DataFrame, conf_ratings: pd.DataFrame) -> pd.DataFrame:
    """Attach CSI values to team dataframe."""
    if conf_ratings.empty:
        df["CSI"] = 0.0
        df["CSI_multiplier"] = 1.0
        return df
    lookup = conf_ratings.set_index("Conference")[["CSI", "CSI_multiplier"]]
    out = df.copy()
    out["CSI"] = out["Conference"].map(lookup["CSI"]).fillna(0.0)
    out["CSI_multiplier"] = out["Conference"].map(lookup["CSI_multiplier"]).fillna(1.0)

    if "Conf_Strength_Weight" in out.columns:
        manual = pd.to_numeric(out["Conf_Strength_Weight"], errors="coerce")
        use_manual = manual.notna()
        out.loc[use_manual, "CSI_multiplier"] = np.minimum(
            out.loc[use_manual, "CSI_multiplier"], manual[use_manual]
        ).clip(lower=0.75, upper=1.05)
    return out

