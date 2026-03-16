"""Output writers for rankings, brackets, simulation, and dashboard assets."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from engine.normalization import compute_rank_divergence
from engine.win_probability import predicted_spread

log = logging.getLogger(__name__)

HISTORICAL_UPSET_RATES: dict[tuple[int, int], float] = {
    (1, 16): 0.012,
    (2, 15): 0.069,
    (3, 14): 0.144,
    (4, 13): 0.206,
    (5, 12): 0.356,
    (6, 11): 0.388,
    (7, 10): 0.387,
    (8, 9): 0.519
}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_ranking_csv(df: pd.DataFrame, model_name: str, output_dir: str) -> Path:
    """Write model ranking CSV."""
    target_dir = Path(output_dir) / "rankings"
    _ensure_dir(target_dir)
    path = target_dir / f"{model_name}_rankings.csv"
    df.to_csv(path, index=False)
    return path


def write_bracket_json(bracket: dict[str, Any], strategy_name: str, output_dir: str) -> Path:
    """Write bracket JSON for one strategy."""
    target_dir = Path(output_dir) / "brackets"
    _ensure_dir(target_dir)
    path = target_dir / f"bracket_{strategy_name}.json"
    path.write_text(json.dumps(bracket, indent=2), encoding="utf-8")
    return path


def write_bracket_html(
    bracket: dict[str, Any],
    strategy_name: str,
    output_dir: str,
    template_dir: str = "templates"
) -> Path:
    """Render bracket HTML via Jinja template."""
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"])
    )
    template = env.get_template("bracket.html.j2")
    html = template.render(
        strategy_name=strategy_name,
        description=bracket.get("description", ""),
        champion=bracket.get("champion", ""),
        final_four=bracket.get("final_four", []),
        regions=bracket.get("rounds", {}),
        final_four_games=bracket.get("final_four_games", []),
        championship_game=bracket.get("championship_game", [])
    )
    target_dir = Path(output_dir) / "brackets"
    _ensure_dir(target_dir)
    path = target_dir / f"bracket_{strategy_name}.html"
    path.write_text(html, encoding="utf-8")
    return path


def classify_matchup_verdict(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    win_prob_a: float,
    cinderella_score_b: float,
    models_picking_upset: int
) -> dict[str, str]:
    """Classify matchup into verdict label and visual metadata."""
    seed_a = int(team_a.get("Seed", 16))
    seed_b = int(team_b.get("Seed", 16))
    seed_gap = max(0, seed_b - seed_a)
    is_true_upset_spot = seed_gap >= 2

    if (
        is_true_upset_spot
        and 0.55 <= win_prob_a <= 0.75
        and cinderella_score_b >= 0.40
        and models_picking_upset >= 3
    ):
        return {
            "verdict": "TRAP GAME",
            "icon": "⚠️",
            "color": "#dc2626",
            "pick": str(team_a.get("Team")),
            "pick_strength": "SOFT"
        }
    if win_prob_a >= 0.85:
        return {
            "verdict": "LOCK",
            "icon": "🔒",
            "color": "#1a7f37",
            "pick": str(team_a.get("Team")),
            "pick_strength": "STRONG"
        }
    # Reserve "UPSET ALERT" for true probability flips only. High Cinderella/model
    # disagreement without a flipped edge should remain a toss-up or lean.
    if is_true_upset_spot and win_prob_a < 0.5:
        return {
            "verdict": "UPSET ALERT",
            "icon": "⚡",
            "color": "#ef4444",
            "pick": str(team_b.get("Team")),
            "pick_strength": "MEDIUM"
        }
    if win_prob_a >= 0.65:
        return {
            "verdict": "LEAN",
            "icon": "→",
            "color": "#2da44e",
            "pick": str(team_a.get("Team")),
            "pick_strength": "MEDIUM"
        }
    if win_prob_a <= 0.35:
        return {
            "verdict": "LEAN",
            "icon": "→",
            "color": "#2da44e",
            "pick": str(team_b.get("Team")),
            "pick_strength": "MEDIUM"
        }
    return {
        "verdict": "TOSS-UP",
        "icon": "🎲",
        "color": "#f59e0b",
        "pick": str(team_a.get("Team")) if win_prob_a >= 0.5 else str(team_b.get("Team")),
        "pick_strength": "WEAK"
    }


def _count_upset_picks(
    higher_name: str,
    lower_name: str,
    brackets: dict[str, dict[str, Any]]
) -> int:
    """Count how many strategy brackets pick the lower-seeded team to win."""
    upset_count = 0
    for bracket in brackets.values():
        for region_rounds in bracket.get("rounds", {}).values():
            for round_games in region_rounds.values():
                for game in round_games:
                    h_team = str(game.get("higher_seed_team", ""))
                    l_team = str(game.get("lower_seed_team", ""))
                    if h_team == higher_name and l_team == lower_name:
                        if game.get("is_upset"):
                            upset_count += 1
    return upset_count


def _build_verdict_entry(
    higher_seed: dict[str, Any],
    lower_seed: dict[str, Any],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    brackets: dict[str, dict[str, Any]] | None,
    region: str = "",
    round_name: str = ""
) -> dict[str, Any]:
    """Build a single matchup verdict dict."""
    p_higher = float(win_prob_fn(higher_seed, lower_seed))
    c_score = float(lower_seed.get("CinderellaScore") or 0.0)
    h_name = str(higher_seed.get("Team"))
    l_name = str(lower_seed.get("Team"))
    upset_picks = _count_upset_picks(h_name, l_name, brackets) if brackets else 0
    verdict = classify_matchup_verdict(higher_seed, lower_seed, p_higher, c_score, upset_picks)
    higher_divergence = compute_rank_divergence(higher_seed, {})
    lower_divergence = compute_rank_divergence(lower_seed, {})
    seed_a = int(higher_seed.get("Seed", 16))
    seed_b = int(lower_seed.get("Seed", 16))
    matchup_key = (min(seed_a, seed_b), max(seed_a, seed_b))

    ranking_signal_flags: list[str] = []
    if seed_a <= 6 and higher_divergence > 0.65:
        ranking_signal_flags.append("Committee darling ⚠")
    if seed_b >= 9 and lower_divergence < 0.35:
        ranking_signal_flags.append("Analytics value pick ✓")

    return {
        "region": region,
        "round": round_name,
        "team_a": {
            "name": h_name,
            "seed": seed_a,
            "power_score": float(higher_seed.get("PowerScore") or 0.0),
            "adjEM": float(higher_seed.get("AdjEM") or 0.0),
            "fraud_score": float(higher_seed.get("FraudScore") or 0.0),
            "fraud_level": str(higher_seed.get("FraudLevel") or ""),
        },
        "team_b": {
            "name": l_name,
            "seed": seed_b,
            "power_score": float(lower_seed.get("PowerScore") or 0.0),
            "adjEM": float(lower_seed.get("AdjEM") or 0.0),
            "cinderella_score": c_score,
            "cinderella_level": str(lower_seed.get("CinderellaAlertLevel") or ""),
        },
        "win_prob_a": p_higher,
        "predicted_spread": predicted_spread(higher_seed, lower_seed),
        "historical_upset_rate": HISTORICAL_UPSET_RATES.get(matchup_key, 0.30),
        "models_agreeing": len(brackets) - upset_picks if brackets else 0,
        "models_picking_upset": upset_picks,
        "verdict": verdict["verdict"],
        "verdict_icon": verdict["icon"],
        "verdict_color": verdict["color"],
        "pick": verdict["pick"],
        "pick_strength": verdict["pick_strength"],
        "volatility_flag": bool(float(lower_seed.get("Volatility_Score") or 0.0) > 0.65),
        "rank_divergence_a": round(float(higher_divergence), 3),
        "rank_divergence_b": round(float(lower_divergence), 3),
        "ranking_signal_flags": ranking_signal_flags,
    }


def write_matchup_verdicts_json(
    teams: list[dict[str, Any]],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    output_dir: str,
    brackets: dict[str, dict[str, Any]] | None = None,
    bracket_input: dict[str, Any] | None = None
) -> Path:
    """Precompute matchup verdicts for actual bracket matchups."""
    from engine import FIRST_ROUND_MATCHUPS

    team_lookup = {str(t.get("Team")): t for t in teams}
    matchups: list[dict[str, Any]] = []

    if bracket_input:
        teams_by_region: dict[str, list[dict[str, Any]]] = {}
        for entry in bracket_input.get("teams", []):
            region = str(entry.get("region", ""))
            name = str(entry.get("team", ""))
            enriched = dict(team_lookup.get(name, {}))
            enriched["Team"] = name
            enriched["Seed"] = int(entry.get("seed", 16))
            enriched["slot"] = int(entry.get("slot", 99))
            teams_by_region.setdefault(region, []).append(enriched)

        for region, region_teams in teams_by_region.items():
            sorted_teams = sorted(region_teams, key=lambda t: int(t.get("slot", 99)))
            for slot_a, slot_b in FIRST_ROUND_MATCHUPS:
                if slot_a >= len(sorted_teams) or slot_b >= len(sorted_teams):
                    continue
                ta, tb = sorted_teams[slot_a], sorted_teams[slot_b]
                seed_a = int(ta.get("Seed", 16))
                seed_b = int(tb.get("Seed", 16))
                higher = ta if seed_a <= seed_b else tb
                lower = tb if seed_a <= seed_b else ta
                matchups.append(
                    _build_verdict_entry(higher, lower, win_prob_fn, brackets, region, "R64")
                )
    else:
        for i, team_a in enumerate(teams):
            for j, team_b in enumerate(teams):
                if i >= j:
                    continue
                seed_a = int(team_a.get("Seed", 16))
                seed_b = int(team_b.get("Seed", 16))
                higher = team_a if seed_a <= seed_b else team_b
                lower = team_b if higher is team_a else team_a
                matchups.append(
                    _build_verdict_entry(higher, lower, win_prob_fn, brackets)
                )

    payload = {"matchups": matchups}
    path = Path(output_dir) / "bracket_matchup_verdicts.json"
    _ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_simulation_json(results: dict[str, Any], output_dir: str, metadata: dict[str, Any] | None = None) -> Path:
    """Write simulation JSON artifact."""
    payload = {"results": results}
    if metadata:
        payload.update(metadata)
    path = Path(output_dir) / "simulation_results.json"
    _ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_summary_json(summary: dict[str, Any], output_dir: str) -> Path:
    """Write bracket summary JSON artifact."""
    path = Path(output_dir) / "bracket_summary.json"
    _ensure_dir(path.parent)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def write_bracket_pick_sheet(
    rankings: dict[str, pd.DataFrame],
    simulation: dict[str, Any],
    verdicts: dict[str, Any],
    output_dir: str
) -> Path:
    """Create plain-text bracket decision guide."""
    power = rankings.get("power", next(iter(rankings.values())))
    top_rows = power.head(10)
    lines = [
        "MARCH MATHNESS - BRACKET DECISION GUIDE",
        "=" * 67,
        "",
        "TOP 10 POWER RANKINGS",
        "-" * 67
    ]
    for _, row in top_rows.iterrows():
        lines.append(
            f"#{int(row.get('Rank', 0)): <3} {row.get('Team', ''):<24} "
            f"Seed:{int(row.get('Seed', 0)):<2} Score:{float(row.get('PowerScore', 0)):.1f}"
        )
    lines.extend(["", "ROUND OF 64 — MATCHUP VERDICTS", "-" * 67])
    by_region: dict[str, list[dict[str, Any]]] = {}
    for matchup in verdicts.get("matchups", []):
        region = matchup.get("region", "")
        by_region.setdefault(region, []).append(matchup)
    for region, region_matchups in by_region.items():
        if region:
            lines.append(f"\n  {region.upper()}")
        for matchup in region_matchups:
            pick_prob = matchup['win_prob_a'] if matchup['pick'] == matchup['team_a']['name'] else 1.0 - matchup['win_prob_a']
            lines.append(
                f"  {matchup['verdict_icon']} ({matchup['team_a']['seed']}) {matchup['team_a']['name']:<20} "
                f"vs ({matchup['team_b']['seed']}) {matchup['team_b']['name']:<20} "
                f"-> {matchup['pick']} [{matchup['verdict']}] {pick_prob*100:.0f}%"
            )
    lines.extend(["", "CHAMPIONSHIP PROBABILITIES", "-" * 67])
    sorted_sim = sorted(
        simulation.items(),
        key=lambda item: float(item[1].get("Champion", 0.0)),
        reverse=True
    )
    for team, rounds in sorted_sim[:12]:
        lines.append(f"{team:<24} {float(rounds.get('Champion', 0.0))*100:>5.1f}%")

    path = Path(output_dir) / "my_bracket_picks.txt"
    _ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_all_outputs(
    rankings: dict[str, pd.DataFrame],
    brackets: dict[str, dict[str, Any]],
    simulation: dict[str, Any],
    summary: dict[str, Any],
    config: dict[str, Any],
    all_teams_for_verdicts: list[dict[str, Any]] | None = None,
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float] | None = None,
    bracket_input: dict[str, Any] | None = None
) -> dict[str, list[str]]:
    """Write all output artifacts and return written path summary."""
    output_dir = config.get("output_dir", "./outputs")
    written: dict[str, list[str]] = {"rankings": [], "brackets": [], "other": []}

    for model_name, df in rankings.items():
        path = write_ranking_csv(df, model_name, output_dir)
        written["rankings"].append(str(path))

    for strategy_name, bracket in brackets.items():
        written["brackets"].append(str(write_bracket_json(bracket, strategy_name, output_dir)))
        try:
            html_path = write_bracket_html(bracket, strategy_name, output_dir)
            written["brackets"].append(str(html_path))
        except Exception as exc:
            log.warning("HTML bracket rendering failed for %s: %s", strategy_name, exc)

    written["other"].append(str(write_simulation_json(simulation, output_dir)))
    written["other"].append(str(write_summary_json(summary, output_dir)))

    if all_teams_for_verdicts is not None and win_prob_fn is not None:
        verdict_path = write_matchup_verdicts_json(
            all_teams_for_verdicts, win_prob_fn, output_dir,
            brackets=brackets or None, bracket_input=bracket_input
        )
        written["other"].append(str(verdict_path))
        verdict_payload = json.loads(Path(verdict_path).read_text(encoding="utf-8"))
        pick_sheet = write_bracket_pick_sheet(rankings, simulation, verdict_payload, output_dir)
        written["other"].append(str(pick_sheet))

    return written

