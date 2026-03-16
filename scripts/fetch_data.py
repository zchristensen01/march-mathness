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
    """Fetch Torvik season team CSV (requires cloudscraper).

    The CSV endpoint uses lowercase/abbreviated column names that differ
    from our canonical schema — this mapping was verified against the
    actual 2026 endpoint response.  Four-factor stats (eFG%, TO%, etc.)
    are NOT in the CSV; they come from fetch_torvik_factors().
    """
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_team_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))

    rename_map: dict[str, str] = {
        "rank": "Torvik_Rank",
        "team": "Team",
        "conf": "Conference",
        "record": "Record",
        "adjoe": "AdjO",
        "adjde": "AdjD",
        "barthag": "Barthag",
        "adjt": "Adj_T",
        "elite SOS": "Elite_SOS",
    }
    if "WAB" in df.columns:
        pass  # already canonical
    elif "wAB" in df.columns:
        rename_map["wAB"] = "WAB"

    df = df.rename(columns=rename_map)
    df["Team"] = df["Team"].apply(normalize_team_name)

    for col in ("AdjO", "AdjD", "Barthag", "Adj_T"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["AdjEM"] = df["AdjO"] - df["AdjD"]

    if "Record" in df.columns:
        rec_split = df["Record"].astype(str).str.split("-", expand=True)
        df["Wins"] = pd.to_numeric(rec_split[0], errors="coerce")
        df["Games"] = df["Wins"] + pd.to_numeric(rec_split[1], errors="coerce")

    # Convert SOS from Barthag-scale rating (0-1, higher=harder) to rank
    if "sos" in df.columns:
        sos_rating = pd.to_numeric(df["sos"], errors="coerce")
        df["SOS"] = sos_rating.rank(ascending=False, method="min").astype(int)
    elif "SOS" not in df.columns:
        df["SOS"] = np.nan

    return df


# Verified against Duke/Alabama/Gonzaga/UCSB in the 2026 teamslice response
_TEAMSLICE_FOUR_FACTORS = {
    7: "eFG%",
    8: "Opp_eFG%",
    9: "FTR",
    10: "Opp_FTR",
    11: "TO%",
    12: "Opp_TO%",
    13: "OR%",
    14: "Opp_OR%",
    15: "FT%",
    16: "2P%",
    17: "2P_%_D",
    18: "3P%",
    19: "3P_%_D",
    20: "Blk_%",
    21: "Blked_%",
    22: "Ast_%",
    23: "Op_Ast_%",
    24: "3P_Rate",
    25: "3P_Rate_D",
}


def fetch_torvik_factors(year: int, max_retries: int = 3) -> pd.DataFrame | None:
    """Fetch four-factor + shooting stats from the Torvik teamslice JSON.

    The teamslice endpoint returns arrays (no column headers).  Positional
    mapping was determined empirically by cross-referencing Duke, Alabama,
    Gonzaga, and UC Santa Barbara values against known stat ranges.

    Torvik rate-limits rapid requests, so we retry with exponential backoff.
    """
    import time

    try:
        scraper = cloudscraper.create_scraper()
        url = f"http://barttorvik.com/teamslicejson.php?year={year}&json=1&type=R"

        data: list | None = None
        for attempt in range(max_retries):
            if attempt > 0:
                wait = 3 * (2 ** (attempt - 1))
                print(f"    retry {attempt}/{max_retries-1} in {wait}s...")
                time.sleep(wait)

            response = scraper.get(url, timeout=30)
            response.raise_for_status()

            if "<html>" in response.text[:500].lower() or "Verifying" in response.text[:500]:
                print("  ⚠ Torvik factors: Cloudflare blocked")
                continue

            parsed = response.json()
            if isinstance(parsed, list) and len(parsed) > 50:
                data = parsed
                break

        if not data:
            print("  ⚠ Torvik factors: empty/blocked after retries (four factors will be missing)")
            return None

        rows: list[dict[str, Any]] = []
        for entry in data:
            if not isinstance(entry, list) or len(entry) < 15:
                continue
            row: dict[str, Any] = {"Team": normalize_team_name(str(entry[0]))}
            for idx, col_name in _TEAMSLICE_FOUR_FACTORS.items():
                if idx < len(entry):
                    row[col_name] = entry[idx]
            rows.append(row)

        if not rows:
            print("  ⚠ Torvik factors: parsed 0 teams from response")
            return None

        df = pd.DataFrame(rows)
        for col in df.columns:
            if col != "Team":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "Opp_OR%" in df.columns:
            df["DR%"] = (100.0 - df["Opp_OR%"]).clip(lower=0, upper=100)

        print(f"  ✓ Torvik factors: {len(df)} teams, {len(df.columns)-1} stats")
        return df
    except Exception as exc:
        print(f"  ⚠ Torvik factors fetch failed: {exc}")
        return None


def fetch_massey() -> pd.DataFrame | None:
    """Fetch Massey ratings table (requires cloudscraper).

    Massey's page is JS-rendered so pd.read_html often finds no usable
    table.  This is best-effort; Massey_Rank defaults to 150 when missing.
    """
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.masseyratings.com/cb/ncaa-d1/ratings"
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), header=0)
        if not tables:
            print("  ⚠ Massey: no tables found in response (JS-rendered page)")
            return None
        df = tables[0]
        if len(df) < 50:
            print(f"  ⚠ Massey: table has only {len(df)} rows (expected ~360)")
            return None
        df.columns = [str(c).strip() for c in df.columns]
        df["Team"] = df.iloc[:, 1].apply(normalize_team_name)
        df["Massey_Rank"] = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        result = df[["Team", "Massey_Rank"]].dropna()
        print(f"  ✓ Massey: {len(result)} teams")
        return result
    except Exception as exc:
        print(f"  ⚠ Massey fetch failed: {exc} (will use default rank=150)")
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
                    team_obj = entry.get("team", {})
                    name = team_obj.get("displayName") or team_obj.get("location", "")
                    if name:
                        rows.append(
                            {
                                "Team": normalize_team_name(name),
                                "AP_Poll_Rank": int(entry["current"]),
                            }
                        )
        if rows:
            print(f"  ✓ AP poll: {len(rows)} ranked teams")
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Team", "AP_Poll_Rank"])
    except Exception as exc:
        print(f"  ⚠ AP poll fetch failed: {exc}")
        return pd.DataFrame(columns=["Team", "AP_Poll_Rank"])


def fetch_torvik_early_snapshot(year: int) -> pd.DataFrame | None:
    """Fetch Torvik time-machine early rank snapshot.

    The endpoint returns a JSON array-of-arrays (same layout as the CSV:
    position 0 = rank, position 1 = team name).  Despite the .json.gz
    extension, the response is uncompressed JSON.
    """
    try:
        snapshot_date = date(year, 2, 15).strftime("%Y%m%d")
        scraper = cloudscraper.create_scraper()

        for ext in ("json.gz", "json"):
            url = f"http://barttorvik.com/timemachine/team_results/{snapshot_date}_team_results.{ext}"
            response = scraper.get(url, timeout=30)
            if response.status_code != 200:
                continue

            raw = response.content
            # Try gzip first; fall back to plain JSON
            try:
                import gzip
                raw = gzip.decompress(raw)
            except Exception:
                pass

            payload = json.loads(raw)
            if not payload or not isinstance(payload, list):
                continue

            # Array-of-arrays: [rank, team, conf, record, ...]
            if isinstance(payload[0], list):
                rows = [
                    {"Team": normalize_team_name(str(row[1])), "TRank_Early": int(row[0])}
                    for row in payload
                    if len(row) >= 2
                ]
            else:
                # Dict-based fallback
                df = pd.DataFrame(payload)
                df["Team"] = df["Team"].apply(normalize_team_name)
                df = df.rename(columns={"Rank": "TRank_Early"})
                return df[["Team", "TRank_Early"]]

            if rows:
                print(f"  ✓ Early snapshot: {len(rows)} teams from {snapshot_date}")
                return pd.DataFrame(rows)

        print("  ⚠ Torvik early snapshot: no valid response from any URL")
        return None
    except Exception as exc:
        print(f"  ⚠ Torvik early snapshot unavailable: {exc}")
        return None


def fetch_espn_net_rank() -> pd.DataFrame | None:
    """Fetch NET rankings.  ESPN's public teams API no longer embeds NET
    data, so this is a best-effort attempt.  NET_Rank will be populated
    via the Claude Research prompt (prompt 01) if this fails.
    """
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
            if net_rank is not None:
                rows.append({"Team": name, "NET_Rank": int(net_rank)})
        if rows:
            df = pd.DataFrame(rows)
            print(f"  ✓ ESPN NET: {len(df)} teams")
            return df
        print("  ⚠ ESPN NET: endpoint returned no NET data (will use defaults/manual)")
        return None
    except Exception as exc:
        print(f"  ⚠ ESPN NET fetch failed: {exc} (will use defaults/manual)")
        return None


def compute_player_metrics(year: int) -> pd.DataFrame | None:
    """Compute Star_Player_Index and Bench_Minutes_Pct from Torvik player CSV.

    The player CSV endpoint is behind strong Cloudflare protection that
    cloudscraper cannot reliably bypass.  When blocked, player metrics
    default to Star_Player_Index=5.0 and Bench_Minutes_Pct=30.0 and can
    be refined via overrides.json or Claude Research prompt 04.
    """
    try:
        scraper = cloudscraper.create_scraper()
        url = f"http://barttorvik.com/{year}_player_results.csv"
        response = scraper.get(url, timeout=30)
        response.raise_for_status()

        if "<html>" in response.text[:500].lower() or "Verifying" in response.text[:500]:
            print("  ⚠ Player CSV: Cloudflare blocked (use prompt 04 for star player overrides)")
            return None

        players = pd.read_csv(io.StringIO(response.text))
        if "Team" not in players.columns and "team" in players.columns:
            players = players.rename(columns={"team": "Team"})
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
        if rows:
            print(f"  ✓ Player metrics: {len(rows)} teams")
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
    player_metrics_df: pd.DataFrame | None = None,
    factors_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Merge all data sources into final teams_input table."""
    df = torvik_df.copy()

    if factors_df is not None and not factors_df.empty and "Team" in factors_df.columns:
        df = df.merge(factors_df, on="Team", how="left", suffixes=("", "_factor"))
        df = df[[c for c in df.columns if not c.endswith("_factor")]]

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
    # Ensure all prompt-output columns exist as placeholders so the user
    # can paste data into existing columns rather than creating new ones.
    PLACEHOLDER_COLUMNS = [
        "Seed", "NET_Rank", "Quad1_Wins", "Last_10_Games_Metric",
        "Conf_Tourney_Champion", "Won_Play_In",
        "Star_Player_Index", "Bench_Minutes_Pct", "Exp",
        "Elite_SOS", "Conf_Strength_Weight",
    ]
    for col in PLACEHOLDER_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    SCHEMA_COLUMNS = [
        "Team", "Conference", "Record", "Wins", "Games", "Seed",
        "AdjO", "AdjD", "AdjEM", "Barthag", "Adj_T",
        "eFG%", "Opp_eFG%", "TO%", "Opp_TO%", "OR%", "DR%", "Opp_OR%",
        "FTR", "Opp_FTR", "FT%",
        "2P%", "2P_%_D", "3P%", "3P_%_D", "3P_Rate", "3P_Rate_D",
        "Blk_%", "Blked_%", "Ast_%", "Op_Ast_%",
        "SOS", "Elite_SOS", "WAB",
        "Torvik_Rank", "NET_Rank", "Massey_Rank", "CompRank",
        "TRank_Early", "RankTrajectory",
        "AP_Poll_Rank", "Luck",
        "Exp", "Star_Player_Index", "Bench_Minutes_Pct",
        "Coach_Tourney_Experience", "Program_Prestige",
        "Quad1_Wins", "Last_10_Games_Metric",
        "Conf_Strength_Weight", "Conf_Tourney_Champion", "Won_Play_In",
    ]
    keep = [c for c in SCHEMA_COLUMNS if c in df.columns]
    return df[keep]


def main() -> None:
    parser = argparse.ArgumentParser(description="March Mathness data fetcher")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--tournament-only", action="store_true")
    args = parser.parse_args()

    print(f"\nFetching data for {args.year}...")
    print("=" * 60)

    import time

    print("\n[1/7] Torvik core stats (CSV)...")
    torvik = fetch_torvik_main(args.year)
    print(f"  ✓ {len(torvik)} teams from CSV")

    # Brief pause to avoid Torvik rate limiting between endpoints
    time.sleep(2)

    print("[2/7] Torvik four-factor stats (JSON)...")
    factors = fetch_torvik_factors(args.year)

    print("[3/7] Massey ratings...")
    massey = fetch_massey()

    print("[4/7] AP poll...")
    ap_poll = fetch_ap_poll()

    print("[5/7] Torvik early-season snapshot...")
    trank_early = fetch_torvik_early_snapshot(args.year)

    print("[6/7] ESPN NET rankings...")
    net_rank = fetch_espn_net_rank()

    print("[7/7] Player metrics + coach scores...")
    player_metrics = compute_player_metrics(args.year)
    coach_scores = load_coach_scores()

    print("\nMerging all sources...")
    merged = merge_all_sources(
        torvik,
        massey,
        ap_poll,
        coach_scores,
        trank_early_df=trank_early,
        net_rank_df=net_rank,
        player_metrics_df=player_metrics,
        factors_df=factors,
    )

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    out_main = data_dir / "teams_input.csv"
    merged.to_csv(out_main, index=False)

    if args.tournament_only:
        tournament_df = merged[merged["Seed"].notna()].copy()
        tournament_df.to_csv(data_dir / "tournament_teams_input.csv", index=False)

    print(f"\n{'=' * 60}")
    print(f"✓ Saved {len(merged)} teams to {out_main}")

    # Data quality summary
    required = ["Team", "AdjO", "AdjD", "Barthag", "eFG%", "Opp_eFG%",
                 "TO%", "Opp_TO%", "OR%", "SOS", "Adj_T"]
    present = [c for c in required if c in merged.columns]
    missing_req = [c for c in required if c not in merged.columns]
    print(f"\nRequired columns: {len(present)}/{len(required)} present")
    if missing_req:
        print(f"  ✗ MISSING: {missing_req}")

    key_cols = ["Team", "AdjO", "AdjD", "Barthag", "eFG%", "Opp_eFG%",
                "TO%", "Opp_TO%", "OR%", "SOS", "Adj_T", "Conference",
                "NET_Rank", "Massey_Rank", "Star_Player_Index", "WAB"]
    print("\nNull coverage for key columns:")
    for col in key_cols:
        if col in merged.columns:
            non_null = merged[col].notna().sum()
            total = len(merged)
            pct = non_null / total * 100
            status = "✓" if pct > 90 else "⚠" if pct > 50 else "✗"
            print(f"  {status} {col}: {non_null}/{total} ({pct:.0f}%)")

    print("\nNext steps:")
    print("  1) Fill seeds and Last_10_Games_Metric after Selection Sunday")
    print("  2) Update coach scores in data/coach_scores.json")
    print("  3) Apply injury overrides in data/overrides.json")
    print("  4) Run: python main.py --mode full")


if __name__ == "__main__":
    main()

