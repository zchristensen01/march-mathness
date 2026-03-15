# March Mathness — Data Sources & API Guide
**Version 3.1** — All data is free ($0/year). No paid subscriptions. Torvik and Massey require `cloudscraper` (not plain `requests`) due to Cloudflare protection. ESPN API works from normal computers but not CI/sandbox environments. Luck metric computed from Torvik data via `WinPct − Barthag`.

This document specifies every data source, how to access it, what it provides, and how to assemble `teams_input.csv` from scratch. All sources are free ($0/year).

---

## ⚠️ API Reliability Summary (verified by live testing March 2026)

| Source | Method | Status | Notes |
|--------|--------|--------|-------|
| BartTorvik CSV/JSON | `cloudscraper` | ✅ Works | `requests.get()` returns 403 — Cloudflare blocks it. Use cloudscraper. |
| Luck metric | Computed | ✅ Always available | `WinPct − Barthag` — computed from Torvik data, no external dependency |
| ESPN Rankings API | HTTP | ✅ Works (real computer) | Blocked in CI/sandbox environments. Add try/except fallback to every call |
| ESPN Scoreboard API | HTTP | ✅ Works (real computer) | Same — add fallback to manual `tournament_results.json` |
| Massey Ratings | `cloudscraper` | ✅ Works | Same Cloudflare issue as Torvik — use cloudscraper |
| Kaggle MMLM | Manual download | ✅ Static | Download once, save to `data/historical/` |

**Bottom line:** Add `cloudscraper` to `requirements.txt`. Wrap every ESPN call in `try/except`. No paid subscriptions required.

---

## 1. Primary Source: BartTorvik (barttorvik.com)

**Cost:** Free  
**Auth:** None required  
**Coverage:** 2008–present, all D-I teams  
**Format:** CSV and JSON via direct URL

BartTorvik is the primary data source. It provides all efficiency metrics, four factors, SOS, tempo, height, experience, and player-level data at no cost, with direct CSV/JSON export endpoints that do not require scraping.

### 1.1 Core Team Stats Endpoint

**⚠️ Must use `cloudscraper` — plain `requests.get()` returns 403 Forbidden (Cloudflare protection).**

```python
import cloudscraper
import pandas as pd
import io

def fetch_torvik_season(year: int = 2026) -> pd.DataFrame:
    """
    Fetches all D-I team stats for the given season.
    Uses cloudscraper to bypass Cloudflare TLS fingerprinting.
    Plain requests.get() will return 403 — do not use it here.
    """
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_team_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))

# Alternative: manual download
# If cloudscraper ever breaks, visit barttorvik.com in your browser,
# navigate to the team stats page, and download the CSV manually.
# Save to data/teams_input_manual.csv and skip fetch_data.py.
# This is a completely valid approach since you only need it once per year.
```

### 1.2 Four Factors Endpoint (Richer Data)

```python
def fetch_torvik_factors(year: int = 2026, game_type: str = "R") -> pd.DataFrame:
    """
    game_type: "R" = regular season, "C" = conference only, "N" = non-conference
    Also requires cloudscraper.
    """
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/teamslicejson.php?year={year}&json=1&type={game_type}"
    data = scraper.get(url, timeout=30).json()
    return pd.DataFrame(data)
```

### 1.3 Player-Level Data (for Star_Player_Index and Bench_Minutes_Pct)

**Also requires `cloudscraper` — same Cloudflare issue as team data.**

```python
def fetch_torvik_players(year: int = 2026) -> pd.DataFrame:
    """
    Player stats by team. Use to compute Star_Player_Index and Bench_Minutes_Pct.
    Plain requests.get() returns 403 — must use cloudscraper.
    
    Key columns returned: Team, Player, Min, BPM, OBPM, DBPM, Usage, ...
    Use minutes share to determine bench depth:
      bench_pct = sum(minutes for players ranked 6+ on depth chart) / total_team_minutes
    Use BPM/OBPM of top player as proxy for Star_Player_Index calibration.
    """
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_player_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))
```

### 1.4 Historical Archives & Time Machine (for backtest + ranking trajectory)

```python
def fetch_torvik_historical(year: int) -> pd.DataFrame:
    """Available from 2008-09 season onward."""
    url = f"http://barttorvik.com/{year}_team_results.csv"
    return pd.read_csv(url)

# Point-in-time ratings (prevents data leakage in training):
# http://barttorvik.com/timemachine/team_results/{YYYYMMDD}_team_results.json.gz
# Example: http://barttorvik.com/timemachine/team_results/20240317_team_results.json.gz


def fetch_torvik_early_snapshot(year: int, weeks_before: int = 4) -> pd.DataFrame:
    """
    Fetches a point-in-time Torvik T-Rank snapshot from ~4 weeks before
    Selection Sunday. Used to compute RankTrajectory = TRank_Early − Torvik_Rank
    (positive = team improved heading into tournament).
    
    Requires cloudscraper. Date is estimated as Feb 15 for most years.
    """
    from datetime import date, timedelta
    # Selection Sunday is typically mid-March; snapshot ~4 weeks earlier
    snapshot_date = date(year, 2, 15).strftime('%Y%m%d')
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/timemachine/team_results/{snapshot_date}_team_results.json.gz"
    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        import gzip, json
        data = json.loads(gzip.decompress(response.content))
        df = pd.DataFrame(data)
        df['Team'] = df['Team'].apply(normalize_team_name)
        df = df.rename(columns={'Rank': 'TRank_Early'})
        print(f"  ✓ Torvik Time Machine: {len(df)} teams from {snapshot_date}")
        return df[['Team', 'TRank_Early']]
    except Exception as e:
        print(f"  ⚠ Torvik Time Machine snapshot failed: {e}")
        print(f"    RankTrajectory / NETMomentum will default to 0 (neutral).")
        return None
```

### 1.5 Column Mapping: Torvik → teams_input.csv

| Torvik Column | teams_input.csv Column | Notes |
|---------------|----------------------|-------|
| `Team` | `Team` | May need name normalization |
| `Conf` | `Conference` | |
| `Rec` | `Record` | |
| `AdjOE` | `AdjO` | |
| `AdjDE` | `AdjD` | |
| `Barthag` | `Barthag` | |
| `EFG%` | `eFG%` | |
| `EFGD%` | `Opp_eFG%` | |
| `TOR` | `TO%` | Turnover rate |
| `TORD` | `Opp_TO%` | |
| `ORB` | `OR%` | Offensive rebound % |
| `DRB` | `DR%` | Defensive rebound % |
| `FTR` | `FTR` | |
| `FTRD` | `Opp_FTR` | |
| `FT%` | `FT%` | Free throw percentage |
| `SOS` | `SOS` | Strength of schedule rank (1 = hardest) |
| `A/TO` | `AST_TO` | Assist-to-turnover ratio |
| `AST%` | `Ast_%` | Assisted field goal percentage |
| `AST%D` | `Op_Ast_%` | Opponent assisted FG% |
| `2P%` | `2P%` | |
| `2P%D` | `2P_%_D` | |
| `3P%` | `3P%` | |
| `3P%D` | `3P_%_D` | |
| `3PR` | `3P_Rate` | 3-point attempt rate |
| `3PRD` | `3P_Rate_D` | |
| `Blk%` | `Blk_%` | |
| `Blk%D` | `Blked_%` | |
| `Tempo` | `Adj_T` | |
| `Raw Tempo` | `Raw_T` | |
| `Avg Hgt` | `Avg_Hgt` | |
| `Eff Hgt` | `Eff_Hgt` | |
| `Experience` | `Exp` | |
| `PPP Off` | `PPP_Off` | |
| `PPP Def` | `PPP_Def` | |
| `WAB` | `WAB` | Wins Above Bubble — already in Torvik CSV |
| `wAB` | `WAB` | Alternate column name in some years |
| `Rank` | `Torvik_Rank` | T-Rank |

---

## 2. Luck Metric (Computed — No External Dependency)

The Luck metric measures the gap between a team's actual win% and their efficiency-predicted win%. High positive Luck = winning more games than efficiency deserves = regression candidate = fraud signal. This feeds the Fraud Score algorithm (Section 10 of `ALGORITHM.md`) at 15% weight. Year-to-year correlation is just 0.06, so it serves as a penalty modifier rather than a primary predictor.

Luck = `actual_win% − pythagorean_expected_win%`. Torvik's Barthag IS the Pythagorean win expectancy, so `WinPct − Barthag` produces this directly — no external dependency.

```python
def compute_luck(df: pd.DataFrame) -> pd.DataFrame:
    """
    Luck = WinPct - Barthag
    
    Torvik's Barthag IS the Pythagorean win expectancy (0-1 scale).
    Positive = team winning more games than efficiency deserves (fraud signal).
    Negative = losing more close games than expected (underseeded).
    
    Always computed from Torvik data — no external dependency.
    """
    win_pct = df['Wins'].fillna(20) / df['Games'].fillna(30).clip(lower=1)
    barthag = df['Barthag'].fillna(0.5)
    df['Luck'] = (win_pct - barthag).round(4)
    print(f"  ✓ Luck computed for {len(df)} teams (WinPct − Barthag)")
    return df
```

---

## 3. ESPN APIs (Free, No Auth)

### 3.1 BPI and NET Rankings

```python
def fetch_espn_bpi(year: int = 2026) -> pd.DataFrame:
    """Fetches ESPN BPI rankings. No auth required."""
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
    params = {"limit": 400, "groups": 50, "enable": "standings"}
    response = requests.get(url, params=params)
    data = response.json()
    teams = []
    for team in data.get('teams', []):
        teams.append({
            'Team': normalize_team_name(team['displayName']),
            'BPI': team.get('statistics', {}).get('bpi', None),
            'NET_Rank': team.get('statistics', {}).get('netRanking', None),
        })
    return pd.DataFrame(teams)
```

### 3.2 AP Poll Rankings (NEW — added in v2)

Fetched automatically by `fetch_data.py`. Unranked teams receive `AP_Poll_Rank = 26`.
Research basis: FiveThirtyEight weighted human rankings at 25% of their model because polls capture recruiting depth and program talent that pure efficiency stats miss. In the last 10 years, only UConn won a championship while ranked outside the Coaches Poll top 6.

```python
def fetch_ap_poll_rankings() -> pd.DataFrame:
    """
    Fetches current AP Top 25 rankings from ESPN.
    Unranked teams receive AP_Poll_Rank = 26.
    No auth required.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        rankings = []
        for poll in data.get('rankings', []):
            if 'AP' in poll.get('name', ''):
                for entry in poll.get('ranks', []):
                    rankings.append({
                        'Team': normalize_team_name(entry['team']['displayName']),
                        'AP_Poll_Rank': int(entry['current'])
                    })
        df = pd.DataFrame(rankings)
        print(f"  ✓ AP Poll: fetched {len(df)} ranked teams")
        return df
    except Exception as e:
        print(f"  ⚠ AP Poll fetch failed: {e} — all teams receive rank 26")
        return pd.DataFrame(columns=['Team', 'AP_Poll_Rank'])
```

---

## 4. Massey Ratings (Free)

**Cost:** Free  
**Auth:** None  
**URL:** https://www.masseyratings.com/cb/ncaa-d1/ratings

```python
def fetch_massey_ratings() -> pd.DataFrame:
    """Parses Massey's composite ratings page (aggregates 50+ computer systems)."""
    url = "https://www.masseyratings.com/cb/ncaa-d1/ratings"
    try:
        tables = pd.read_html(url)
        df = tables[0]
        df.columns = [str(c).strip() for c in df.columns]
        df['Team'] = df.iloc[:, 1].apply(normalize_team_name)
        df['Massey_Rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        return df[['Team', 'Massey_Rank']].dropna()
    except Exception as e:
        print(f"  ⚠ Massey fetch failed: {e}")
        return None
```

---

## 5. Kaggle MMLM Dataset (Historical Tournament Results)

**Cost:** Free (requires Kaggle account)  
**URL:** https://www.kaggle.com/competitions/march-machine-learning-mania-2024/data  
**Use:** Historical tournament game-by-game results for backtest calibration

Key files:

| File | Use |
|------|-----|
| `MTeams.csv` | Team ID → team name mapping |
| `MNCAATourneySeeds.csv` | Seed assignments per year |
| `MNCAATourneyCompactResults.csv` | Game outcomes (winner, loser, score) |
| `MNCAATourneyDetailedResults.csv` | Full box scores for tournament games |
| `MRegularSeasonDetailedResults.csv` | Full box scores for regular season |

---

## 6. Program Prestige Lookup Table (NEW — added in v2)

This is a static lookup in `engine/scoring.py` (or `models/program_prestige.json`). Auto-applied by `fetch_data.py` — no manual action required. Update once per year if a program rises/falls significantly.

**Research basis:** Jake Allen's ML model (Medium) found prior program tournament wins among the most important features for predicting champions. Blue blood programs have recruiting pipelines, facilities, and institutional knowledge that partially persist even in down years.

```python
PROGRAM_PRESTIGE = {
    # Blue bloods (8-10): consistent recruiting, deep tournament history
    "Kansas": 10, "Kentucky": 10, "Duke": 10, "North Carolina": 9,
    "Connecticut": 9, "Gonzaga": 8, "Michigan State": 8, "Arizona": 8,
    "UCLA": 8, "Villanova": 8,

    # Established programs (5-7): solid history, occasional deep runs
    "Houston": 7, "Tennessee": 7, "Auburn": 7, "Creighton": 6,
    "Baylor": 7, "Arkansas": 6, "Florida": 7, "Virginia": 7,
    "Indiana": 6, "Ohio State": 6, "Purdue": 6, "Texas": 6,
    "Illinois": 5, "Wisconsin": 5, "Maryland": 5, "Louisville": 6,
    "Syracuse": 5, "Georgetown": 5, "Marquette": 5,

    # Solid mid-majors with tournament history (3-4)
    "Xavier": 4, "Butler": 4, "Murray State": 4,
    "San Diego State": 5, "Wichita State": 5,
    "St. Mary's": 4, "VCU": 4, "Davidson": 3,
}
PROGRAM_PRESTIGE_DEFAULT = 2  # Default for any unlisted team

def get_program_prestige(team_name: str) -> float:
    return PROGRAM_PRESTIGE.get(team_name, PROGRAM_PRESTIGE_DEFAULT)
```

---

## 7. Coach Scores File (NEW — added in v2)

Manually maintained at `data/coach_scores.json`. Update once per year after the bracket is announced (~15 minutes). See schema in `DATA_SCHEMA.md` Section 4 for the scoring rubric.

**Research basis:** Sports Betting Dime analysis of 2010–2025 champions: 7 of 10 recent champion coaches had 24+ years head coaching experience and 500+ wins. Harvard Cox survival model found coach tournament experience interacted significantly with team strength in predicting tournament advancement.

```python
def load_coach_scores(path: str = 'data/coach_scores.json') -> dict:
    """Loads coach tournament experience scores. Returns default for missing teams."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    print("  ⚠ coach_scores.json not found — all coaches receive default score of 3")
    return {"_default": 3}

def get_coach_score(team_name: str, coach_scores: dict) -> float:
    return float(coach_scores.get(team_name, coach_scores.get('_default', 3)))
```

---

## 8. Team Name Normalization

Different sources use different team name formats. This is a critical data engineering step.

### 8.1 Common mismatches

| Torvik Name | ESPN Name | Canonical |
|-------------|-----------|-----------|
| `UConn` | `Connecticut` | `Connecticut` |
| `UCSB` | `UC Santa Barbara` | `UC Santa Barbara` | `UC Santa Barbara` |
| `LMU (CA)` | `Loyola Marymount` | `Loyola Marymount` | `Loyola Marymount` |
| `TAM C. Christi` | `Texas A&M-CC` | `Texas A&M-Corpus Christi` | `Texas A&M-Corpus Christi` |
| `Col. of Charleston` | `College of Charleston` | `College of Charleston` | `College of Charleston` |

### 8.2 Normalization function

```python
TEAM_NAME_MAP = {
    "UConn": "Connecticut",
    "UCSB": "UC Santa Barbara",
    "LMU (CA)": "Loyola Marymount",
    "TAM C. Christi": "Texas A&M-Corpus Christi",
    "Col. of Charleston": "College of Charleston",
    "SIU Edwardsville": "SIUE",
    "St. Mary's (CA)": "Saint Mary's",
    "FIU": "Florida International",
}

def normalize_team_name(name: str) -> str:
    return TEAM_NAME_MAP.get(str(name).strip(), str(name).strip())
```

---

## 9. Complete Data Fetch Script

Save as `scripts/fetch_data.py`. Run once after Selection Sunday.

**⚠️ Requires `cloudscraper` for Torvik and Massey.** Plain `requests` returns 403 from both. Install with: `pip install cloudscraper`.

```python
"""
scripts/fetch_data.py
Run: python scripts/fetch_data.py --year 2026

Requires: cloudscraper (for Torvik + Massey)
Install:  pip install cloudscraper
"""

import pandas as pd
import numpy as np
import requests
import cloudscraper   # ← REQUIRED for Torvik and Massey (Cloudflare bypass)
import io
import argparse
import json
import os
from dotenv import load_dotenv

load_dotenv()  # loads any environment variables from .env file


# ─────────────────────────────────────────────────────────────────────────────
# TEAM NAME NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

TEAM_NAME_MAP = {
    "UConn": "Connecticut",
    "UCSB": "UC Santa Barbara",
    "LMU (CA)": "Loyola Marymount",
    "TAM C. Christi": "Texas A&M-Corpus Christi",
    "Col. of Charleston": "College of Charleston",
    "SIU Edwardsville": "SIUE",
    "St. Mary's (CA)": "Saint Mary's",
    "FIU": "Florida International",
}

def normalize_team_name(name: str) -> str:
    return TEAM_NAME_MAP.get(str(name).strip(), str(name).strip())


# ─────────────────────────────────────────────────────────────────────────────
# PROGRAM PRESTIGE (auto-applied, no manual work needed)
# ─────────────────────────────────────────────────────────────────────────────

PROGRAM_PRESTIGE = {
    "Kansas": 10, "Kentucky": 10, "Duke": 10, "North Carolina": 9,
    "Connecticut": 9, "Gonzaga": 8, "Michigan State": 8, "Arizona": 8,
    "UCLA": 8, "Villanova": 8,
    "Houston": 7, "Tennessee": 7, "Auburn": 7, "Creighton": 6,
    "Baylor": 7, "Arkansas": 6, "Florida": 7, "Virginia": 7,
    "Indiana": 6, "Ohio State": 6, "Purdue": 6, "Texas": 6,
    "Illinois": 5, "Wisconsin": 5, "Maryland": 5, "Louisville": 6,
    "Syracuse": 5, "Georgetown": 5, "Marquette": 5,
    "Xavier": 4, "Butler": 4, "Murray State": 4,
    "San Diego State": 5, "Wichita State": 5,
    "St. Mary's": 4, "VCU": 4, "Davidson": 3,
}

def get_program_prestige(team_name: str) -> float:
    return float(PROGRAM_PRESTIGE.get(team_name, 2))


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHERS (note: cloudscraper used for Cloudflare-protected sites)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_torvik_main(year: int) -> pd.DataFrame:
    """Uses cloudscraper — plain requests.get() returns 403 Forbidden."""
    print(f"  Fetching Torvik main stats for {year}...")
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_team_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    df = df.rename(columns={
        'AdjOE': 'AdjO', 'AdjDE': 'AdjD', 'EFG%': 'eFG%',
        'EFGD%': 'Opp_eFG%', 'TOR': 'TO%', 'TORD': 'Opp_TO%',
        'ORB': 'OR%', 'DRB': 'DR%', 'FTRD': 'Opp_FTR',
        '2P%D': '2P_%_D', '3P%D': '3P_%_D', '3PR': '3P_Rate',
        '3PRD': '3P_Rate_D', 'Blk%': 'Blk_%', 'Blk%D': 'Blked_%',
        'Tempo': 'Adj_T', 'Raw Tempo': 'Raw_T',
        'Avg Hgt': 'Avg_Hgt', 'Eff Hgt': 'Eff_Hgt',
        'Experience': 'Exp', 'PPP Off': 'PPP_Off', 'PPP Def': 'PPP_Def',
        'Rank': 'Torvik_Rank', 'Conf': 'Conference', 'Rec': 'Record',
        'wAB': 'WAB',  # handle alternate column name
    })
    df['AdjEM'] = df['AdjO'] - df['AdjD']
    df['Team'] = df['Team'].apply(normalize_team_name)

    # Parse Wins and Games from Record column (e.g., "28-5")
    if 'Record' in df.columns:
        record_parts = df['Record'].str.split('-', expand=True)
        df['Wins'] = pd.to_numeric(record_parts[0], errors='coerce')
        df['Games'] = df['Wins'] + pd.to_numeric(record_parts[1], errors='coerce')

    print(f"  ✓ Torvik: {len(df)} teams loaded")
    return df


def fetch_espn_net_rank() -> pd.DataFrame | None:
    """
    Fetches NET rankings via ESPN API. No auth required.
    ⚠ ESPN API is blocked in CI/sandbox environments but works from real computers.
    Falls back gracefully — NET_Rank will be NaN and CompRank uses remaining ranks.
    """
    print("  Fetching ESPN NET rankings...")
    try:
        import requests
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams"
        params = {"limit": 400, "groups": 50, "enable": "standings"}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        teams = []
        for team in data.get('teams', []):
            net_rank = None
            for stat in team.get('statistics', []):
                if 'netRanking' in str(stat):
                    net_rank = stat.get('netRanking')
                    break
            if net_rank is None and 'record' in team:
                for item in team.get('record', {}).get('items', []):
                    for s in item.get('stats', []):
                        if s.get('name') == 'netRanking':
                            net_rank = int(s.get('value', 0))
            teams.append({
                'Team': normalize_team_name(team.get('displayName', '')),
                'NET_Rank': net_rank,
            })
        df = pd.DataFrame(teams).dropna(subset=['NET_Rank'])
        df['NET_Rank'] = df['NET_Rank'].astype(int)
        print(f"  ✓ ESPN NET: {len(df)} teams loaded")
        return df
    except Exception as e:
        print(f"  ⚠ ESPN NET fetch failed: {e}")
        print(f"    NET_Rank will be NaN — CompRank uses Torvik + Massey instead.")
        return None


def compute_player_metrics(year: int = 2026) -> pd.DataFrame | None:
    """
    Fetches Torvik player data and computes per-team aggregates:
    - Star_Player_Index: best player BPM normalized to 1-10 scale
    - Bench_Minutes_Pct: fraction of minutes played by non-starters
    
    Automates two columns that were previously manual-only.
    """
    print("  Fetching Torvik player data...")
    try:
        scraper = cloudscraper.create_scraper()
        url = f"http://barttorvik.com/{year}_player_results.csv"
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        players = pd.read_csv(io.StringIO(response.text))
        players['Team'] = players['Team'].apply(normalize_team_name)

        results = []
        for team_name, group in players.groupby('Team'):
            group = group.sort_values('Min', ascending=False)
            top_player_bpm = group.iloc[0]['BPM'] if 'BPM' in group.columns else 0
            star_index = np.clip(top_player_bpm * 0.8 + 3, 1, 10).round(1)

            total_min = group['Min'].sum()
            if total_min > 0 and len(group) > 5:
                bench_min = group.iloc[5:]['Min'].sum()
                bench_pct = round(bench_min / total_min, 3)
            else:
                bench_pct = 0.30  # default

            results.append({
                'Team': team_name,
                'Star_Player_Index': star_index,
                'Bench_Minutes_Pct': bench_pct,
            })

        df = pd.DataFrame(results)
        print(f"  ✓ Player metrics: {len(df)} teams (Star_Player_Index + Bench_Minutes_Pct)")
        return df
    except Exception as e:
        print(f"  ⚠ Player data fetch failed: {e}")
        print(f"    Star_Player_Index and Bench_Minutes_Pct will need manual entry.")
        return None


def fetch_massey() -> pd.DataFrame | None:
    """Uses cloudscraper — plain requests returns 403."""
    print("  Fetching Massey ratings...")
    try:
        scraper = cloudscraper.create_scraper()
        url = "https://www.masseyratings.com/cb/ncaa-d1/ratings"
        response = scraper.get(url, timeout=30)
        tables = pd.read_html(io.StringIO(response.text), header=0)
        df = tables[0]
        df.columns = [str(c).strip() for c in df.columns]
        df['Team'] = df.iloc[:, 1].apply(normalize_team_name)
        df['Massey_Rank'] = pd.to_numeric(df.iloc[:, 0], errors='coerce')
        result = df[['Team', 'Massey_Rank']].dropna()
        print(f"  ✓ Massey: {len(result)} teams loaded")
        return result
    except Exception as e:
        print(f"  ⚠ Massey fetch failed: {e}")
        return None


def fetch_ap_poll() -> pd.DataFrame:
    """
    Fetches AP Top 25. Uses plain requests (ESPN doesn't need cloudscraper).
    ⚠ ESPN API is blocked in CI/sandbox environments but works from real computers.
    Add browser-like headers to improve success rate.
    """
    print("  Fetching AP Poll rankings...")
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        data = requests.get(url, headers=headers, timeout=10).json()
        rankings = []
        for poll in data.get('rankings', []):
            if 'AP' in poll.get('name', ''):
                for entry in poll.get('ranks', []):
                    rankings.append({
                        'Team': normalize_team_name(entry['team']['displayName']),
                        'AP_Poll_Rank': int(entry['current'])
                    })
        df = pd.DataFrame(rankings)
        print(f"  ✓ AP Poll: {len(df)} ranked teams")
        return df
    except Exception as e:
        print(f"  ⚠ AP Poll fetch failed: {e} — all teams receive rank 26")
        return pd.DataFrame(columns=['Team', 'AP_Poll_Rank'])


def load_coach_scores(path: str = 'data/coach_scores.json') -> dict:
    if os.path.exists(path):
        with open(path) as f:
            scores = json.load(f)
        print(f"  ✓ Coach scores: loaded {len(scores)-1} entries from {path}")
        return scores
    print(f"  ⚠ {path} not found — all coaches receive default score of 3")
    return {"_default": 3}


# ─────────────────────────────────────────────────────────────────────────────
# MERGE
# ─────────────────────────────────────────────────────────────────────────────

def merge_all_sources(torvik_df, massey_df,
                      ap_poll_df, coach_scores,
                      trank_early_df=None,
                      net_rank_df=None,
                      player_metrics_df=None) -> pd.DataFrame:
    df = torvik_df.copy()

    # Compute Luck from Torvik data (WinPct − Barthag)
    df = compute_luck(df)

    # NET rank merge (ESPN)
    if net_rank_df is not None:
        df = df.merge(net_rank_df, on='Team', how='left')
    else:
        df['NET_Rank'] = np.nan

    # Player-derived metrics merge (Star_Player_Index, Bench_Minutes_Pct)
    if player_metrics_df is not None:
        df = df.merge(player_metrics_df, on='Team', how='left')

    # Massey merge
    if massey_df is not None:
        df = df.merge(massey_df, on='Team', how='left')
    else:
        df['Massey_Rank'] = np.nan

    # T-Rank early snapshot merge (for ranking trajectory / NETMomentum)
    if trank_early_df is not None:
        df = df.merge(trank_early_df, on='Team', how='left')
        df['RankTrajectory'] = df['TRank_Early'] - df['Torvik_Rank']
    else:
        df['TRank_Early'] = np.nan
        df['RankTrajectory'] = 0  # neutral default

    # AP Poll merge (unranked teams get 26)
    if not ap_poll_df.empty:
        df = df.merge(ap_poll_df, on='Team', how='left')
        df['AP_Poll_Rank'] = df['AP_Poll_Rank'].fillna(26).astype(int)
    else:
        df['AP_Poll_Rank'] = 26

    # Composite rank (average of available ranking systems)
    rank_cols = [c for c in ['Torvik_Rank', 'Massey_Rank', 'NET_Rank']
                 if c in df.columns]
    df['CompRank'] = df[rank_cols].mean(axis=1, skipna=True)

    # Program Prestige (auto-applied from lookup table)
    df['Program_Prestige'] = df['Team'].apply(get_program_prestige)

    # Coach Tournament Experience (from coach_scores.json)
    default_coach = float(coach_scores.get('_default', 3))
    df['Coach_Tourney_Experience'] = df['Team'].apply(
        lambda t: float(coach_scores.get(t, default_coach))
    )

    # WAB: ensure column exists (different Torvik years use different names)
    if 'WAB' not in df.columns:
        df['WAB'] = np.nan

    # Add empty columns for manual data (filled in after bracket announcement)
    for col in ['Seed', 'Quad1_Wins', 'Last_10_Games_Metric',
                'Elite_SOS', 'Conf_Strength_Weight',
                'Conf_Tourney_Champion', 'Won_Play_In']:
        if col not in df.columns:
            df[col] = np.nan

    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="March Mathness data fetcher")
    parser.add_argument('--year', type=int, default=2026)
    parser.add_argument('--tournament-only', action='store_true')
    args = parser.parse_args()

    print(f"\nFetching data for {args.year}...")
    print("=" * 50)

    torvik       = fetch_torvik_main(args.year)
    massey       = fetch_massey()
    ap_poll      = fetch_ap_poll()
    trank_early  = fetch_torvik_early_snapshot(args.year)
    net_rank     = fetch_espn_net_rank()
    player_stats = compute_player_metrics(args.year)
    coach_scores = load_coach_scores()

    print("\nMerging sources...")
    merged = merge_all_sources(
        torvik, massey, ap_poll, coach_scores,
        trank_early, net_rank, player_stats
    )

    os.makedirs('data', exist_ok=True)
    out_path = f'data/teams_input_{args.year}.csv'
    merged.to_csv(out_path, index=False)
    merged.to_csv('data/teams_input.csv', index=False)
    print(f"\n✓ Saved {len(merged)} teams to {out_path}")
    print(f"✓ Saved canonical copy to data/teams_input.csv")

    if args.tournament_only:
        tourney = merged[merged['Seed'].notna()].copy()
        tourney.to_csv('data/tournament_teams_input.csv', index=False)
        print(f"✓ Saved {len(tourney)} tournament teams to data/tournament_teams_input.csv")

    print("\nNext steps:")
    print("  1. Add Seeds to data/teams_input.csv after bracket announcement")
    print("  2. Fill Last_10_Games_Metric (wins in last 10 games ÷ 10)")
    print("  3. Verify Star_Player_Index auto-values; override standouts manually")
    print("  4. Update data/coach_scores.json for this year's coaches")
    print("  5. Set Conf_Tourney_Champion = 1 for conference tournament winners")
    print("  6. Set Won_Play_In = 1 for First Four winners (after Tue/Wed games)")
    print("  7. Check for injuries and update data/overrides.json")
    print("  8. Run: python main.py --mode full")


if __name__ == '__main__':
    main()
```

---

## 10. Manual Data Collection

After running `scripts/fetch_data.py`, some fields require manual collection. Most can be gathered via Claude Research — see `DATA_INPUT_CHECKLIST.md` for exact prompts, formats, and file locations.

**Summary of manual data:**

| Data | File | Method |
|------|------|--------|
| Seeds, Quad1_Wins, Last_10_Games_Metric, Conf_Tourney_Champion | `data/teams_input.csv` | Claude Research → paste into CSV |
| Bracket structure (regions, slots) | `data/bracket_input.json` | Claude Research (prompt 02) → save JSON |
| Coach tournament experience scores | `data/coach_scores.json` | Claude Research → save JSON |
| Star_Player_Index overrides (standouts only) | `data/teams_input.csv` | Claude Research → update specific rows |
| Injury overrides | `data/overrides.json` | Claude Research → save JSON |
| Won_Play_In flag (4 teams) | `data/teams_input.csv` | After First Four games |

Notes:
- `NET_Rank` is auto-fetched from ESPN when available.
- `Star_Player_Index` and `Bench_Minutes_Pct` are auto-computed from Torvik player data when available.
- If those upstream fetches fail, the pipeline uses defaults and you can optionally backfill manually.

**⚠️ Team names in ALL files must match the canonical names in `data/teams_input.csv`.** See team name normalization in Section 8.

### 10.4 Conference name standardization

Use these exact strings in the `Conference` column to match `models/conference_weights.json`:

```
SEC, Big12, ACC, B10, BE, AAC, MWC, WCC, A10, MVC, MAC, CUSA,
SBC, Horizon, CAA, WAC, OVC, SoCon, MAAC, NEC, Patriot, BSky, SWAC,
MEAC, AEC, Summit, Unknown
```

Note: `P12` (Pac-12) is no longer a valid conference code as of 2024–25. Former Pac-12 members are now coded as `B10`, `Big12`, `ACC`, or `WCC` in Torvik data.

---

## 11. Data Quality Validation

Run before the main pipeline to catch problems early:

```python
REQUIRED_COLUMNS = [
    'Team', 'AdjO', 'AdjD', 'Barthag', 'eFG%', 'Opp_eFG%',
    'TO%', 'Opp_TO%', 'OR%', 'SOS', 'Adj_T'
]

def validate_input(df: pd.DataFrame) -> list[str]:
    """Returns list of validation errors. Empty list = data is clean."""
    errors = []

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            errors.append(f"MISSING REQUIRED COLUMN: {col}")

    dupes = df[df.duplicated('Team', keep=False)]['Team'].unique()
    for t in dupes:
        errors.append(f"DUPLICATE TEAM: {t}")

    if 'AdjEM' in df.columns:
        bad = df[(df['AdjEM'] < -25) | (df['AdjEM'] > 50)]
        for _, row in bad.iterrows():
            errors.append(f"AdjEM out of range for {row['Team']}: {row['AdjEM']}")

    if 'Seed' in df.columns:
        bad_seeds = df[df['Seed'].notna() & ~df['Seed'].isin(range(1, 17))]
        for _, row in bad_seeds.iterrows():
            errors.append(f"Invalid seed for {row['Team']}: {row['Seed']}")

    if 'AP_Poll_Rank' in df.columns:
        bad_ap = df[df['AP_Poll_Rank'].notna() & ~df['AP_Poll_Rank'].between(1, 26)]
        for _, row in bad_ap.iterrows():
            errors.append(f"AP_Poll_Rank out of range for {row['Team']}: {row['AP_Poll_Rank']}")

    return errors
```

---

## 12. Cost Summary

| Source | Cost | Provides | Auto-fetched? |
|--------|------|---------|---------------|
| BartTorvik (team) | **$0** | AdjEM, AdjO, AdjD, Barthag, all four factors, SOS, FT%, tempo, height, experience, PPP, WAB, Luck (computed) | ✅ Yes |
| BartTorvik (player) | **$0** | Star_Player_Index, Bench_Minutes_Pct (auto-computed from BPM + minutes) | ✅ Yes |
| BartTorvik (Time Machine) | **$0** | TRank_Early → RankTrajectory / NETMomentum | ✅ Yes |
| Massey Ratings | **$0** | Consensus computer ranking | ✅ Yes |
| ESPN AP Poll | **$0** | AP Poll rank | ✅ Yes |
| ESPN NET | **$0** | NET rank (for CompRank) | ✅ Yes |
| Kaggle MMLM | **$0** | Historical tournament results for backtest/calibration | Manual download (one-time) |
| Program Prestige | **$0** | Blue blood index | ✅ Auto (lookup table) |
| Coach Scores | **$0** | Coach tournament experience | Manual JSON (~15 min/year) |
| **Total** | **$0/year** | Complete data stack | |

**Every data source is free.** No paid subscriptions required. The Luck metric (`WinPct − Barthag`) is computed from Torvik data and uses Torvik data only. CompRank averages Torvik_Rank, Massey_Rank, and NET_Rank.