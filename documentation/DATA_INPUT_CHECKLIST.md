# March Mathness — Data Input Checklist

**Everything you need to collect before running the app.**
Bracket releases tonight (Selection Sunday, March 15 2026). Follow this in order.

---

## Accounts Needed

| Account | Cost | URL | Required? |
|---------|------|-----|-----------|
| **Kaggle** | Free | https://www.kaggle.com | Optional (for calibration) |

No paid subscriptions. Every data source is free.

---

## Team Name Matching

Every team name you enter must match `data/teams_input.csv` exactly. Mismatched names cause silent data loss.

After running `fetch_data.py` in Phase 1, you will extract a team name list. You paste this list into every Claude Research prompt so it uses your exact names.

---

## Phase 1: Automated Data Fetch

**When:** Before the bracket is announced.
**Effort:** Run two commands.

```bash
python scripts/fetch_data.py --year 2026
```

This auto-fetches ~40 columns for all ~365 D-I teams from BartTorvik, ESPN, and Massey:
- All efficiency stats (AdjO, AdjD, AdjEM, Barthag, four factors, tempo, height, etc.)
- Rankings (Torvik_Rank, Massey_Rank, NET_Rank, AP_Poll_Rank, CompRank)
- Player-derived metrics (Star_Player_Index from BPM, Bench_Minutes_Pct from minutes)
- Ranking trajectory (TRank_Early, RankTrajectory)
- Luck metric (WinPct - Barthag, computed automatically)
- Program_Prestige (static lookup)
- Record, Wins, Games (parsed from Torvik)

Then extract your canonical team name list:

```bash
python -c "import pandas as pd; df = pd.read_csv('data/teams_input.csv'); print('\n'.join(sorted(df['Team'].tolist())))" > data/team_names.txt
```

You will paste the contents of `data/team_names.txt` into every prompt in the `documentation/prompts/` folder.

---

## Phase 2: Selection Sunday Data

**When:** After bracket is announced tonight.

### What is already in the CSV from Phase 1 (no action needed)

- NET_Rank (auto-fetched from ESPN)
- All efficiency stats, rankings, player metrics, Luck

### What you need to add

| Data | File to Update | Prompt File |
|------|---------------|-------------|
| Seeds, Quad1 Wins, Last 10 Games, Conf Tourney Champions | `data/teams_input.csv` | `prompts/01_selection_sunday_stats.txt` |
| Bracket structure (regions, matchups, slots) | `data/bracket_input.json` | `prompts/02_bracket_structure.txt` |

Open each prompt file, paste your team name list where indicated, and send the prompt to Claude Research. Follow the instructions in the file for what to do with the output.

**Column details for the CSV updates:**

| Column | Type | What It Is | Example |
|--------|------|-----------|---------|
| Seed | integer 1-16 | Tournament seed | 1 |
| Quad1_Wins | integer 0-15 | Wins vs Quad 1 opponents | 8 |
| Last_10_Games_Metric | float 0.0-1.0 | Wins in last 10 games divided by 10 | 0.80 |
| Conf_Tourney_Champion | 0 or 1 | Won their conference tournament | 1 |

---

## Phase 3: Enrichment (Optional, Significant Accuracy Boost)

| Data | File to Create/Update | Prompt File |
|------|----------------------|-------------|
| Coach tournament experience | `data/coach_scores.json` | `prompts/03_coach_scores.txt` |
| Star player overrides | `data/teams_input.csv` | `prompts/04_star_players.txt` |
| Injury adjustments | `data/overrides.json` | `prompts/05_injury_report.txt` |

Same process: open the prompt file, paste your team name list, send to Claude Research, save the output where indicated.

---

## Phase 4: First Four Play-In Results

**When:** Tuesday and Wednesday nights (March 18-19).

After each play-in game:

1. In `data/teams_input.csv`: set `Won_Play_In = 1` for the 4 winning teams
2. In `data/bracket_input.json`: remove the `play_in` and `play_in_opponent` fields from the winning team entries

---

## Phase 5: Historical Calibration Data (One-Time, Optional)

Improves prediction accuracy but the app runs without it.

1. Create a free Kaggle account at https://www.kaggle.com
2. Download from https://www.kaggle.com/competitions/march-machine-learning-mania-2024/data:
   - `MNCAATourneyCompactResults.csv`
   - `MNCAATourneySeeds.csv`
   - `MTeams.csv`
3. Save to `data/historical/`
4. For BartTorvik historical stats, fetch from the Time Machine:
   `http://barttorvik.com/timemachine/team_results/YYYYMMDD_team_results.json.gz`
   Save as `data/historical/YYYY_teams.csv`

---

## All Files Summary

| File | Format | What Goes In It | Source |
|------|--------|----------------|--------|
| `data/teams_input.csv` | CSV | All team stats + manual columns | `fetch_data.py` creates it, you add columns |
| `data/bracket_input.json` | JSON | 68-team bracket with regions and slots | Claude Research (prompt 02) |
| `data/coach_scores.json` | JSON | Coach experience scores | Claude Research (prompt 03) |
| `data/overrides.json` | JSON | Injury adjustments | Claude Research (prompt 05) |
| `data/team_names.txt` | Text | Canonical team names for prompts | Extracted from teams_input.csv |
| `data/historical/` | CSV | Past tournament data for calibration | Kaggle + Torvik Time Machine |

---

## All Prompt Files

Located in `documentation/prompts/`:

| File | What It Gets You | When to Run |
|------|-----------------|-------------|
| `01_selection_sunday_stats.txt` | Seeds, Q1 wins, last 10 record, conf champs | Selection Sunday night |
| `02_bracket_structure.txt` | Complete bracket JSON with matchups | Selection Sunday night |
| `03_coach_scores.txt` | Coach tournament experience scores | Any time before running app |
| `04_star_players.txt` | Star player overrides for standouts | Any time before running app |
| `05_injury_report.txt` | Injury adjustments | Night before tournament starts |

Every prompt file has the same structure:
1. What the task is and when to run it
2. The exact prompt to copy and send to Claude Research
3. A placeholder for your team name list
4. Instructions for what to do with the output

---

## Timeline for Tonight

| When | What | How Long |
|------|------|----------|
| Now | Run `fetch_data.py` and extract team names | 3 min |
| Now | Copy contents of `data/team_names.txt` somewhere handy | 1 min |
| Bracket announced | Watch the bracket show | -- |
| Right after | Send prompt 01 (selection sunday stats) | 5 min |
| Right after | Send prompt 02 (bracket structure) | 5 min |
| Results come back | Paste stats into CSV, save bracket JSON, verify names | 15 min |
| Same session | Send prompt 03 (coach scores) | 5 min |
| Same session | Send prompt 04 (star players) | 5 min |
| Results come back | Save coach_scores.json, update star player overrides | 5 min |
| **Total Selection Sunday** | | **~45 min** |
| Wed night | Send prompt 05 (injury report), save overrides.json | 5 min |
| Tues/Wed | Set Won_Play_In flags, update bracket JSON | 4 min |
| Thursday | Run the app: `python main.py --mode full` | -- |
