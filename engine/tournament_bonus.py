"""Mid-tournament giant-killer bonus logic."""

from __future__ import annotations

from typing import Any

import pandas as pd

from engine.ingestion import load_bracket


def compute_tournament_bonus(
    team_name: str,
    completed_games: list[dict[str, Any]],
    all_adjems: dict[str, float],
    max_adjem_bonus: float = 4.0
) -> dict[str, Any]:
    """Compute bonus deltas for a team from completed tournament wins."""
    team_games = [g for g in completed_games if g.get("winner_name") == team_name]
    if not team_games:
        return {}

    bonus = {
        "AdjEM_delta": 0.0,
        "AdjO_delta": 0.0,
        "AdjD_delta": 0.0,
        "momentum_bonus": 0.0,
        "giant_killer_flag": False,
        "giant_killer_count": 0,
        "description": []
    }

    for game in team_games:
        winner_seed = int(game.get("winner_seed", 16) or 16)
        loser_seed = int(game.get("loser_seed", 1) or 1)
        seed_gap = loser_seed - winner_seed
        margin = int(game.get("margin", 0) or 0)
        game_stats = game.get("winner_game_stats", {})
        _opponent_adjem = all_adjems.get(str(game.get("loser_name")), 0.0)

        if seed_gap > 0:
            bonus["giant_killer_flag"] = True
            bonus["giant_killer_count"] += 1
            upset_magnitude = min(seed_gap / 4.0, 1.0)
            margin_factor = min(margin / 15.0, 1.0)
            adjem_bonus = min(2.5 * upset_magnitude + 1.5 * margin_factor, max_adjem_bonus)
            bonus["AdjEM_delta"] += adjem_bonus
            bonus["description"].append(
                f"Beat #{loser_seed}-seed by {margin} pts (+{adjem_bonus:.1f} AdjEM)"
            )

        if int(game_stats.get("steals", 0)) >= 8 or int(game_stats.get("turnovers", 99)) <= 8:
            bonus["AdjD_delta"] += 1.0
            bonus["description"].append("Won turnover battle in tournament (+1.0 AdjD)")

        if float(game_stats.get("fg_pct", 0.0)) >= 50:
            bonus["AdjO_delta"] += 0.8
            bonus["description"].append(f"Shot {float(game_stats['fg_pct']):.1f}% from field (+0.8 AdjO)")

        if margin >= 15:
            bonus["momentum_bonus"] += 0.05
            bonus["description"].append(f"Dominant win (margin={margin}) (+momentum)")

        if seed_gap < 0 and margin <= 4:
            bonus["AdjEM_delta"] -= 0.5
            bonus["description"].append(f"Barely beat lower seed by {margin} (-0.5 AdjEM)")

    if len(team_games) >= 2:
        most_recent = team_games[-1]
        if int(most_recent.get("loser_seed", 16)) < int(most_recent.get("winner_seed", 16)):
            bonus["AdjEM_delta"] *= 1.2
            bonus["description"].append("Sustained giant-killer (+20% amplifier)")

    return bonus


def apply_tournament_bonuses(
    df: pd.DataFrame,
    completed_games: list[dict[str, Any]],
    surviving_teams: list[str],
    max_adjem_bonus: float = 4.0
) -> pd.DataFrame:
    """Apply tournament performance bonuses to surviving teams."""
    out = df.copy()
    all_adjems = {
        str(row["Team"]): float(row["AdjEM"])
        for _, row in out.iterrows()
        if pd.notna(row.get("AdjEM"))
    }
    for team_name in surviving_teams:
        mask = out["Team"] == team_name
        if not mask.any():
            continue
        bonus = compute_tournament_bonus(team_name, completed_games, all_adjems, max_adjem_bonus=max_adjem_bonus)
        if not bonus:
            continue
        out.loc[mask, "AdjEM"] = pd.to_numeric(out.loc[mask, "AdjEM"], errors="coerce").fillna(0) + float(
            bonus.get("AdjEM_delta", 0)
        )
        out.loc[mask, "AdjO"] = pd.to_numeric(out.loc[mask, "AdjO"], errors="coerce").fillna(0) + float(
            bonus.get("AdjO_delta", 0)
        )
        out.loc[mask, "AdjD"] = pd.to_numeric(out.loc[mask, "AdjD"], errors="coerce").fillna(0) - float(
            bonus.get("AdjD_delta", 0)
        )
        out.loc[mask, "Last_10_Games_Metric"] = (
            pd.to_numeric(out.loc[mask, "Last_10_Games_Metric"], errors="coerce").fillna(0.65)
            + float(bonus.get("momentum_bonus", 0))
        ).clip(upper=1.0)
        out.loc[mask, "TournamentBonus_AdjEM"] = float(bonus.get("AdjEM_delta", 0))
        out.loc[mask, "GiantKiller"] = bool(bonus.get("giant_killer_flag", False))
        out.loc[mask, "GiantKillerCount"] = int(bonus.get("giant_killer_count", 0))
        out.loc[mask, "BonusDescription"] = " | ".join(bonus.get("description", []))
    return out


def build_remaining_bracket(
    config: dict[str, Any],
    completed_games: list[dict[str, Any]],
    df_survivors: pd.DataFrame
) -> dict[str, list[dict[str, Any]]]:
    """Build remaining bracket with surviving teams only."""
    bracket = load_bracket(config["bracket_file"])
    eliminated = {str(game.get("loser_name")) for game in completed_games}
    lookup = {str(row["Team"]): row.to_dict() for _, row in df_survivors.iterrows()}
    remaining: dict[str, list[dict[str, Any]]] = {}
    for region, teams in bracket["teams_by_region"].items():
        region_teams: list[dict[str, Any]] = []
        for team in teams:
            name = str(team.get("team"))
            if name in eliminated:
                continue
            if name in lookup:
                region_teams.append({**lookup[name], "slot": team.get("slot"), "Seed": team.get("Seed", lookup[name].get("Seed", 16))})
        region_teams.sort(key=lambda t: int(t.get("slot", 99)))
        remaining[region] = region_teams
    return remaining

