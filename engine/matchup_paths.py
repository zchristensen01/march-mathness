"""Build tournament path matchup options for top-ranked teams."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from engine import order_final_four_regions

ROUND_SEQUENCE: list[str] = ["R64", "R32", "S16", "E8", "F4", "Championship"]
ROUND_REACH_KEY: dict[str, str] = {
    "R64": "R64",
    "R32": "R32",
    "S16": "S16",
    "E8": "E8",
    "F4": "F4",
    "Championship": "Championship",
}
IN_REGION_GROUP_SIZE: dict[str, int] = {
    "R64": 2,
    "R32": 4,
    "S16": 8,
    "E8": 16,
}
FINAL_ROUND_CAP = 6


def _team_name(team: dict[str, Any]) -> str:
    return str(team.get("Team", team.get("team", "")))


def _to_int(value: Any, default: int) -> int:
    as_num = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return int(as_num) if pd.notna(as_num) else default


def _to_float(value: Any, default: float = 0.0) -> float:
    as_num = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(as_num) if pd.notna(as_num) else default


def _build_bracket_lookup(
    bracket_with_stats: dict[str, list[dict[str, Any]]]
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_name: dict[str, dict[str, Any]] = {}
    by_region: dict[str, list[dict[str, Any]]] = {}
    for region, teams in bracket_with_stats.items():
        ordered = sorted(teams, key=lambda team: _to_int(team.get("slot"), 99))
        by_region[region] = ordered
        for team in ordered:
            name = _team_name(team)
            if not name:
                continue
            enriched = dict(team)
            enriched["Team"] = name
            enriched["region"] = region
            enriched["slot"] = _to_int(team.get("slot"), 99)
            enriched["Seed"] = _to_int(team.get("Seed", team.get("seed")), 16)
            by_name[name] = enriched
    return by_name, by_region


def _get_possible_opponents_in_region(
    slot_idx: int,
    round_name: str,
    region_teams: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if round_name not in IN_REGION_GROUP_SIZE:
        return []
    group_size = IN_REGION_GROUP_SIZE[round_name]
    if group_size <= 0 or slot_idx < 0 or slot_idx >= len(region_teams):
        return []
    if round_name == "R64":
        opp_idx = slot_idx ^ 1
        if 0 <= opp_idx < len(region_teams):
            return [region_teams[opp_idx]]
        return []

    group_start = (slot_idx // group_size) * group_size
    half_size = group_size // 2
    my_half_start = group_start if slot_idx < group_start + half_size else group_start + half_size
    opp_half_start = group_start + half_size if my_half_start == group_start else group_start
    opp_half_end = min(opp_half_start + half_size, len(region_teams))
    return region_teams[opp_half_start:opp_half_end]


def _paired_final_four_region(team_region: str, final_four_regions: list[str]) -> str | None:
    if team_region not in final_four_regions:
        return None
    idx = final_four_regions.index(team_region)
    if idx in (0, 1):
        return final_four_regions[1 - idx]
    if idx in (2, 3):
        return final_four_regions[5 - idx]
    return None


def _championship_regions(team_region: str, final_four_regions: list[str]) -> list[str]:
    if team_region not in final_four_regions:
        return []
    idx = final_four_regions.index(team_region)
    if idx in (0, 1):
        return [final_four_regions[2], final_four_regions[3]]
    return [final_four_regions[0], final_four_regions[1]]


def _get_cross_region_opponents(
    team_region: str,
    round_name: str,
    teams_by_region: dict[str, list[dict[str, Any]]],
    final_four_regions: list[str]
) -> list[dict[str, Any]]:
    if round_name == "F4":
        paired = _paired_final_four_region(team_region, final_four_regions)
        if paired is None:
            return []
        return list(teams_by_region.get(paired, []))
    if round_name == "Championship":
        regions = _championship_regions(team_region, final_four_regions)
        out: list[dict[str, Any]] = []
        for region in regions:
            out.extend(teams_by_region.get(region, []))
        return out
    return []


def _opponent_entry(
    team: dict[str, Any],
    opponent: dict[str, Any],
    round_name: str,
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    sim_results: dict[str, dict[str, float]],
    power_rank_map: dict[str, int]
) -> dict[str, Any]:
    team_name = _team_name(team)
    opp_name = _team_name(opponent)
    reach_key = ROUND_REACH_KEY[round_name]
    team_reach_prob = 1.0 if round_name == "R64" else _to_float(sim_results.get(team_name, {}).get(reach_key), 0.0)
    opp_reach_prob = 1.0 if round_name == "R64" else _to_float(sim_results.get(opp_name, {}).get(reach_key), 0.0)
    meeting_prob = max(0.0, min(1.0, team_reach_prob * opp_reach_prob))
    win_prob = max(0.0, min(1.0, _to_float(win_prob_fn(team, opponent), 0.5)))
    return {
        "team": opp_name,
        "seed": _to_int(opponent.get("Seed"), 16),
        "win_prob": round(win_prob, 4),
        "meeting_prob": round(meeting_prob, 4),
        "power_rank": power_rank_map.get(opp_name),
        "adjEM": round(_to_float(opponent.get("AdjEM"), 0.0), 3),
    }


def _sort_and_cap(round_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            -float(row.get("meeting_prob", 0.0)),
            -float(row.get("win_prob", 0.0)),
            _to_int(row.get("seed"), 99),
            str(row.get("team", "")),
        ),
    )
    if round_name in {"F4", "Championship"}:
        return ordered[:FINAL_ROUND_CAP]
    return ordered


def generate_matchup_paths(
    bracket_with_stats: dict[str, list[dict[str, Any]]],
    sim_results: dict[str, dict[str, float]],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    power_rankings_df: pd.DataFrame,
    top_n: int = 20
) -> dict[str, Any]:
    """Build possible tournament-path opponents for top power-ranked teams."""
    team_lookup, teams_by_region = _build_bracket_lookup(bracket_with_stats)
    regions = list(teams_by_region.keys())
    final_four_regions = order_final_four_regions(regions)

    ranking_view = power_rankings_df.copy()
    if "Rank" in ranking_view.columns:
        ranking_view["Rank"] = pd.to_numeric(ranking_view["Rank"], errors="coerce")
        ranking_view = ranking_view.sort_values("Rank", ascending=True)
    elif "PowerScore" in ranking_view.columns:
        ranking_view["PowerScore"] = pd.to_numeric(ranking_view["PowerScore"], errors="coerce")
        ranking_view = ranking_view.sort_values("PowerScore", ascending=False)

    power_rank_map: dict[str, int] = {}
    for _, row in ranking_view.iterrows():
        name = str(row.get("Team", ""))
        if not name:
            continue
        rank_val = pd.to_numeric(pd.Series([row.get("Rank")]), errors="coerce").iloc[0]
        if pd.notna(rank_val):
            power_rank_map[name] = int(rank_val)

    top_teams: list[str] = []
    for _, row in ranking_view.iterrows():
        name = str(row.get("Team", ""))
        if not name or name not in team_lookup:
            continue
        top_teams.append(name)
        if len(top_teams) >= top_n:
            break

    team_paths: dict[str, Any] = {}
    for team_name in top_teams:
        team = team_lookup[team_name]
        region = str(team.get("region", ""))
        seed = _to_int(team.get("Seed"), 16)
        slot = _to_int(team.get("slot"), 99)
        slot_idx = slot - 1
        region_teams = teams_by_region.get(region, [])

        rounds_payload: dict[str, list[dict[str, Any]]] = {}
        for round_name in ROUND_SEQUENCE:
            if round_name in IN_REGION_GROUP_SIZE:
                opponents = _get_possible_opponents_in_region(slot_idx, round_name, region_teams)
            else:
                opponents = _get_cross_region_opponents(region, round_name, teams_by_region, final_four_regions)

            rows = [
                _opponent_entry(team, opponent, round_name, win_prob_fn, sim_results, power_rank_map)
                for opponent in opponents
                if _team_name(opponent) and _team_name(opponent) != team_name
            ]
            rounds_payload[round_name] = _sort_and_cap(round_name, rows)

        team_paths[team_name] = {
            "seed": seed,
            "region": region,
            "slot": slot,
            "power_rank": power_rank_map.get(team_name),
            "rounds": rounds_payload,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": top_n,
        "rounds": ROUND_SEQUENCE,
        "team_paths": team_paths,
    }

