"""Output writers for rankings, brackets, simulation, and dashboard assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from engine.win_probability import predicted_spread

HISTORICAL_UPSET_RATES: dict[tuple[int, int], float] = {
    (1, 16): 0.0125,
    (2, 15): 0.069,
    (3, 14): 0.144,
    (4, 13): 0.206,
    (5, 12): 0.356,
    (6, 11): 0.388,
    (7, 10): 0.375,
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


def write_conference_strength_csv(conf_ratings: pd.DataFrame, output_dir: str) -> Path:
    """Write conference strength CSV."""
    target_dir = Path(output_dir) / "rankings"
    _ensure_dir(target_dir)
    path = target_dir / "conference_strength.csv"
    conf_ratings.to_csv(path, index=False)
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
        regions=bracket.get("rounds", {})
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
    if 0.55 <= win_prob_a <= 0.75 and cinderella_score_b >= 0.40 and models_picking_upset >= 3:
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
    if win_prob_a < 0.5 or (cinderella_score_b >= 0.55 and models_picking_upset >= 4):
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
    return {
        "verdict": "TOSS-UP",
        "icon": "🎲",
        "color": "#f59e0b",
        "pick": str(team_a.get("Team")),
        "pick_strength": "WEAK"
    }


def write_matchup_verdicts_json(
    teams: list[dict[str, Any]],
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    output_dir: str
) -> Path:
    """Precompute matchup verdicts for UI rendering."""
    matchups: list[dict[str, Any]] = []
    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if i >= j:
                continue
            seed_a = int(team_a.get("Seed", 16))
            seed_b = int(team_b.get("Seed", 16))
            higher_seed = team_a if seed_a <= seed_b else team_b
            lower_seed = team_b if higher_seed is team_a else team_a
            p_higher = float(win_prob_fn(higher_seed, lower_seed))
            c_score = float(lower_seed.get("CinderellaScore") or 0.0)
            verdict = classify_matchup_verdict(higher_seed, lower_seed, p_higher, c_score, models_picking_upset=0)
            matchup_key = (int(min(seed_a, seed_b)), int(max(seed_a, seed_b)))
            matchups.append(
                {
                    "team_a": {"name": higher_seed.get("Team"), "seed": int(higher_seed.get("Seed", 16))},
                    "team_b": {"name": lower_seed.get("Team"), "seed": int(lower_seed.get("Seed", 16))},
                    "win_prob_a": p_higher,
                    "predicted_spread": predicted_spread(higher_seed, lower_seed),
                    "historical_upset_rate": HISTORICAL_UPSET_RATES.get(matchup_key, 0.30),
                    "verdict": verdict["verdict"],
                    "verdict_icon": verdict["icon"],
                    "verdict_color": verdict["color"],
                    "pick": verdict["pick"],
                    "pick_strength": verdict["pick_strength"],
                    "volatility_flag": bool(float(lower_seed.get("Volatility_Score") or 0.0) > 0.65)
                }
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
    lines.extend(["", "MATCHUP VERDICTS", "-" * 67])
    for matchup in verdicts.get("matchups", [])[:40]:
        lines.append(
            f"{matchup['verdict_icon']} {matchup['team_a']['name']} ({matchup['team_a']['seed']}) "
            f"vs {matchup['team_b']['name']} ({matchup['team_b']['seed']}) "
            f"-> {matchup['pick']} [{matchup['verdict']}] ({matchup['win_prob_a']*100:.1f}%)"
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
    conf_ratings: pd.DataFrame | None = None,
    all_teams_for_verdicts: list[dict[str, Any]] | None = None,
    win_prob_fn: Callable[[dict[str, Any], dict[str, Any]], float] | None = None
) -> dict[str, list[str]]:
    """Write all output artifacts and return written path summary."""
    output_dir = config.get("output_dir", "./outputs")
    written: dict[str, list[str]] = {"rankings": [], "brackets": [], "other": []}

    for model_name, df in rankings.items():
        path = write_ranking_csv(df, model_name, output_dir)
        written["rankings"].append(str(path))

    if conf_ratings is not None and not conf_ratings.empty:
        written["rankings"].append(str(write_conference_strength_csv(conf_ratings, output_dir)))

    for strategy_name, bracket in brackets.items():
        written["brackets"].append(str(write_bracket_json(bracket, strategy_name, output_dir)))
        try:
            html_path = write_bracket_html(bracket, strategy_name, output_dir)
            written["brackets"].append(str(html_path))
        except Exception:
            # HTML writing should not block core pipeline outputs.
            pass

    written["other"].append(str(write_simulation_json(simulation, output_dir)))
    written["other"].append(str(write_summary_json(summary, output_dir)))

    if all_teams_for_verdicts is not None and win_prob_fn is not None:
        verdict_path = write_matchup_verdicts_json(all_teams_for_verdicts, win_prob_fn, output_dir)
        written["other"].append(str(verdict_path))
        verdict_payload = json.loads(Path(verdict_path).read_text(encoding="utf-8"))
        pick_sheet = write_bracket_pick_sheet(rankings, simulation, verdict_payload, output_dir)
        written["other"].append(str(pick_sheet))

    return written

