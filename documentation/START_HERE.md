# March Mathness - Start Here (Operational Runbook)

This is the fastest path from zero setup to tournament outputs.

If you only read one doc before Selection Sunday, read this one.

---

## 1) Before You Run Anything

From repo root, make sure you have:

- Python 3.11+
- Virtual environment created and activated
- Dependencies installed

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

No API keys are required.

---

## 2) First Command To Run

Run this before the bracket is announced:

```bash
python scripts/fetch_data.py --year 2026
```

### What this command does

It builds `data/teams_input.csv` (all D-I teams) by pulling and merging:

- **BartTorvik team data**  
  `http://barttorvik.com/2026_team_results.csv`
- **BartTorvik player data** (for auto star/bench metrics)  
  `http://barttorvik.com/2026_player_results.csv`
- **BartTorvik Time Machine** (early-season rank snapshot)  
  `http://barttorvik.com/timemachine/team_results/20260215_team_results.json.gz`
- **Massey ratings page**  
  `https://www.masseyratings.com/cb/ncaa-d1/ratings`
- **ESPN AP Poll API**  
  `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/rankings`
- **ESPN Teams API** (NET rank)  
  `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams`

### What files are created/updated

- `data/teams_input.csv` (canonical working file)
- `data/teams_input_2026.csv` (year snapshot)

### What is already auto-populated at this stage

- Efficiency/four-factor stats
- `NET_Rank` (if ESPN endpoint succeeds)
- `Star_Player_Index`, `Bench_Minutes_Pct` (if Torvik player endpoint succeeds)
- `CompRank`, `Luck`, `Program_Prestige`, `Coach_Tourney_Experience` defaults/merges

---

## 3) Generate Team Name List For Prompts

Run:

```bash
python -c "import pandas as pd; df = pd.read_csv('data/teams_input.csv'); print('\n'.join(sorted(df['Team'].tolist())))" > data/team_names.txt
```

Then paste `data/team_names.txt` into each prompt in `documentation/prompts/`.

---

## 4) Selection Sunday Workflow (Right After Bracket Release)

Use prompts in this order:

1. `documentation/prompts/01_selection_sunday_stats.txt` (required)
2. `documentation/prompts/02_bracket_structure.txt` (required)
3. `documentation/prompts/03_coach_scores.txt` (recommended)
4. `documentation/prompts/04_star_players.txt` (recommended)
5. `documentation/prompts/05_injury_report.txt` (night before games)
6. `documentation/prompts/06_team_experience.txt` (recommended — can run before Selection Sunday)

### Where to put outputs

- Prompt 01 output -> update columns in `data/teams_input.csv`:
  - `Seed`
  - `NET_Rank`
  - `Quad1_Wins`
  - `Last_10_Games_Metric` (wins in last 10 / 10)
  - `Conf_Tourney_Champion`
- Prompt 02 output -> save as `data/bracket_input.json`
- Prompt 03 output -> save as `data/coach_scores.json`
- Prompt 04 output -> update `Star_Player_Index` overrides in `data/teams_input.csv` for listed teams only
- Prompt 05 output -> save as `data/overrides.json`
- Prompt 06 output -> update `Exp` and `Bench_Minutes_Pct` columns in `data/teams_input.csv`

---

## 5) Run The Full Pipeline

After Selection Sunday files are set:

```bash
python main.py --mode full
```

### What this does

1. Loads `data/teams_input.csv` (+ `data/overrides.json` if present)
2. Normalizes features and computes derived metrics
3. Computes conference strength multipliers
4. Generates ranking tables
5. Loads `data/bracket_input.json`
6. Runs Monte Carlo simulation
7. Generates strategy brackets
8. Writes all output artifacts under `outputs/`

### Key output files

- `outputs/rankings/*_rankings.csv`
- `outputs/simulation_results.json`
- `outputs/bracket_summary.json`
- `outputs/brackets/bracket_<strategy>.json`
- `outputs/my_bracket_picks.txt`

Optional UI:

```bash
streamlit run app.py
```

---

## 6) First Four (Play-In) Update

When First Four games finish:

1. In `data/teams_input.csv`, set `Won_Play_In = 1` for each of the 4 winners.
2. In `data/bracket_input.json`, for each winner entry remove:
   - `play_in`
   - `play_in_opponent`

Then rerun:

```bash
python main.py --mode full
```

---

## 7) Mid-Tournament Updates (After Any Completed Games)

Use:

```bash
python main.py --mode update
```

### What update mode does

- Pulls completed games from ESPN scoreboard API
- Pulls box score stats for those games
- If ESPN fails, falls back to `data/tournament_results.json`
- Removes eliminated teams from remaining field
- Applies tournament-performance bonus to survivors
- Re-runs rankings + simulation for the remaining bracket

### ESPN endpoints used in update mode

- Scoreboard:  
  `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`
- Game summary/box score:  
  `https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary`

### If ESPN is blocked/unavailable

Create/update `data/tournament_results.json` with completed games and rerun:

```bash
python main.py --mode update
```

Use `documentation/MID_TOURNAMENT_UPDATES.md` for full fallback JSON schema.

---

## 8) Command Cheat Sheet

```bash
# 0) setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1) pre-bracket fetch
python scripts/fetch_data.py --year 2026

# 2) extract canonical team names for Claude prompts
python -c "import pandas as pd; df = pd.read_csv('data/teams_input.csv'); print('\n'.join(sorted(df['Team'].tolist())))" > data/team_names.txt

# 3) full run after manual Selection Sunday inputs are ready
python main.py --mode full

# 4) in-tournament update run
python main.py --mode update

# 5) rankings only
python main.py --mode rankings

# 6) UI
streamlit run app.py
```

---

## 9) Do You Need `package.json`?

No. This is a Python project, so command workflow should live in Markdown docs and/or a Makefile, not `package.json`.

If you want, a next step is adding a `Makefile` with targets like `make fetch`, `make full`, `make update`, and `make ui`.
