# March Mathness — Product Requirements Document (PRD)

> **Current-state override (2026-03):** For scoring behavior and schema, follow `new_instructions.md`, `documentation/ALGORITHM.md`, and `documentation/DATA_SCHEMA.md`. Any PRD details that conflict are superseded.

**Version:** 2.0  
**Status:** Approved for build  
**Target build time:** ~20 hours solo in Cursor  
**Stack:** Python backend + React/Next.js frontend (or pure Python + Streamlit for speed)

---

## 1. Product Overview

March Mathness is a research-backed NCAA Tournament prediction and bracket analysis engine. It ingests a CSV of per-team statistics (collected once per year, after the bracket is announced), runs a multi-model scoring system grounded in peer-reviewed sports analytics research, and outputs a suite of ranked tables, matchup win probabilities, bracket simulations, and Cinderella detection scores — all readable by a human making bracket decisions.

The app has two modes:
- **Pre-bracket mode:** Teams are not yet seeded; the system ranks all teams and flags Cinderella candidates by statistical profile.
- **Post-bracket mode:** After Selection Sunday, the 68-team bracket is entered (seeds, regions, matchup slots), and the system runs full bracket simulation with round-by-round win probabilities.

---

## 2. Goals and Non-Goals

### Goals
- Produce the most statistically defensible bracket predictions achievable in a solo 20-hour build
- All math must be traceable to peer-reviewed research or validated public rating systems (Torvik, Massey, FiveThirtyEight)
- Generate 6 ranked output tables covering different prediction lenses
- Generate 8 bracket strategy outputs (from conservative to chaos) using Monte Carlo simulation
- Be usable by someone without a statistics background — plain-language labels on every output
- Run fully offline after data ingestion (no live API calls during simulation)
- Support manual injury overrides before running the simulation

### Non-Goals
- Real-time game-day updates or live scoring
- Historical game-by-game replay (we use pre-computed season aggregates)
- Mobile-native app (web UI only)
- Multiplayer bracket pool management
- Anything requiring paid infrastructure

---

## 3. Users

**Primary user:** The builder (you), using this to fill personal brackets and potentially share with friends.  
**Secondary user:** Any technically comfortable person who can edit a CSV and read a table.

There is no authentication, no database, no multi-tenancy. Single user, local or single-server deployment.

---

## 4. Core Feature List

### F1 — Data Ingestion
- Accept a single CSV file (`teams_input.csv`) with one row per team
- Validate all required columns are present; surface clear errors for missing/malformed data
- Support manual override JSON file (`overrides.json`) to adjust specific team stats (e.g., injury adjustments)
- Re-run the full analysis pipeline on demand after data or override changes

### F2 — Efficiency-First Scoring (No CSI Multiplier)
- Do not apply conference-strength multipliers to model scores
- Treat conference adjustments as obsolete in this product version
- Use only team-level metrics from `teams_input.csv` plus normalized/derived features

### F3 — Composite Power Score
- For each team, compute a single composite power score using research-validated weights
- Score is derived from 12 weighted sub-components (see Algorithm doc)
- No conference multiplier step is applied
- Output a Power Rankings table (all teams, sorted by power score)

### F4 — Six Ranked Output Tables
1. **Power Rankings** — overall composite score
2. **Cinderella Rankings** — seeds 9+ only, Cinderella Score (see Algorithm doc)
3. **Defensive Rankings** — defense-weighted composite
4. **Offensive Rankings** — offense-weighted composite
5. **Momentum Rankings** — recency-weighted composite
6. **Giant Killer Rankings** — upset-profile composite (seeds 6+ only)

Each table includes: Rank, Team, Seed, Conference, Score, Key Strengths (plain-language labels), Alert Level where applicable.

### F5 — Matchup Win Probability Engine
- For any pair of teams, compute P(team A wins) using calibrated logistic function based on AdjEM difference
- Accounts for expected pace (average of both teams' adjusted tempo)
- Returns: win probability, predicted point spread, confidence tier

### F6 — Cinderella Detection
- For teams seeded 9 or higher, compute a 6-component Cinderella Score (0–1 scale)
- Flag teams as: 🔴 High Alert (>0.55), 🟡 Watch (0.40–0.55), ⬜ No Signal (<0.40)
- Output a ranked Cinderella table with per-component score breakdown

### F7 — Monte Carlo Bracket Simulation
- Accept the full 68-team bracket (seeds, regions, slot positions) as input
- Run 10,000 Monte Carlo simulations of the entire bracket
- For each team, output: probability of reaching each round (R64, R32, S16, E8, F4, Championship, Champion)
- Output 8 bracket "strategies" — each strategy picks winners using a different model blend:
  1. **Standard** — composite power score
  2. **Favorites** — chalk-heavy, efficiency-first
  3. **Upsets** — actively picks upsets where Cinderella score is high
  4. **Analytics** — pure AdjEM/Barthag logistic
  5. **Cinderella** — maximizes Cinderella score picks
  6. **Defensive** — defense-weighted model
  7. **Momentum** — recency-weighted model
  8. **Experience** — experience and coaching-weighted model

### F8 — Bracket Output Artifacts
- For each of the 8 strategies: bracket JSON, bracket HTML visualization
- Bracket summary: Final Four consensus picks, champion consensus, Cinderella consensus
- Each bracket shows: predicted winner per matchup, win probability, upset flag

### F9 — Dashboard UI
- Single-page HTML dashboard (or Streamlit app)
- Sections: Power Rankings, Team Traits, Cinderella Scores, Fraud Alerts, Matchup Calculator, Bracket Simulation, Bracket Strategies, Pick Sheet
- Each bracket strategy viewable as an interactive bracket diagram
- Color coding: green (dominant favorite), yellow (toss-up), red (likely upset)

### F10 — Manual Injury Override
- User edits `overrides.json` with team name → stat adjustments
- Example: `{"Duke": {"AdjEM": -4.5, "AdjO": -3.0}}` — reduces Duke's efficiency to account for injured player
- Pipeline re-applies overrides before scoring; override flags appear in output tables

---

## 5. Data Flow (high-level)

```
[teams_input.csv]  +  [bracket_input.json]  +  [overrides.json]
        ↓
  [Data Ingestion & Validation]
        ↓
  [Feature Engineering & Normalization]
        ↓
  [Multi-Model Scoring Engine]
        ↓
  [Multi-Model Scoring Engine]
  ┌─────┬────────┬────────┬──────────┬──────────┬────────────┐
  │Power│Cindera-│Defensive│Offensive│Momentum  │Giant Killer│
  │Score│lla     │Score    │Score    │Score     │Score       │
  └─────┴────────┴────────┴──────────┴──────────┴────────────┘
        ↓
  [Win Probability Engine]
        ↓
  [Monte Carlo Bracket Simulation × 10,000]
        ↓
  [8 Strategy Bracket Generators]
        ↓
  [Output Artifacts]
  ┌──────────────────┬───────────────────┬─────────────────┐
  │6 Ranking CSVs    │8 Bracket JSON/HTML│Dashboard HTML   │
  └──────────────────┴───────────────────┴─────────────────┘
```

---

## 6. Input Requirements Summary

### 6.1 Primary Data File: `teams_input.csv`
- One row per team (68 teams post-bracket, up to ~365 pre-bracket)
- Required columns: see `DATA_SCHEMA.md` for complete spec
- Source: auto-assembled by `scripts/fetch_data.py` from BartTorvik, ESPN, and Massey (see `API_DATA_SOURCES.md`)

### 6.2 Bracket File: `bracket_input.json`
- Required only for post-bracket simulation
- Specifies: team name, seed, region, slot number (1–68)
- Format: see `DATA_SCHEMA.md`

### 6.3 Overrides File: `overrides.json`
- Optional; used for injury adjustments
- Format: `{ "TeamName": { "stat_key": adjusted_value, ... } }`
- Applied additively (delta from original) or as absolute override (flag-controlled)

---

## 7. Output Requirements Summary

| Output | Format | When Generated |
|--------|--------|----------------|
| `power_rankings.csv` | CSV | Every run |
| `cinderella_rankings.csv` | CSV | Every run |
| `defensive_rankings.csv` | CSV | Every run |
| `offensive_rankings.csv` | CSV | Every run |
| `momentum_rankings.csv` | CSV | Every run |
| `giant_killer_rankings.csv` | CSV | Every run |
| `matchup_probabilities.csv` | CSV | Post-bracket only |
| `bracket_[strategy].json` | JSON | Post-bracket only |
| `bracket_[strategy].html` | HTML | Post-bracket only |
| `simulation_results.json` | JSON | Post-bracket only |
| `bracket_summary.json` | JSON | Post-bracket only |
| `tournament_dashboard.html` | HTML | Every run |

---

## 8. Non-Functional Requirements

- **Performance:** Full pipeline (all models, 10K simulations) completes in < 30 seconds on a modern laptop
- **Determinism:** Simulation results are reproducible via a fixed random seed (configurable in `config.json`)
- **Portability:** Runs with `python main.py` after `pip install -r requirements.txt`; no Docker required
- **Explainability:** Every score is decomposable into its components; no black-box outputs
- **Extensibility:** Weight dictionaries are external JSON configs, not hardcoded — user can tune without code changes

---

## 9. Configuration File: `config.json`

```json
{
  "random_seed": 42,
  "n_simulations": 10000,
  "cinderella_min_seed": 9,
  "giant_killer_min_seed": 6,
  "fraud_max_seed": 6,
  "giant_killer_seed_gap_minimum": 1,
  "probability_clip_min": 0.03,
  "probability_clip_max": 0.97,
  "game_std_dev": 11.0,
  "recency_window_games": 10,
  "output_dir": "./outputs",
  "data_file": "./data/teams_input.csv",
  "bracket_file": "./data/bracket_input.json",
  "overrides_file": "./data/overrides.json",
  "results_file": "./data/tournament_results.json",
  "coach_scores_file": "./data/coach_scores.json",
  "espn_api_timeout": 10,
  "espn_groups_id": 100,
  "max_adjEM_bonus": 4.0
}
```

---

## 10. Success Criteria

- All 6 ranking tables generate without errors from a complete `teams_input.csv`
- Cinderella scores correlate directionally with historical upset outcomes (manual check against last 3 years)
- Monte Carlo championship probabilities produce reasonable odds for top seeds (1-seeds should have highest championship probability)
- A complete bracket (68 teams, 8 strategies) generates in under 30 seconds
- The dashboard HTML renders correctly in Chrome/Firefox without any server dependency