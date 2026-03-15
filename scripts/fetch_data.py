"""Fetch and assemble teams_input.csv from free sources."""

from __future__ import annotations

import argparse
import io
import json
from datetime import date
from pathlib import Path
from typing import Any

import cloudscraper
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

TEAM_NAME_MAP: dict[str, str] = {
    "UConn": "Connecticut",
    "UCSB": "UC Santa Barbara",
    "LMU (CA)": "Loyola Marymount",
    "TAM C. Christi": "Texas A&M-Corpus Christi",
    "Col. of Charleston": "College of Charleston",
    "SIU Edwardsville": "SIUE",
    "St. Mary's (CA)": "Saint Mary's",
    "FIU": "Florida International"
}

PROGRAM_PRESTIGE: dict[str, int] = {
    "Kansas": 10,
    "Kentucky": 10,
    "Duke": 10,
    "North Carolina": 9,
    "Connecticut": 9,
    "Gonzaga": 8,
    "Michigan State": 8,
    "Arizona": 8,
    "UCLA": 8,
    "Villanova": 8,
    "Houston": 7,
    "Tennessee": 7,
    "Auburn": 7,
    "Creighton": 6,
    "Baylor": 7,
    "Arkansas": 6,
    "Florida": 7,
    "Virginia": 7
}


def normalize_team_name(name: str) -> str:
    return TEAM_NAME_MAP.get(str(name).strip(), str(name).strip())


def get_program_prestige(team_name: str) -> float:
    return float(PROGRAM_PRESTIGE.get(team_name, 2))


def fetch_torvik_main(year: int) -> pd.DataFrame:
    """Fetch Torvik season team CSV (requires cloudscraper)."""
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_team_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    df = df.rename(
        columns={
            "AdjOE": "AdjO",
            "AdjDE": "AdjD",
            "EFG%": "eFG%",
            "EFGD%": "Opp_eFG%",
            "TOR": "TO%",
            "TORD": "Opp_TO%",
            "ORB": "OR%",
            "DRB": "DR%",
            "FTRD": "Opp_FTR",
            "2P%D": "2P_%_D",
            "3P%D": "3P_%_D",
            "3PR": "3P_Rate",
            "3PRD": "3P_Rate_D",
            "Blk%": "Blk_%",
            "Blk%D": "Blked_%",
            "Tempo": "Adj_T",
            "Raw Tempo": "Raw_T",
            "Avg Hgt": "Avg_Hgt",
            "Eff Hgt": "Eff_Hgt",
            "Experience": "Exp",
            "PPP Off": "PPP_Off",
            "PPP Def": "PPP_Def",
            "Rank": "Torvik_Rank",
            "Conf": "Conference",
            "Rec": "Record",
            "wAB": "WAB"
        }
    )
    df["Team"] = df["Team"].apply(normalize_team_name)
    df["AdjEM"] = pd.to_numeric(df["AdjO"], errors="coerce") - pd.to_numeric(df["AdjD"], errors="coerce")
    if "Record" in df.columns:
        rec_split = df["Record"].astype(str).str.split("-", expand=True)
        df["Wins"] = pd.to_numeric(rec_split[0], errors="coerce")
        df["Games"] = df["Wins"] + pd.to_numeric(rec_split[1], errors="coerce")
    return df


def fetch_massey() -> pd.DataFrame | None:
    """Fetch Massey ratings table (requires cloudscraper)."""
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.masseyratings.com/cb/ncaa-d1/ratings"
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), header=0)
        df = tables[0]
        df.columns = [str(c).strip() for c in df.columns]
        df["Team"] = df.iloc[:, 1].apply(normalize_team_name)
        df["Massey_Rank"] = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        return df[["Team", "Massey_Rank"]].dropna()
    except Exception as exc:
        print(f"  ⚠ Massey fetch failed: {exc}")
        return None


def fetch_ap_poll() -> pd.DataFrame:
    """Fetch AP poll rankings from ESPN."""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        data = requests.get(url, headers=headers, timeout=10).json()
        rows: list[dict[str, Any]] = []
        for poll in data.get("rankings", []):
            if "AP" in poll.get("name", ""):
                for entry in poll.get("ranks", []):
                    rows.append(
                        {
                            "Team": normalize_team_name(entry["team"]["displayName"]),
                            "AP_Poll_Rank": int(entry["current"])
                        }
                    )
        return pd.DataFrame(rows)
    except Exception as exc:
        print(f"  ⚠ AP poll fetch failed: {exc}")
        return pd.DataFrame(columns=["Team", "AP_Poll_Rank"])


def fetch_torvik_early_snapshot(year: int) -> pd.DataFrame | None:
    """Fetch Torvik time-machine early rank snapshot."""
    try:
        snapshot_date = date(year, 2, 15).strftime("%Y%m%d")
        url = f"http://barttorvik.com/timemachine/team_results/{snapshot_date}_team_results.json.gz"
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        import gzip

        payload = json.loads(gzip.decompress(response.content))
        df = pd.DataFrame(payload)
        df["Team"] = df["Team"].apply(normalize_team_name)
        df = df.rename(columns={"Rank": "TRank_Early"})
        return df[["Team", "TRank_Early"]]
    except Exception as exc:
        print(f"  ⚠ Torvik early snapshot unavailable: {exc}")
        return None


def fetch_espn_net_rank() -> pd.DataFrame | None:
    """Fetch ESPN team list and extract NET ranking if available."""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
        params = {"limit": 400, "groups": 50, "enable": "standings"}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        rows: list[dict[str, Any]] = []
        for team in data.get("teams", []):
            name = normalize_team_name(team.get("displayName", ""))
            net_rank = None
            for stat in team.get("statistics", []):
                if isinstance(stat, dict) and "netRanking" in stat:
                    net_rank = stat.get("netRanking")
            rows.append({"Team": name, "NET_Rank": net_rank})
        df = pd.DataFrame(rows).dropna(subset=["NET_Rank"])
        if not df.empty:
            df["NET_Rank"] = df["NET_Rank"].astype(int)
        return df
    except Exception as exc:
        print(f"  ⚠ ESPN NET fetch failed: {exc}")
        return None


def compute_player_metrics(year: int) -> pd.DataFrame | None:
    """Compute Star_Player_Index and Bench_Minutes_Pct from Torvik player CSV."""
    try:
        scraper = cloudscraper.create_scraper()
        url = f"http://barttorvik.com/{year}_player_results.csv"
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        players = pd.read_csv(io.StringIO(response.text))
        players["Team"] = players["Team"].apply(normalize_team_name)
        rows = []
        for team_name, group in players.groupby("Team"):
            group = group.sort_values("Min", ascending=False)
            top_player_bpm = float(group.iloc[0].get("BPM", 0.0)) if len(group) > 0 else 0.0
            star_index = float(np.clip(top_player_bpm * 0.8 + 3, 1, 10))
            total_min = float(pd.to_numeric(group["Min"], errors="coerce").sum())
            if total_min > 0 and len(group) > 5:
                bench_min = float(pd.to_numeric(group.iloc[5:]["Min"], errors="coerce").sum())
                bench_pct = bench_min / total_min
            else:
                bench_pct = 0.30
            rows.append({"Team": team_name, "Star_Player_Index": round(star_index, 1), "Bench_Minutes_Pct": round(bench_pct, 3)})
        return pd.DataFrame(rows)
    except Exception as exc:
        print(f"  ⚠ Player metrics fetch failed: {exc}")
        return None


def load_coach_scores(path: str = "data/coach_scores.json") -> dict[str, Any]:
    coach_path = Path(path)
    if coach_path.exists():
        return json.loads(coach_path.read_text(encoding="utf-8"))
    print("  ⚠ coach_scores.json not found; defaulting all coaches to 3")
    return {"_default": 3}


def compute_luck(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Luck = WinPct - Barthag."""
    win_pct = pd.to_numeric(df.get("Wins"), errors="coerce").fillna(20) / pd.to_numeric(df.get("Games"), errors="coerce").fillna(30).clip(lower=1)
    barthag = pd.to_numeric(df.get("Barthag"), errors="coerce").fillna(0.5)
    df["Luck"] = (win_pct - barthag).round(4)
    return df


def merge_all_sources(
    torvik_df: pd.DataFrame,
    massey_df: pd.DataFrame | None,
    ap_poll_df: pd.DataFrame,
    coach_scores: dict[str, Any],
    trank_early_df: pd.DataFrame | None = None,
    net_rank_df: pd.DataFrame | None = None,
    player_metrics_df: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Merge all data sources into final teams_input table."""
    df = torvik_df.copy()
    df = compute_luck(df)
    if net_rank_df is not None:
        df = df.merge(net_rank_df, on="Team", how="left")
    else:
        df["NET_Rank"] = np.nan
    if player_metrics_df is not None:
        df = df.merge(player_metrics_df, on="Team", how="left")
    if massey_df is not None:
        df = df.merge(massey_df, on="Team", how="left")
    else:
        df["Massey_Rank"] = np.nan
    if trank_early_df is not None:
        df = df.merge(trank_early_df, on="Team", how="left")
        df["RankTrajectory"] = df["TRank_Early"] - df["Torvik_Rank"]
    else:
        df["TRank_Early"] = np.nan
        df["RankTrajectory"] = 0
    if not ap_poll_df.empty:
        df = df.merge(ap_poll_df, on="Team", how="left")
        df["AP_Poll_Rank"] = df["AP_Poll_Rank"].fillna(26).astype(int)
    else:
        df["AP_Poll_Rank"] = 26
    rank_cols = [c for c in ["Torvik_Rank", "Massey_Rank", "NET_Rank"] if c in df.columns]
    df["CompRank"] = df[rank_cols].mean(axis=1, skipna=True)
    df["Program_Prestige"] = df["Team"].apply(get_program_prestige)
    default_coach = float(coach_scores.get("_default", 3))
    df["Coach_Tourney_Experience"] = df["Team"].apply(lambda team: float(coach_scores.get(team, default_coach)))
    if "WAB" not in df.columns:
        df["WAB"] = np.nan
    for col in ["Seed", "Quad1_Wins", "Last_10_Games_Metric", "Elite_SOS", "Conf_Strength_Weight", "Conf_Tourney_Champion", "Won_Play_In"]:
        if col not in df.columns:
            df[col] = np.nan
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="March Mathness data fetcher")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--tournament-only", action="store_true")
    args = parser.parse_args()

    print(f"\nFetching data for {args.year}...")
    print("=" * 60)
    torvik = fetch_torvik_main(args.year)
    massey = fetch_massey()
    ap_poll = fetch_ap_poll()
    trank_early = fetch_torvik_early_snapshot(args.year)
    net_rank = fetch_espn_net_rank()
    player_metrics = compute_player_metrics(args.year)
    coach_scores = load_coach_scores()

    merged = merge_all_sources(
        torvik,
        massey,
        ap_poll,
        coach_scores,
        trank_early_df=trank_early,
        net_rank_df=net_rank,
        player_metrics_df=player_metrics
    )

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_year = data_dir / f"teams_input_{args.year}.csv"
    out_main = data_dir / "teams_input.csv"
    merged.to_csv(out_year, index=False)
    merged.to_csv(out_main, index=False)

    if args.tournament_only:
        tournament_df = merged[merged["Seed"].notna()].copy()
        tournament_df.to_csv(data_dir / "tournament_teams_input.csv", index=False)

    print(f"✓ Saved {len(merged)} teams to {out_year}")
    print(f"✓ Saved canonical copy to {out_main}")
    print("\nNext steps:")
    print("  1) Fill seeds and Last_10_Games_Metric after Selection Sunday")
    print("  2) Update coach scores JSON")
    print("  3) Apply injury overrides in data/overrides.json")
    print("  4) Run: python main.py --mode full")


if __name__ == "__main__":
    main()

