"""Historical backtest runner."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from engine.win_probability import production_win_probability


def _load_year_data(year: int) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    teams_path = Path(f"data/historical/{year}_teams.csv")
    games_path = Path(f"data/historical/{year}_games.csv")
    if not teams_path.exists() or not games_path.exists():
        return None
    teams = pd.read_csv(teams_path)
    games = pd.read_csv(games_path)
    return teams, games


def _evaluate_year(year: int) -> dict[str, float] | None:
    payload = _load_year_data(year)
    if payload is None:
        return None
    teams_df, games_df = payload
    team_lookup = {str(row["Team"]): row.to_dict() for _, row in teams_df.iterrows()}
    correct = 0
    log_loss_total = 0.0
    brier_total = 0.0
    n = 0
    for _, game in games_df.iterrows():
        team_a = team_lookup.get(str(game["team_a"]))
        team_b = team_lookup.get(str(game["team_b"]))
        if team_a is None or team_b is None:
            continue
        prob_a = production_win_probability(team_a, team_b)
        actual_a = 1.0 if str(game["winner"]) == str(game["team_a"]) else 0.0
        pred_a = 1.0 if prob_a >= 0.5 else 0.0
        correct += int(pred_a == actual_a)
        prob_winner = prob_a if actual_a == 1.0 else (1.0 - prob_a)
        log_loss_total += -np.log(max(prob_winner, 1e-9))
        brier_total += (prob_a - actual_a) ** 2
        n += 1
    if n == 0:
        return None
    return {
        "year": year,
        "accuracy": correct / n,
        "log_loss": log_loss_total / n,
        "brier": brier_total / n
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest March Mathness on historical data")
    parser.add_argument("--years", nargs="+", type=int, required=True, help="e.g. --years 2022 2023 2024")
    args = parser.parse_args()

    rows = []
    for year in args.years:
        result = _evaluate_year(year)
        if result is None:
            print(f"Year {year}: skipped (missing data files)")
            continue
        rows.append(result)

    if not rows:
        print("No backtest results generated.")
        return

    df = pd.DataFrame(rows)
    avg = {
        "year": "Avg",
        "accuracy": df["accuracy"].mean(),
        "log_loss": df["log_loss"].mean(),
        "brier": df["brier"].mean()
    }

    print("Year  | Accuracy | Log Loss | Brier")
    for _, row in df.iterrows():
        print(
            f"{int(row['year'])}  | {row['accuracy']*100:6.2f}%  | "
            f"{row['log_loss']:.3f}    | {row['brier']:.3f}"
        )
    print(
        f"{avg['year']}   | {avg['accuracy']*100:6.2f}%  | "
        f"{avg['log_loss']:.3f}    | {avg['brier']:.3f}"
    )


if __name__ == "__main__":
    main()

