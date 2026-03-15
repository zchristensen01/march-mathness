"""Live tournament results fetch and parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


def fetch_tournament_scores(group_id: int = 100, timeout: int = 10) -> dict[str, Any]:
    """Fetch NCAA tournament scoreboard data from ESPN."""
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    params = {"groups": group_id, "limit": 50}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def parse_tournament_results(scoreboard_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse completed game results from scoreboard payload."""
    results: list[dict[str, Any]] = []
    for event in scoreboard_data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        status = competition.get("status", {}).get("type", {}).get("name")
        if status != "STATUS_FINAL":
            continue
        competitors = competition.get("competitors", [])
        if len(competitors) != 2:
            continue
        team_a, team_b = competitors[0], competitors[1]
        winner = team_a if team_a.get("winner") else team_b
        loser = team_b if winner is team_a else team_a
        winner_seed = int(winner.get("curatedRank", {}).get("current", winner.get("seed", 0)) or 0)
        loser_seed = int(loser.get("curatedRank", {}).get("current", loser.get("seed", 0)) or 0)
        winner_score = int(winner.get("score", 0))
        loser_score = int(loser.get("score", 0))
        results.append(
            {
                "game_id": event.get("id"),
                "winner_name": winner.get("team", {}).get("displayName", ""),
                "winner_seed": winner_seed,
                "winner_score": winner_score,
                "loser_name": loser.get("team", {}).get("displayName", ""),
                "loser_seed": loser_seed,
                "loser_score": loser_score,
                "margin": winner_score - loser_score,
                "is_upset": winner_seed > loser_seed if winner_seed and loser_seed else False,
                "round": competition.get("notes", [{}])[0].get("headline", "Unknown Round"),
                "date": event.get("date")
            }
        )
    return results


def fetch_game_boxscore(game_id: str, timeout: int = 10) -> dict[str, Any]:
    """Fetch ESPN game summary/box score endpoint."""
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary"
    params = {"event": game_id}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def parse_team_game_stats(box_data: dict[str, Any], team_name: str) -> dict[str, Any]:
    """Extract team stats from ESPN box score for one team."""
    stats: dict[str, Any] = {}
    for team in box_data.get("boxscore", {}).get("teams", []):
        display_name = team.get("team", {}).get("displayName")
        if display_name != team_name:
            continue
        for stat in team.get("statistics", []):
            label = stat.get("label")
            value = str(stat.get("displayValue", ""))
            if label == "FG%":
                stats["fg_pct"] = float(value.replace("%", ""))
            elif label == "3PT%":
                stats["three_pct"] = float(value.replace("%", ""))
            elif label == "FT%":
                stats["ft_pct"] = float(value.replace("%", ""))
            elif label == "Rebounds":
                stats["rebounds"] = int(value)
            elif label == "Assists":
                stats["assists"] = int(value)
            elif label == "Turnovers":
                stats["turnovers"] = int(value)
            elif label == "Steals":
                stats["steals"] = int(value)
            elif label == "Blocks":
                stats["blocks"] = int(value)
    return stats


def fetch_results(config: dict[str, Any]) -> dict[str, Any]:
    """Try ESPN first, then fallback to manual JSON."""
    timeout = int(config.get("espn_api_timeout", 10))
    group_id = int(config.get("espn_groups_id", 100))
    try:
        raw = fetch_tournament_scores(group_id=group_id, timeout=timeout)
        games = parse_tournament_results(raw)
        for game in games[:20]:
            game_id = str(game.get("game_id"))
            if not game_id:
                continue
            try:
                box = fetch_game_boxscore(game_id, timeout=timeout)
                game["winner_game_stats"] = parse_team_game_stats(box, game["winner_name"])
                game["loser_game_stats"] = parse_team_game_stats(box, game["loser_name"])
            except Exception:
                pass
        if games:
            print(f"  ✓ ESPN API: fetched {len(games)} completed games")
            return {"source": "espn_api", "completed_games": games}
    except Exception as exc:
        print(f"  ⚠ ESPN API failed: {exc} - falling back to manual JSON")

    results_file = Path(config.get("results_file", "data/tournament_results.json"))
    if results_file.exists():
        with results_file.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        print(f"  ✓ Manual JSON: loaded {len(payload.get('completed_games', []))} games")
        return payload

    print("  ⚠ No result source available.")
    return {"source": "none", "completed_games": []}

