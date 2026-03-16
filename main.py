"""March Mathness CLI entry point."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from engine.bracket_generator import generate_all_brackets, generate_bracket_summary
from engine.calibration import calibrate_probability, load_calibration_model
from engine.ingestion import load_bracket, load_teams
from engine.live_results import fetch_results
from engine.matchup_paths import generate_matchup_paths
from engine.normalization import (
    compute_consistency_score,
    compute_derived_features,
    compute_volatility_score,
    normalize_all_teams,
    normalize_value
)
from engine.output import write_all_outputs
from engine.scoring import RANKING_KEY_TO_MODEL, generate_all_rankings, seed_mismatch
from engine.simulation import generate_modal_bracket, simulate_bracket
from engine.tournament_bonus import apply_tournament_bonuses, build_remaining_bracket
from engine.win_probability import production_win_probability


def _load_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def _apply_coach_scores(df: pd.DataFrame, coach_path: str | None) -> None:
    """Apply coach_scores.json to Coach_Tourney_Experience column in-place."""
    if not coach_path:
        return
    p = Path(coach_path)
    if not p.exists():
        return
    scores = json.loads(p.read_text(encoding="utf-8"))
    if not scores or len(scores) <= 1:
        return
    default = float(scores.get("_default", 3))
    df["Coach_Tourney_Experience"] = df["Team"].apply(
        lambda team: float(scores.get(team, default))
    )


def _prepare_norms(df: pd.DataFrame) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    norms = normalize_all_teams(df)
    deriveds = [compute_derived_features(norms[i], row.to_dict()) for i, (_, row) in enumerate(df.iterrows())]
    for i, (_, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()
        norms[i]["Consistency_Score"] = compute_consistency_score(row_dict)
        norms[i]["Volatility_Score"] = compute_volatility_score(row_dict, norms[i])
        df.at[i, "Consistency_Score"] = norms[i]["Consistency_Score"]
        df.at[i, "Volatility_Score"] = norms[i]["Volatility_Score"]
        wins = pd.to_numeric(pd.Series([row_dict.get("Wins")]), errors="coerce").iloc[0]
        games = pd.to_numeric(pd.Series([row_dict.get("Games")]), errors="coerce").iloc[0]
        win_pct = float(wins) / float(games) if pd.notna(wins) and pd.notna(games) and games > 0 else 0.65
        last_10 = float(row_dict.get("Last_10_Games_Metric", 0.65))
        df.at[i, "MomentumDelta"] = round(last_10 - win_pct, 4)

        actual_seed = pd.to_numeric(pd.Series([row_dict.get("Seed")]), errors="coerce").iloc[0]
        comp_rank = pd.to_numeric(pd.Series([row_dict.get("CompRank")]), errors="coerce").iloc[0]
        if pd.notna(actual_seed) and pd.notna(comp_rank):
            sm = seed_mismatch(int(actual_seed), int(comp_rank))
        else:
            sm = 0.0
        df.at[i, "SeedMismatch"] = sm
        norms[i]["SeedMismatch_norm"] = normalize_value(sm, 0, 1)
    return norms, deriveds


def _print_terminal_summary(rankings: dict[str, pd.DataFrame]) -> None:
    power = rankings.get("power", next(iter(rankings.values())))
    print("\n" + "=" * 67)
    print("TOP 10 POWER RANKINGS")
    print("-" * 67)
    for _, row in power.head(10).iterrows():
        print(
            f"#{int(row.get('Rank', 0)): <3} {row.get('Team', ''):<24} "
            f"Seed:{int(row.get('Seed', 0)):<2} Score:{float(row.get('PowerScore', 0)):.1f} "
            f"AdjEM:+{float(row.get('AdjEM', 0)):.1f}"
        )

    cinderella_df = rankings.get("cinderella")
    if cinderella_df is not None and "CinderellaAlertLevel" in cinderella_df.columns:
        high = cinderella_df[cinderella_df["CinderellaAlertLevel"] == "HIGH"].sort_values("CinderellaScore", ascending=False)
        if not high.empty:
            print("\n🔴 CINDERELLA ALERTS (HIGH)")
            print("-" * 67)
            for _, row in high.iterrows():
                print(
                    f"{row.get('Team', ''):<24} #{int(row.get('Seed', 0)):<2} "
                    f"Score:{float(row.get('CinderellaScore', 0)):.3f}"
                )

    if "FraudLevel" in power.columns:
        fraud = power[power["FraudLevel"].isin(["HIGH", "MEDIUM"])]
        if not fraud.empty:
            print("\n💀 FRAUD ALERTS")
            print("-" * 67)
            for _, row in fraud.head(8).iterrows():
                print(
                    f"{row.get('Team', ''):<24} #{int(row.get('Seed', 0)):<2} "
                    f"Fraud:{float(row.get('FraudScore', 0)):.3f} [{row.get('FraudLevel', '')}]"
                )


_SCORING_COLUMNS = [
    "PowerScore", "FraudScore", "FraudLevel", "FraudExplanation",
    "CinderellaScore", "CinderellaAlertLevel",
    "Consistency_Score", "Volatility_Score", "RankDivergence",
]


def _enrich_teams_from_rankings(
    df: pd.DataFrame,
    rankings: dict[str, pd.DataFrame],
) -> None:
    """Merge scoring columns from the power ranking back into df in-place.

    Without this, team dicts used for bracket generation, simulation,
    and matchup verdicts lack FraudScore, CinderellaScore, etc.
    """
    power = rankings.get("power")
    if power is None:
        return
    score_lookup: dict[str, dict[str, Any]] = {}
    for _, row in power.iterrows():
        team = str(row.get("Team", ""))
        score_lookup[team] = {
            col: row[col] for col in _SCORING_COLUMNS if col in power.columns
        }
    for col in _SCORING_COLUMNS:
        if col not in df.columns:
            df[col] = None
    for idx, row in df.iterrows():
        team = str(row["Team"])
        if team in score_lookup:
            for col, val in score_lookup[team].items():
                df.at[idx, col] = val


def _build_team_lookup(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {str(row["Team"]): row.to_dict() for _, row in df.iterrows()}


def _attach_bracket_stats(
    bracket: dict[str, Any],
    team_lookup: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    teams_by_region = bracket["teams_by_region"]
    result: dict[str, list[dict[str, Any]]] = {}
    for region, teams in teams_by_region.items():
        region_list = []
        for team in teams:
            name = str(team["team"])
            merged = dict(team_lookup.get(name, {"Team": name, "AdjEM": 0.0, "Adj_T": 68.0, "Seed": team.get("Seed", 16)}))
            merged["Team"] = name
            merged["Seed"] = int(team.get("Seed", merged.get("Seed", 16)))
            merged["slot"] = int(team.get("slot", 16))
            region_list.append(merged)
        result[region] = sorted(region_list, key=lambda t: int(t.get("slot", 99)))
    return result


def run_tournament_update(config: dict[str, Any]) -> None:
    """Mid-tournament rescore pipeline."""
    print("\n🏀 MID-TOURNAMENT UPDATE MODE")
    print("=" * 67)
    df = load_teams(config["data_file"], config.get("overrides_file"))
    _apply_coach_scores(df, config.get("coach_scores_file"))
    results = fetch_results(config)
    completed_games = results.get("completed_games", [])
    print(f"  ✓ {len(completed_games)} completed games found")

    all_losers = {str(g.get("loser_name")) for g in completed_games}
    bracket = load_bracket(config["bracket_file"])
    tournament_teams = {str(t["team"]) for t in bracket["teams"]}
    surviving_teams = [team for team in tournament_teams if team not in all_losers]
    print(f"  ✓ {len(surviving_teams)} surviving teams")

    df_updated = apply_tournament_bonuses(
        df,
        completed_games,
        surviving_teams,
        max_adjem_bonus=float(config.get("max_adjEM_bonus", 4.0))
    )
    df_survivors = df_updated[df_updated["Team"].isin(surviving_teams)].copy()

    norms, deriveds = _prepare_norms(df_survivors)
    rankings = generate_all_rankings(df_survivors, norms, deriveds)
    _enrich_teams_from_rankings(df_survivors, rankings)

    remaining_bracket = build_remaining_bracket(config, completed_games, df_survivors)
    sim_results = simulate_bracket(
        remaining_bracket,
        production_win_probability,
        n_sims=int(config["n_simulations"]),
        seed=int(config["random_seed"])
    )
    summary = {"source": results.get("source"), "completed_games": len(completed_games)}
    write_all_outputs(
        rankings,
        {},
        sim_results,
        summary,
        config,
        all_teams_for_verdicts=df_survivors.to_dict("records"),
        win_prob_fn=production_win_probability
    )
    print(f"✅ Update complete. Outputs: {config['output_dir']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="March Mathness")
    parser.add_argument("--mode", choices=["full", "rankings", "simulate", "update"], default="full")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--sims", type=int, default=None)
    args = parser.parse_args()

    config = _load_config(args.config)
    if args.seed is not None:
        config["random_seed"] = args.seed
    if args.sims is not None:
        config["n_simulations"] = args.sims

    if args.mode == "update":
        run_tournament_update(config)
        return

    print("=" * 67)
    print("MARCH MATHNESS - Tournament Prediction Engine")
    print("=" * 67)
    t0 = time.time()

    df = load_teams(config["data_file"], config.get("overrides_file"))
    _apply_coach_scores(df, config.get("coach_scores_file"))
    norms, deriveds = _prepare_norms(df)
    rankings = generate_all_rankings(df, norms, deriveds)
    _enrich_teams_from_rankings(df, rankings)
    _print_terminal_summary(rankings)

    if args.mode == "rankings":
        write_all_outputs(
            rankings,
            {},
            {},
            {},
            config,
            all_teams_for_verdicts=df.to_dict("records"),
            win_prob_fn=production_win_probability
        )
        print(f"\n✅ Rankings complete in {time.time() - t0:.1f}s")
        return

    bracket = load_bracket(config["bracket_file"])
    team_lookup = _build_team_lookup(df)
    bracket_with_stats = _attach_bracket_stats(bracket, team_lookup)

    calibration_model = load_calibration_model()
    if calibration_model is not None:
        def calibrated_win_prob(a: dict[str, Any], b: dict[str, Any]) -> float:
            raw = production_win_probability(a, b)
            return calibrate_probability(raw, calibration_model)
        win_prob_fn = calibrated_win_prob
    else:
        win_prob_fn = production_win_probability

    simulation_results = simulate_bracket(
        bracket_with_stats,
        win_prob_fn,
        n_sims=int(config["n_simulations"]),
        seed=int(config["random_seed"])
    )
    modal = generate_modal_bracket(simulation_results, bracket_with_stats, win_prob_fn)

    model_scores: dict[str, dict[str, float]] = {}
    for ranking_key, rdf in rankings.items():
        score_col = "PowerScore" if ranking_key == "power" else "ModelScore"
        scoring_model = RANKING_KEY_TO_MODEL.get(ranking_key, ranking_key)
        for _, row in rdf.iterrows():
            team = str(row["Team"])
            score = float(row.get(score_col, row.get("PowerScore", 50.0)))
            model_scores.setdefault(team, {})
            model_scores[team][scoring_model] = score

    all_brackets = generate_all_brackets(bracket_with_stats, model_scores, simulation_results, win_prob_fn)
    summary = generate_bracket_summary(all_brackets)
    summary["modal_bracket"] = modal
    matchup_paths = generate_matchup_paths(
        bracket_with_stats,
        simulation_results,
        win_prob_fn,
        rankings["power"],
        top_n=20,
    )

    write_all_outputs(
        rankings,
        all_brackets,
        simulation_results,
        summary,
        config,
        all_teams_for_verdicts=df.to_dict("records"),
        win_prob_fn=win_prob_fn,
        bracket_input=bracket,
        matchup_paths=matchup_paths,
    )

    print(f"\n✅ Complete in {time.time() - t0:.1f}s")
    print(f"Outputs saved to: {config['output_dir']}")


if __name__ == "__main__":
    main()

