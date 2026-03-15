"""Data ingestion, normalization, and override handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ALIAS_MAP: dict[str, str] = {
    "Adj OE": "AdjO",
    "Adj DE": "AdjD",
    "AdjOE": "AdjO",
    "AdjDE": "AdjD",
    "eFG D.": "Opp_eFG%",
    "Opp eFG%": "Opp_eFG%",
    "TOV%": "TO%",
    "TOV% D": "Opp_TO%",
    "O Reb%": "OR%",
    "D Reb%": "DR%",
    "FT Rate": "FTR",
    "FT Rate D": "Opp_FTR",
    "3P % D.": "3P_%_D",
    "2P % D.": "2P_%_D",
    "Raw T": "Raw_T",
    "Adj. T": "Adj_T",
    "PPP Off.": "PPP_Off",
    "PPP Def.": "PPP_Def",
    "Elite SOS": "Elite_SOS",
    "Avg Hgt.": "Avg_Hgt",
    "Eff. Hgt.": "Eff_Hgt",
    "Exp.": "Exp",
    "T_Rank_Early": "TRank_Early",
    "T_Rank": "Torvik_Rank",
    "wAB": "WAB"
}

REQUIRED_COLUMNS: list[str] = [
    "Team",
    "AdjO",
    "AdjD",
    "Barthag",
    "eFG%",
    "Opp_eFG%",
    "TO%",
    "Opp_TO%",
    "OR%",
    "SOS",
    "Adj_T"
]

DEFAULTS: dict[str, Any] = {
    "Seed": 10,
    "Conference": "Unknown",
    "Star_Player_Index": 5.0,
    "Bench_Minutes_Pct": 30.0,
    "Last_10_Games_Metric": 0.65,
    "Massey_Rank": 150,
    "Elite_SOS": 10.0,
    "Quad1_Wins": 3,
    "Exp": 1.5,
    "Avg_Hgt": 77.0,
    "Eff_Hgt": 79.0,
    "AP_Poll_Rank": 26,
    "Coach_Tourney_Experience": 3.0,
    "Program_Prestige": 2.0,
    "WAB": 2.0,
    "Conf_Tourney_Champion": 0,
    "Won_Play_In": 0,
    "OverrideActive": 0
}

NUMERIC_DEFAULT_COLUMNS: list[str] = [
    "AdjO",
    "AdjD",
    "AdjEM",
    "Barthag",
    "eFG%",
    "Opp_eFG%",
    "TO%",
    "Opp_TO%",
    "OR%",
    "DR%",
    "FTR",
    "Opp_FTR",
    "FT%",
    "SOS",
    "Adj_T",
    "Torvik_Rank",
    "NET_Rank",
    "CompRank",
    "TRank_Early"
]


class IngestionError(ValueError):
    """Raised for malformed ingestion inputs."""


def normalize_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Map known alias columns to canonical schema names."""
    mapped = {col: ALIAS_MAP.get(col, col) for col in df.columns}
    normalized = df.rename(columns=mapped)
    if "Team" in normalized.columns:
        normalized["Team"] = normalized["Team"].astype(str).str.strip()
    return normalized


def _parse_record_fields(df: pd.DataFrame) -> pd.DataFrame:
    if "Record" not in df.columns:
        return df
    record_split = df["Record"].astype(str).str.split("-", n=1, expand=True)
    wins = pd.to_numeric(record_split[0], errors="coerce")
    losses = pd.to_numeric(record_split[1], errors="coerce")
    if "Wins" not in df.columns:
        df["Wins"] = wins
    if "Games" not in df.columns:
        df["Games"] = wins + losses
    return df


def _ensure_adjem(df: pd.DataFrame) -> pd.DataFrame:
    if "AdjO" not in df.columns or "AdjD" not in df.columns:
        return df
    adjo = pd.to_numeric(df["AdjO"], errors="coerce")
    adjd = pd.to_numeric(df["AdjD"], errors="coerce")
    df["AdjO"] = adjo
    df["AdjD"] = adjd
    df["AdjEM"] = (adjo - adjd).round(3)
    return df


def compute_luck(df: pd.DataFrame) -> pd.DataFrame:
    """Compute luck as WinPct - Barthag for rows with missing luck."""
    if "Luck" not in df.columns:
        df["Luck"] = np.nan
    wins = pd.to_numeric(df.get("Wins"), errors="coerce")
    games = pd.to_numeric(df.get("Games"), errors="coerce")
    barthag = pd.to_numeric(df.get("Barthag"), errors="coerce")
    if wins is None or games is None:
        wins = pd.Series([20.0] * len(df))
        games = pd.Series([30.0] * len(df))
    win_pct = wins.fillna(20) / games.fillna(30).clip(lower=1)
    proxy = (win_pct - barthag.fillna(0.5)).round(4)
    mask = pd.isna(df["Luck"])
    df.loc[mask, "Luck"] = proxy[mask]
    return df


def apply_defaults(df: pd.DataFrame) -> pd.DataFrame:
    """Fill deterministic defaults defined by schema docs."""
    for column, default in DEFAULTS.items():
        if column not in df.columns:
            df[column] = default
        else:
            df[column] = df[column].fillna(default)
    for col in NUMERIC_DEFAULT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "DR%" not in df.columns and "Opp_OR%" in df.columns:
        opp_or = pd.to_numeric(df["Opp_OR%"], errors="coerce")
        df["DR%"] = (100.0 - opp_or).clip(lower=0, upper=100)
    if "CompRank" not in df.columns:
        rank_cols = [c for c in ("Torvik_Rank", "Massey_Rank", "NET_Rank") if c in df.columns]
        if rank_cols:
            df["CompRank"] = df[rank_cols].mean(axis=1, skipna=True)
    return df


def apply_conf_tourney_champion_bonus(df: pd.DataFrame) -> pd.DataFrame:
    """Apply +0.05 to Last_10_Games_Metric for conference tournament champions."""
    if "Conf_Tourney_Champion" not in df.columns:
        return df
    metric = pd.to_numeric(df["Last_10_Games_Metric"], errors="coerce").fillna(0.65)
    conf_champ = pd.to_numeric(df["Conf_Tourney_Champion"], errors="coerce").fillna(0)
    metric = np.where(conf_champ == 1, np.minimum(metric + 0.05, 1.0), metric)
    df["Last_10_Games_Metric"] = metric
    return df


def apply_overrides(df: pd.DataFrame, overrides_path: str | None = None) -> pd.DataFrame:
    """Apply override JSON data in delta or absolute mode."""
    if not overrides_path:
        return df
    path = Path(overrides_path)
    if not path.exists():
        return df
    with path.open("r", encoding="utf-8") as f:
        overrides = json.load(f)
    if not isinstance(overrides, dict):
        raise IngestionError("overrides.json must be a JSON object keyed by team name.")
    team_idx = {name: idx for idx, name in enumerate(df["Team"].astype(str))}
    for team_name, payload in overrides.items():
        if team_name not in team_idx:
            continue
        if not isinstance(payload, dict):
            raise IngestionError(f"Override payload for '{team_name}' must be an object.")
        i = team_idx[team_name]
        mode = str(payload.get("mode", "delta")).lower()
        if mode not in {"delta", "absolute"}:
            raise IngestionError(f"Invalid override mode for '{team_name}': {mode}")
        for key, value in payload.items():
            if key in {"mode", "note"}:
                continue
            if key not in df.columns:
                continue
            if isinstance(value, (int, float)):
                if mode == "delta":
                    current = pd.to_numeric(pd.Series([df.at[i, key]]), errors="coerce").iloc[0]
                    base = 0.0 if pd.isna(current) else float(current)
                    df.at[i, key] = base + float(value)
                else:
                    df.at[i, key] = float(value)
        df.at[i, "OverrideActive"] = 1
    # Recompute AdjEM if O/D changed.
    df = _ensure_adjem(df)
    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Return required columns missing from the input dataframe."""
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def _validate_rows(df: pd.DataFrame) -> None:
    if "Team" in df.columns:
        dupes = df[df["Team"].duplicated(keep=False)]["Team"].tolist()
        if dupes:
            raise IngestionError(f"Duplicate teams found: {sorted(set(dupes))}")
    if "Seed" in df.columns:
        seed = pd.to_numeric(df["Seed"], errors="coerce")
        bad_seed_mask = seed.notna() & ~seed.between(1, 16)
        if bad_seed_mask.any():
            bad_rows = df.loc[bad_seed_mask, ["Team", "Seed"]].to_dict("records")
            raise IngestionError(f"Invalid seed values detected: {bad_rows}")


def load_teams(csv_path: str, overrides_path: str | None = None) -> pd.DataFrame:
    """Load, validate, and standardize team data."""
    path = Path(csv_path)
    if not path.exists():
        raise IngestionError(f"teams_input.csv not found: {csv_path}")
    df = pd.read_csv(path)
    df = normalize_aliases(df)
    df = _parse_record_fields(df)
    df = _ensure_adjem(df)
    df = compute_luck(df)
    df = apply_defaults(df)
    df = apply_conf_tourney_champion_bonus(df)
    df = apply_overrides(df, overrides_path)

    missing = validate_columns(df)
    if missing:
        raise IngestionError(
            f"Missing required columns: {missing}. "
            "Provide canonical columns or add to alias map."
        )

    _validate_rows(df)
    return df


def load_bracket(bracket_path: str) -> dict[str, Any]:
    """Load and validate bracket input JSON."""
    path = Path(bracket_path)
    if not path.exists():
        raise IngestionError(f"bracket_input.json not found: {bracket_path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise IngestionError("bracket_input.json must be a JSON object.")
    teams = data.get("teams")
    regions = data.get("regions")
    if not isinstance(teams, list) or not teams:
        raise IngestionError("bracket_input.json must include non-empty 'teams' list.")
    if not isinstance(regions, list) or len(regions) != 4:
        raise IngestionError("bracket_input.json must include 4 regions in 'regions'.")

    teams_by_region: dict[str, list[dict[str, Any]]] = {str(region): [] for region in regions}
    for team in teams:
        if not isinstance(team, dict):
            raise IngestionError("Each team entry in bracket_input.json must be an object.")
        required = {"team", "seed", "region", "slot"}
        missing = required - set(team.keys())
        if missing:
            raise IngestionError(f"Bracket team missing fields: {sorted(missing)}")
        region = str(team["region"])
        if region not in teams_by_region:
            raise IngestionError(f"Unknown region in bracket team row: {region}")
        slot = int(team["slot"])
        seed = int(team["seed"])
        if slot < 1 or slot > 16:
            raise IngestionError(f"Invalid slot {slot} for {team['team']}; expected 1-16.")
        if seed < 1 or seed > 16:
            raise IngestionError(f"Invalid seed {seed} for {team['team']}; expected 1-16.")
        teams_by_region[region].append(
            {
                "team": str(team["team"]).strip(),
                "Seed": seed,
                "region": region,
                "slot": slot,
                "play_in": bool(team.get("play_in", False)),
                "play_in_opponent": team.get("play_in_opponent")
            }
        )

    for region, region_teams in teams_by_region.items():
        if len(region_teams) != 16:
            raise IngestionError(
                f"Region '{region}' must have exactly 16 teams, found {len(region_teams)}."
            )
        slots = sorted(t["slot"] for t in region_teams)
        if slots != list(range(1, 17)):
            raise IngestionError(f"Region '{region}' slots must contain every value 1-16.")
        region_teams.sort(key=lambda t: t["slot"])

    return {
        "year": data.get("year"),
        "regions": regions,
        "teams": teams,
        "teams_by_region": teams_by_region
    }

