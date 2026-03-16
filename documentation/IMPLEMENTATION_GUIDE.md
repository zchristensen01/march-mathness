# March Mathness — Implementation Guide
**Version 3.1** — All data sources free ($0/year). Cloudscraper required for Torvik/Massey. Luck computed from Torvik data. No paid subscriptions needed.

**Total build time:** ~20 hours  
**Stack:** Python 3.11 + Streamlit (or static HTML via Jinja2)  
**Approach:** Build the math engine first, UI last. Every hour is accounted for below.

> **Mid-tournament modules note:** `engine/live_results.py` and `engine/tournament_bonus.py` are fully specified in `MID_TOURNAMENT_UPDATES.md`. This guide tells you *when* to build them (Hours 14–15) and how they plug in. Read that document when you reach Hour 14.

---

## 0. Project Setup (30 min)

```bash
mkdir march_mathness && cd march_mathness

# Create directory structure
mkdir -p engine models data/historical outputs/{rankings,brackets,dashboard} templates tests scripts

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install ALL dependencies (note: cloudscraper is required — see API notes)
pip install pandas numpy scipy scikit-learn streamlit jinja2 requests \
            cloudscraper python-dotenv pytest

# Freeze
pip freeze > requirements.txt

# Create empty module files
touch engine/__init__.py engine/ingestion.py engine/normalization.py \
      engine/conference.py engine/scoring.py engine/win_probability.py \
      engine/simulation.py engine/bracket_generator.py \
      engine/live_results.py engine/tournament_bonus.py \
      engine/output.py engine/calibration.py

touch main.py app.py config.json .env

# Add sensitive files to gitignore immediately
echo ".env" >> .gitignore
echo "data/teams_input*.csv" >> .gitignore
```

### `.env` file (optional — for any environment-specific config)

```
# No paid API credentials required. All data sources are free.
# Add any environment-specific overrides here if needed.
```

### `config.json` (create this first)

```json
{
  "random_seed": 42,
  "n_simulations": 10000,
  "apply_conference_adjustment": true,
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

## Pre-Build: Data Fetch Script (run once before starting main pipeline)

**File:** `scripts/fetch_data.py`

Full implementation is in `API_DATA_SOURCES.md` Section 9. Build this FIRST — it generates the `data/teams_input.csv` that all other modules depend on.

**Key functions to implement (in order):**
1. `fetch_torvik_main(year)` — main team stats via cloudscraper (Cloudflare bypass required)
2. `fetch_massey()` — Massey composite rankings via cloudscraper
3. `fetch_ap_poll()` — ESPN AP Top 25 via plain requests (ESPN doesn't need cloudscraper)
4. `fetch_torvik_early_snapshot(year)` — T-Rank snapshot from ~4 weeks before Selection Sunday for ranking trajectory
5. `fetch_espn_net_rank()` — NET rankings via ESPN API (for CompRank)
6. `compute_player_metrics(year)` — Torvik player data → Star_Player_Index
7. `load_coach_scores()` — reads `data/coach_scores.json`
8. `merge_all_sources()` — merges all DataFrames, computes Luck + CompRank, applies Program Prestige and Coach scores, computes RankTrajectory

**Runtime:** ~60 seconds on first run. Saves `data/teams_input.csv` and `data/teams_input_YYYY.csv`.

```bash
# Run after virtual environment is set up:
python scripts/fetch_data.py --year 2026

# Then follow the "Next steps" printed by the script
```

After `fetch_data.py` runs, you still need to manually fill: `Seed`, `Last_10_Games_Metric`, `Quad1_Wins`, `Conf_Tourney_Champion`, and later `Won_Play_In` (after First Four games).  
`NET_Rank` and `Star_Player_Index` are auto-populated by the fetch pipeline when ESPN/Torvik endpoints are available. If those sources fail, the pipeline falls back to defaults and you can optionally backfill manually. See `DATA_INPUT_CHECKLIST.md` for the full post-bracket workflow.

---

## Hour 1–2: Data Ingestion Module

**File:** `engine/ingestion.py`

Implement in this order:

1. `normalize_aliases(df)` — maps all known alternate column names to canonical names. Full alias map in `DATA_SCHEMA.md` Section 11. **Critical alias: `wAB → WAB` (Torvik changes this column name between seasons).**

2. `compute_luck(df)` — computes `Luck = WinPct - Barthag` for all teams. Uses Torvik's Pythagorean model (Barthag). Always computed — no external dependency:
   ```python
   def compute_luck_proxy(df: pd.DataFrame) -> pd.DataFrame:
       if 'Luck' not in df.columns:
           df['Luck'] = np.nan
       mask = df['Luck'].isna()
       if mask.any():
           win_pct = df.loc[mask, 'Wins'].fillna(20) / df.loc[mask, 'Games'].fillna(30).clip(lower=1)
           barthag = df.loc[mask, 'Barthag'].fillna(0.5)
           df.loc[mask, 'Luck'] = (win_pct - barthag).round(4)
       return df
   ```

3. `apply_defaults(df)` — fills missing values with fixed constants from `DATA_SCHEMA.md` Section 1.6. **Zero randomness — no `random.random()` anywhere.**

4. `apply_conf_tourney_champion_bonus(df)` — adds +0.05 to `Last_10_Games_Metric` for teams where `Conf_Tourney_Champion == 1`, capped at 1.0.

5. `apply_overrides(df, overrides_path)` — reads `overrides.json`, applies delta or absolute adjustments to any numeric column (AdjO, AdjD, AdjEM, Star_Player_Index, etc.), sets `OverrideActive = 1` flag. Recalculates `AdjEM = AdjO - AdjD` after applying individual AdjO/AdjD deltas.

6. `validate_columns(df) -> list[str]` — returns list of missing required column names. Empty list = data is clean.

7. `load_teams(csv_path, overrides_path=None) -> pd.DataFrame` — orchestrates all of the above in order. Returns clean DataFrame ready for normalization.

8. `load_bracket(bracket_path) -> dict` — reads `bracket_input.json`, validates structure, returns `{region: [team_dicts]}`.

**Test immediately after building:**
```bash
python -c "
from engine.ingestion import load_teams
df = load_teams('data/teams_input.csv')
print('Shape:', df.shape)
print('Luck nulls:', df['Luck'].isna().sum(), '(should be 0)')
print('Columns:', df.columns.tolist()[:10])
"
```

---

## Hour 3–4: Normalization Module

**File:** `engine/normalization.py`

1. Define `FEATURE_RANGES` as a module-level dict — every feature with `(min, max, direction)` from `ALGORITHM.md` Section 0.2. Direction is `"higher"` or `"inverse"`.

2. `normalize_value(v, min_val, max_val) -> float` — clamp to [0, 1]; return `0.5` for NaN/None.

3. `normalize_inverse(v, min_val, max_val) -> float` — lower raw = higher score; return `0.5` for NaN/None.

4. `normalize_team(team_row: pd.Series) -> dict` — applies correct direction per `FEATURE_RANGES`. Returns `{feature_name: normalized_0_to_1}` for all features.

5. `normalize_all_teams(df) -> list[dict]` — applies `normalize_team` to every row. Returns list parallel to df.

6. `compute_derived_features(norm: dict) -> dict` — the 8 derived features (CloseGame, ThreePtConsistency, BallMovement, Physicality, InsideScoring, InteriorDefense, TournamentReadiness, DefensivePlaymaking). Full formulas in `ALGORITHM.md` Section 0.3.

7. `compute_consistency_score(team: dict) -> float` — `normalize_inverse(abs(Last_10_Games_Metric − WinPct), 0, 0.4)`.

8. `compute_volatility_score(team: dict, norm: dict) -> float` — `0.6 × norm['3P_Rate'] + 0.4 × (1 − consistency_score)`. **This is a risk flag, not a quality metric — never include in PowerScore weights.**

**Test:**
```python
from engine.normalization import normalize_value, normalize_inverse
assert normalize_value(40, -20, 40) == 1.0   # top AdjEM
assert normalize_value(-20, -20, 40) == 0.0  # bottom AdjEM
assert normalize_inverse(80, 80, 125) == 1.0  # best defense (lowest pts allowed)
assert normalize_inverse(125, 80, 125) == 0.0 # worst defense
assert normalize_value(None, 0, 100) == 0.5   # NaN → neutral
```

---

## Hour 5: Conference Module

**File:** `engine/conference.py`

1. Load conference multipliers from `models/conference_weights.json`.

2. `win50_rating(adjems: list[float]) -> float` — uses `scipy.optimize.brentq`. Finds rating R where a team with R would go exactly .500 in a round-robin of the conference. Full implementation in `ALGORITHM.md` Section 1.1.

3. `compute_csi(conf_teams: list[dict]) -> dict` — returns `{win50, nonconf_adj, raw_csi, multiplier}`. Multiplier clamped to [0.75, 1.05].

4. `compute_all_conference_ratings(df: pd.DataFrame) -> pd.DataFrame` — one row per conference, sorted by CSI multiplier descending.

5. `apply_csi_to_teams(df, conf_ratings) -> pd.DataFrame` — adds `CSI` (raw WIN50 value) and `CSI_multiplier` columns to team DataFrame.

**Create `models/conference_weights.json`** with values from `DATA_SCHEMA.md` Section 6.

**Test:**
```python
# SEC and Big 12 should score ≥ 1.0 multiplier
# MEAC, SWAC should score ≈ 0.75-0.80 multiplier
# B10 should score slightly below 1.0 (due to fraud penalty for tournament overperformance)
```

---

## Hour 6–8: Scoring Engine

**File:** `engine/scoring.py`

This is the largest and most important module. Build in this order:

1. Load `models/weights.json` — all 9 model weight dictionaries.
2. Import `PROGRAM_PRESTIGE` dict from `API_DATA_SOURCES.md` Section 6 — copy it directly as a module-level constant.
3. `score_team(norm: dict, derived: dict, weights: dict, csi_multiplier: float) -> float` — weighted sum × 100 × CSI multiplier, rounded to 1 decimal.
4. `score_all_teams(df, norms, deriveds, csi_multipliers, model_name) -> pd.Series`
5. `compute_cinderella_score(team: dict, norm: dict) -> dict` — 6-component formula. **Only runs for Seed ≥ 9; returns `{"CinderellaScore": 0.0, "CinderellaAlertLevel": ""}` for seeds 1–8.** Full formula in `ALGORITHM.md` Section 4.2. **Note: tempo component uses `normalize_inverse` — slower tempo = higher Cinderella score.**
6. `compute_fraud_score(team: dict, norm: dict) -> dict` — 7-component formula. **Only runs for Seed ≤ 6; returns `{"FraudScore": None, "FraudLevel": ""}` for seeds 7–16.** Full formula in `ALGORITHM.md` Section 10. Components: seed deviation (25%), O/D imbalance (25%), form collapse (15%), luck (15%), high-variance style (10%), star dependence (5%), conference (5%). **Note: uses `Luck` column and `implied_seed()` from Section 4.1.**
7. `get_fraud_explanation(team: dict, fraud_result: dict) -> str` — plain-language explanation string. Full implementation in `ALGORITHM.md` Section 10.4.
8. `get_team_strengths(team: dict) -> list[str]` — returns up to 4 strength labels. Full thresholds in `ALGORITHM.md` Section 7.
9. `generate_ranking(df, norms, deriveds, csi_mults, model_name, min_seed=None, max_seed=None) -> pd.DataFrame` — scores all teams, adds CinderellaScore, FraudScore, Consistency, Volatility, Strengths columns, sorts by model score, applies seed filters.
10. `generate_all_rankings(df, norms, deriveds, csi_mults) -> dict[str, pd.DataFrame]` — generates all 6 output tables.

**Create `models/weights.json`** with all 9 weight dicts from `ALGORITHM.md` Section 2.2.

**Ranking output DataFrame columns (complete list, in order):**
```
Rank, Team, Seed, Conference, Record, PowerScore, [ModelScore],
AdjEM, AdjO, AdjD, Barthag, eFG%, Opp_eFG%, TO%, Opp_TO%,
OR%, DR%, FTR, FT%, SOS, Adj_T, WAB, Torvik_Rank,
NET_Rank, CompRank, AP_Poll_Rank, Coach_Tourney_Experience,
Program_Prestige, Last_10_Games_Metric, Luck,
CinderellaScore, CinderellaAlertLevel, SeedMismatch,
FraudScore, FraudLevel, FraudExplanation,
Consistency_Score, Volatility_Score,
CSI, CSI_multiplier, Strengths, OverrideActive
```

**Test:**
```python
# Top-ranked team should appear in top 5 of power rankings
# CinderellaScore column should be blank/None for seeds 1-8
# FraudScore column should be blank/None for seeds 7-16
# All CinderellaAlertLevel 'HIGH' teams should have CinderellaScore >= 0.55
# All FraudLevel 'HIGH' teams should have FraudScore >= 0.60
# Cinderella rankings should only contain seed >= 9
# Giant Killer rankings should only contain seed >= 6
```

---

## Hour 9: Win Probability Engine

**File:** `engine/win_probability.py`

1. `win_probability(team_a: dict, team_b: dict, game_std: float = 11.0) -> float` — normal CDF method. `predicted_spread = (AdjEM_a − AdjEM_b) × avg_tempo / 100`; `P = norm.cdf(spread / 11)`. Clip to [0.03, 0.97].

2. `win_probability_elo(team_a: dict, team_b: dict) -> float` — FiveThirtyEight Elo: `1 / (1 + 10^(−adjEM_diff × 30.464 / 400))`. Clip to [0.03, 0.97].

3. `blended_win_probability(team_a: dict, team_b: dict) -> float` — `0.60 × normal_CDF + 0.40 × elo_style`.

4. `apply_era_seed_prior(model_prob_a: float, seed_a: int, seed_b: int, prior_weight: float = 0.15) -> float` — blends model probability with era-adjusted historical base rate for 6v11, 7v10, 8v9 matchups. 85% model, 15% era prior. From `ALGORITHM.md` Section 3.5.

5. `production_win_probability(team_a: dict, team_b: dict) -> float` — calls `blended_win_probability()` then `apply_era_seed_prior()`. **This is the primary function used everywhere else** — Monte Carlo simulation, bracket strategies, matchup calculator.

6. `predicted_spread(team_a: dict, team_b: dict) -> float` — expected point differential.

7. `confidence_tier(prob: float) -> str` — returns `"Strong Favorite"` / `"Moderate Favorite"` / `"Slight Favorite"` / `"Toss-Up"` / `"Underdog"`. Thresholds: ≥0.85, ≥0.70, ≥0.55, ≥0.45.

8. `apply_fraud_adjustment(win_prob: float, favorite: dict, strategy: str) -> float` — reduces favorite win probability by `FraudScore × 0.08` (max −8%) in `upsets`, `cinderella`, and `analytics` strategies. From `ALGORITHM.md` Section 10.3.

9. `all_matchup_probabilities(teams: list[dict]) -> pd.DataFrame` — n×n matrix showing P(row team beats col team) for all tournament team pairs. Used for the matchup calculator UI tab.

**Test critical cases:**
```python
from engine.win_probability import (win_probability, production_win_probability,
                                     apply_era_seed_prior)

# 1 vs 16 equivalent
assert win_probability({"AdjEM": 30, "Adj_T": 68}, {"AdjEM": -5, "Adj_T": 68}) > 0.97
# 8 vs 9 equivalent (should be near coin flip)
assert 0.44 < win_probability({"AdjEM": 15, "Adj_T": 68}, {"AdjEM": 13, "Adj_T": 68}) < 0.56
# Probability always clipped — never exactly 0 or 1
assert win_probability({"AdjEM": 50, "Adj_T": 68}, {"AdjEM": -20, "Adj_T": 68}) <= 0.97
assert win_probability({"AdjEM": -20, "Adj_T": 68}, {"AdjEM": 50, "Adj_T": 68}) >= 0.03

# Era seed prior pulls 6v11 toward 50/50
raw_6v11 = win_probability({"AdjEM": 16, "Adj_T": 68, "Seed": 6},
                            {"AdjEM": 10, "Adj_T": 68, "Seed": 11})
adjusted_6v11 = apply_era_seed_prior(raw_6v11, 6, 11)
assert adjusted_6v11 < raw_6v11  # era prior pulls favorite probability down

# production_win_probability includes era prior automatically
prod = production_win_probability({"AdjEM": 14, "Adj_T": 68, "Seed": 8},
                                   {"AdjEM": 13, "Adj_T": 68, "Seed": 9})
assert 0.35 < prod < 0.50  # era prior should pull 8-seed below 50%
```

---

## Hour 10–12: Monte Carlo Simulation

**File:** `engine/simulation.py`

1. Define module-level constants:
   ```python
   FIRST_ROUND_MATCHUPS = [(0,1),(2,3),(4,5),(6,7),(8,9),(10,11),(12,13),(14,15)]
   ROUND_NAMES = ["R64", "R32", "S16", "E8", "F4", "Championship", "Champion"]
   ```

2. `_play_game(team_a, team_b, win_prob_fn, reach_count, next_round) -> dict` — simulate a single game, update reach_count for winner, return winning team dict.

3. `simulate_bracket(bracket: dict, win_prob_fn, n_sims: int = 10000, seed: int = 42) -> dict` — full Monte Carlo. Sets `random.seed(seed)` AND `numpy.random.seed(seed)` before loop. Returns `{team_name: {round_name: probability}}`. Convert DataFrame to `list[dict]` before loop for 10× performance.

4. `generate_modal_bracket(simulation_results: dict, bracket: dict, win_prob_fn) -> dict` — picks deterministic winner (higher probability) for each game. Returns structured bracket dict.

**Performance target:** 10,000 simulations should complete in 5–15 seconds. If slower, ensure team data is `list[dict]` not DataFrames inside the hot loop.

**Output format:** See `DATA_SCHEMA.md` Section 8.

**Test:**
```python
# Probabilities are non-increasing across rounds (team can't reach R32 without winning R64)
# Sum of all teams' Champion probability ≈ 1.0 (within 0.001 floating point tolerance)
# A 1-seed should have Champion probability in range [0.10, 0.40]
# A 16-seed should have Champion probability < 0.001
```

---

## Hour 13: Bracket Strategy Generator

**File:** `engine/bracket_generator.py`

1. Load strategy configs from `models/weights.json` — add a `"strategies"` top-level key containing all 8 strategy definitions from `ALGORITHM.md` Section 6.1.

2. `strategy_win_prob(team_a, team_b, strategy, model_scores, base_prob_fn) -> float` — applies strategy-level score blend and Cinderella/Fraud adjustments on top of base win probability. Calls `apply_fraud_adjustment()` for upset-seeking strategies.

3. `simulate_matchup_strategy(team_a, team_b, strategy, model_scores, base_prob_fn) -> dict` — deterministic matchup resolution. Returns `{winner, winner_prob, is_upset, team_a_prob}`. Hard guard: 16-seed never beats 1-seed in `analytics` or `favorites` strategies.

4. `generate_bracket(teams_by_region, strategy_name, strategy_config, model_scores, base_prob_fn) -> dict` — plays through all 63 games deterministically for one strategy. Respects actual bracket structure (see `DATA_SCHEMA.md` Section 2).

5. `generate_all_brackets(teams_by_region, model_scores, simulation_results, base_prob_fn) -> dict` — generates all 8 strategies.

6. `generate_bracket_summary(all_brackets) -> dict` — produces consensus analysis: which teams appear in Final Four across most strategies, which team wins most often, which upsets are consistently picked.

**Strategy bracket output format:** See `DATA_SCHEMA.md` Section 9.

---

## Hour 14: Mid-Tournament Live Update Modules

**These two modules are fully specified in `MID_TOURNAMENT_UPDATES.md`. Read that document now.**

### `engine/live_results.py`
Spec in `MID_TOURNAMENT_UPDATES.md` Section 2.

Functions to implement:
- `fetch_tournament_scores() -> dict` — ESPN scoreboard API. **Note from live testing: ESPN's hidden API endpoints work correctly from a normal computer/server but are blocked in some CI/sandbox environments. This is expected. Add a `try/except` around every ESPN call and fall back to the manual JSON file on failure.**
- `parse_tournament_results(data) -> list[dict]`
- `fetch_game_boxscore(game_id) -> dict`
- `parse_team_game_stats(box_data, team_name) -> dict`
- `fetch_results(config) -> dict` — **the critical auto-detect wrapper**: tries ESPN first, catches any exception (not just connection errors — ESPN silently changes endpoints), falls back to `data/tournament_results.json`. Always print which source was used.

### `engine/tournament_bonus.py`
Spec in `MID_TOURNAMENT_UPDATES.md` Sections 4 and 5.

Functions:
- `compute_tournament_bonus(team_name, completed_games, all_adjEMs) -> dict`
- `apply_tournament_bonuses(df, completed_games, surviving_teams) -> pd.DataFrame`
- `build_remaining_bracket(config, completed_games, df_survivors) -> dict`

---

## Hour 15: Output Writers

**File:** `engine/output.py`

1. `write_ranking_csv(df: pd.DataFrame, model_name: str, output_dir: str)` — saves `{output_dir}/rankings/{model_name}_rankings.csv`. Creates directory if missing.

2. `write_bracket_json(bracket: dict, strategy_name: str, output_dir: str)` — saves `{output_dir}/brackets/bracket_{strategy_name}.json`.

3. `write_bracket_html(bracket: dict, strategy_name: str, output_dir: str, template_dir: str)` — renders Jinja2 bracket template, saves `{output_dir}/brackets/bracket_{strategy_name}.html`.

4. `write_matchup_verdicts_json(teams: list[dict], win_prob_fn, output_dir: str)` — pre-computes all bracket matchup verdicts using `classify_matchup_verdict()` from `UI_OUTPUT_DESIGN.md` Section 4. Saves `{output_dir}/bracket_matchup_verdicts.json`. This is the pre-computed file the UI reads — no math at render time.

5. `write_simulation_json(results: dict, output_dir: str)` — saves `{output_dir}/simulation_results.json`.

6. `write_summary_json(summary: dict, output_dir: str)` — saves `{output_dir}/bracket_summary.json`.

7. `write_bracket_pick_sheet(rankings: dict, simulation: dict, verdicts: list, output_dir: str)` — generates the plain-text printable pick guide `{output_dir}/my_bracket_picks.txt`. Format specified in `UI_OUTPUT_DESIGN.md` Section 8.

8. `write_all_outputs(rankings, brackets, simulation, summary, config)` — calls all of the above; creates all output subdirectories.

---

## Hour 16: Main Orchestrator

**File:** `main.py`

```python
"""
main.py — March Mathness CLI entry point

Usage:
  python main.py --mode full        # rankings + simulation + brackets
  python main.py --mode rankings    # rankings only (no bracket needed)
  python main.py --mode simulate    # simulation + brackets (rankings must exist)
  python main.py --mode update      # mid-tournament re-score (see MID_TOURNAMENT_UPDATES.md)
"""

import argparse, json, time
from engine.ingestion import load_teams, load_bracket
from engine.normalization import (normalize_all_teams, compute_derived_features,
                                   compute_consistency_score, compute_volatility_score)
from engine.conference import compute_all_conference_ratings, apply_csi_to_teams
from engine.scoring import (generate_all_rankings, compute_cinderella_score,
                             compute_fraud_score, generate_bracket_summary)
from engine.win_probability import production_win_probability, blended_win_probability
from engine.simulation import simulate_bracket, generate_modal_bracket
from engine.bracket_generator import generate_all_brackets
from engine.output import write_all_outputs
from engine.live_results import fetch_results
from engine.tournament_bonus import apply_tournament_bonuses, build_remaining_bracket


def main():
    parser = argparse.ArgumentParser(description="March Mathness")
    parser.add_argument('--mode', choices=['full', 'rankings', 'simulate', 'update'],
                        default='full')
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--sims', type=int, default=None)
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)
    if args.seed: config['random_seed'] = args.seed
    if args.sims: config['n_simulations'] = args.sims

    if args.mode == 'update':
        run_tournament_update(config)
        return

    print("=" * 60)
    print("MARCH MATHNESS — Tournament Prediction Engine")
    print("=" * 60)
    t0 = time.time()

    # ── STEP 1: Load and validate data ──────────────────────────────
    print("\n[1/6] Loading team data...")
    df = load_teams(config['data_file'], config.get('overrides_file'))
    print(f"  ✓ {len(df)} teams loaded")
    if df['Luck'].isna().any():
        print("  ⚠ Luck column has nulls after proxy computation — check ingestion")

    # ── STEP 2: Normalize + derive scores ───────────────────────────
    print("\n[2/6] Normalizing features...")
    norms = normalize_all_teams(df)
    deriveds = [compute_derived_features(n) for n in norms]
    for i, (_, row) in enumerate(df.iterrows()):
        norms[i]['Consistency_Score'] = compute_consistency_score(row.to_dict())
        norms[i]['Volatility_Score'] = compute_volatility_score(row.to_dict(), norms[i])
    print(f"  ✓ {len(norms[0])} features normalized per team")

    # ── STEP 3: Conference Strength Index ───────────────────────────
    print("\n[3/6] Computing Conference Strength Index...")
    conf_ratings = compute_all_conference_ratings(df)
    df = apply_csi_to_teams(df, conf_ratings)
    print(f"  ✓ {len(conf_ratings)} conference CSI values computed")

    # ── STEP 4: All ranking models ───────────────────────────────────
    print("\n[4/6] Running scoring models...")
    csi_multipliers = df['CSI_multiplier'].tolist()
    rankings = generate_all_rankings(df, norms, deriveds, csi_multipliers)
    for model_name, rdf in rankings.items():
        print(f"  ✓ {model_name}: {len(rdf)} teams ranked")

    # Print terminal summary
    _print_terminal_summary(rankings)

    if args.mode == 'rankings':
        write_all_outputs(rankings, {}, {}, {}, config)
        print(f"\n✅ Done in {time.time()-t0:.1f}s — outputs saved to {config['output_dir']}")
        return

    # ── STEP 5: Monte Carlo simulation ──────────────────────────────
    print("\n[5/6] Running Monte Carlo simulation...")
    bracket = load_bracket(config['bracket_file'])
    team_lookup = {row['Team']: row.to_dict() for _, row in df.iterrows()}
    bracket_with_stats = {
        region: [team_lookup.get(t['team'], {'Team': t['team'], 'AdjEM': 0, 'Adj_T': 68})
                 for t in teams]
        for region, teams in bracket['teams_by_region'].items()
    }
    simulation_results = simulate_bracket(
        bracket_with_stats, production_win_probability,
        n_sims=config['n_simulations'], seed=config['random_seed']
    )
    print(f"  ✓ {config['n_simulations']:,} simulations complete")

    # ── STEP 6: Bracket strategies ───────────────────────────────────
    print("\n[6/6] Generating bracket strategies...")
    model_scores = {}
    for model_name, rdf in rankings.items():
        for _, row in rdf.iterrows():
            if row['Team'] not in model_scores:
                model_scores[row['Team']] = {}
            model_scores[row['Team']][model_name] = row.get('PowerScore', 50)

    all_brackets = generate_all_brackets(
        bracket_with_stats, model_scores, simulation_results, production_win_probability
    )
    print(f"  ✓ {len(all_brackets)} bracket strategies generated")

    write_all_outputs(rankings, all_brackets, simulation_results,
                      generate_bracket_summary(all_brackets), config)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"✅ Complete in {elapsed:.1f}s")
    print(f"   Rankings:  {config['output_dir']}/rankings/")
    print(f"   Brackets:  {config['output_dir']}/brackets/")
    print(f"   Pick Sheet:{config['output_dir']}/my_bracket_picks.txt")
    print(f"   Dashboard: {config['output_dir']}/dashboard/tournament_dashboard.html")
    print(f"{'='*60}")


def run_tournament_update(config: dict):
    """Mid-tournament re-score. Full implementation in MID_TOURNAMENT_UPDATES.md Section 5."""
    # See MID_TOURNAMENT_UPDATES.md for complete implementation
    pass


def _print_terminal_summary(rankings: dict):
    """Prints the human-readable terminal output after analysis. Spec in UI_OUTPUT_DESIGN.md Section 7."""
    power = rankings.get('default', list(rankings.values())[0])
    cinderella = rankings.get('cinderella', power[power.get('Seed', 16) >= 9] if 'Seed' in power.columns else power)
    fraud = power[power['FraudLevel'].isin(['HIGH', 'MEDIUM'])] if 'FraudLevel' in power.columns else power.iloc[0:0]

    print(f"\n{'='*60}")
    print("TOP 10 POWER RANKINGS")
    print("-" * 60)
    for _, row in power.head(10).iterrows():
        print(f"  #{int(row['Rank']): <3} {row['Team']:<22} Seed:{str(row.get('Seed','?')):<4} Score:{row.get('PowerScore',0):.1f}  AdjEM:+{row.get('AdjEM',0):.1f}")

    if 'CinderellaScore' in cinderella.columns:
        high_alerts = cinderella[cinderella.get('CinderellaAlertLevel','') == 'HIGH'] if 'CinderellaAlertLevel' in cinderella.columns else cinderella.iloc[0:0]
        if len(high_alerts):
            print(f"\n🔴 CINDERELLA ALERTS (HIGH — Score > 0.55)")
            print("-" * 60)
            for _, row in high_alerts.iterrows():
                opp = "TBD"  # populated after bracket is known
                print(f"  {row['Team']:<22} #{row.get('Seed','?')} ({row.get('Conference','?')})  Score:{row.get('CinderellaScore',0):.2f}")

    if len(fraud):
        print(f"\n💀 FRAUD ALERTS (Seeds 1-6 with structural weaknesses)")
        print("-" * 60)
        for _, row in fraud.head(5).iterrows():
            print(f"  {row['Team']:<22} #{row.get('Seed','?')} ({row.get('Conference','?')})  FraudScore:{row.get('FraudScore',0):.2f}  [{row.get('FraudLevel','')}]")
            if 'FraudExplanation' in row:
                print(f"    → {row['FraudExplanation'][:80]}")


if __name__ == '__main__':
    main()
```

---

## Hour 17: Streamlit UI

**File:** `app.py`

```python
"""
app.py — March Mathness Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import json
import os
import tempfile

st.set_page_config(
    page_title="March Mathness 🏀",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏀 March Mathness — Tournament Prediction Engine")

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_csv = st.file_uploader("Upload teams_input.csv", type=['csv'])
    uploaded_bracket = st.file_uploader("Upload bracket_input.json", type=['json'])
    n_sims = st.slider("Monte Carlo Simulations", 1000, 50000, 10000, step=1000)
    seed = st.number_input("Random Seed", value=42, step=1)

    st.header("🩹 Injury Overrides")
    override_text = st.text_area(
        "Paste JSON overrides (optional)",
        value='{\n  "TeamName": {\n    "mode": "delta",\n    "AdjEM": -3.5,\n    "note": "Key player injured"\n  }\n}',
        height=120
    )

    run_button = st.button("🚀 Run Full Analysis", type="primary", use_container_width=True)

    st.divider()

    st.header("🔄 Mid-Tournament Update")
    update_source = st.radio("Results source", ["Auto (ESPN API)", "Manual JSON"])
    if update_source == "Manual JSON":
        results_upload = st.file_uploader("Upload tournament_results.json", type=['json'])
    update_button = st.button("🔄 Fetch & Re-Score", use_container_width=True)

# ── Run pipeline when button pressed ────────────────────────────────
if run_button and uploaded_csv:
    with st.spinner("Running full analysis pipeline..."):
        import subprocess, sys, json as _json

        # Save uploaded files to temp locations
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='wb') as f:
            f.write(uploaded_csv.getvalue())
            csv_path = f.name

        overrides_path = None
        try:
            overrides_data = _json.loads(override_text)
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
                _json.dump(overrides_data, f)
                overrides_path = f.name
        except Exception:
            pass

        bracket_path = None
        if uploaded_bracket:
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='wb') as f:
                f.write(uploaded_bracket.getvalue())
                bracket_path = f.name

        mode = 'full' if bracket_path else 'rankings'
        cmd = [sys.executable, 'main.py', '--mode', mode,
               f'--sims={n_sims}', f'--seed={seed}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            st.success("✅ Analysis complete!")
        else:
            st.error(f"Pipeline error:\n{result.stderr[-500:]}")

# ── Tabs ────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Power Rankings",
    "🔮 Cinderella Scores",
    "💀 Fraud Alerts",
    "🏆 Conference Strength",
    "🎯 Matchup Calculator",
    "🎲 Bracket Simulation",
    "📋 Bracket Strategies",
    "📄 Pick Sheet",
])

# ── Tab 1: Power Rankings ────────────────────────────────────────────
with tab1:
    st.subheader("📊 Power Rankings")
    path = "outputs/rankings/power_rankings.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)

        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            conf_filter = st.multiselect("Filter by Conference", sorted(df['Conference'].unique()))
        with col2:
            seed_range = st.slider("Seed range", 1, 16, (1, 16))
        with col3:
            flag_filter = st.multiselect("Show flags", ["⚠️ Override", "🟣 Volatile"])

        filtered = df.copy()
        if conf_filter:
            filtered = filtered[filtered['Conference'].isin(conf_filter)]
        if 'Seed' in filtered.columns:
            filtered = filtered[filtered['Seed'].between(seed_range[0], seed_range[1])]

        def score_color(val):
            try:
                v = float(val)
                if v >= 75: return 'background-color:#1a7f37;color:white'
                if v >= 60: return 'background-color:#2da44e;color:white'
                if v >= 45: return 'background-color:#f59e0b;color:black'
                return 'background-color:#ef4444;color:white'
            except: return ''

        display_cols = [c for c in ['Rank','Team','Seed','Conference','PowerScore',
                         'AdjEM','AdjO','AdjD','Barthag','FraudLevel',
                         'Volatility_Score','Strengths','OverrideActive']
                        if c in filtered.columns]
        styled = filtered[display_cols].style.applymap(score_color, subset=['PowerScore'])
        st.dataframe(styled, use_container_width=True)
    else:
        st.info("Run analysis to see power rankings.")

# ── Tab 2: Cinderella Scores ─────────────────────────────────────────
with tab2:
    st.subheader("🔮 Cinderella Detection — Seeds 9+")
    path = "outputs/rankings/cinderella_rankings.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        alert_filter = st.selectbox("Filter", ["All", "🔴 HIGH ALERT only", "🟡 WATCH only"])

        def fmt_alert(val):
            if val == 'HIGH': return '🔴 HIGH ALERT'
            if val == 'WATCH': return '🟡 WATCH'
            return '⬜ No signal'

        df['Alert'] = df.get('CinderellaAlertLevel', pd.Series([''] * len(df))).apply(fmt_alert)

        if "HIGH" in alert_filter:
            df = df[df.get('CinderellaAlertLevel','') == 'HIGH']
        elif "WATCH" in alert_filter:
            df = df[df.get('CinderellaAlertLevel','') == 'WATCH']

        for _, row in df.iterrows():
            with st.expander(f"{row.get('Alert','⬜')} {row['Team']} (#{row.get('Seed','?')}) — Score: {row.get('CinderellaScore',0):.3f}"):
                c1, c2 = st.columns(2)
                with c1:
                    components = {
                        'Seed Mismatch': row.get('C_SeedMismatch', 0),
                        'Defense': row.get('C_Defense', 0),
                        'Turnover': row.get('C_Turnover', 0),
                        'Experience': row.get('C_Experience', 0),
                        'Tempo': row.get('C_Tempo', 0),
                        'Rebounding': row.get('C_Rebounding', 0),
                    }
                    for label, val in components.items():
                        st.progress(float(val) if pd.notna(val) else 0, text=f"{label}: {val:.2f}")
                with c2:
                    st.metric("AdjEM", f"+{row.get('AdjEM',0):.1f}")
                    st.metric("Conference", row.get('Conference', '?'))
                    st.write("**Strengths:**", row.get('Strengths', 'N/A'))
    else:
        st.info("Run analysis to see Cinderella scores.")

# ── Tab 3: Fraud Alerts ──────────────────────────────────────────────
with tab3:
    st.subheader("💀 Fraud Alerts — Seeds 1–6 With Structural Weaknesses")
    st.caption("Teams that look strong on paper but have profiles that March Madness historically exposes.")
    path = "outputs/rankings/power_rankings.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        fraud_cols = ['FraudScore', 'FraudLevel']
        if all(c in df.columns for c in fraud_cols):
            fraud_df = df[df['FraudLevel'].isin(['HIGH', 'MEDIUM', 'LOW'])].copy()
            fraud_df = fraud_df.sort_values('FraudScore', ascending=False)

            for _, row in fraud_df.iterrows():
                level = row.get('FraudLevel', '')
                icon = '💀' if level == 'HIGH' else '⚠️' if level == 'MEDIUM' else '📋'
                score = row.get('FraudScore', 0)
                with st.expander(f"{icon} {row['Team']} (#{row.get('Seed','?')} {row.get('Conference','?')}) — Fraud Score: {score:.3f} [{level}]"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**Why this team is a fraud risk:**")
                        explanation = row.get('FraudExplanation', 'No explanation computed.')
                        st.write(explanation)
                    with c2:
                        components = {
                            'Seed Deviation': row.get('F_SeedDeviation', 0),
                            'O/D Imbalance': row.get('F_Imbalance', 0),
                            'Form Collapse': row.get('F_FormCollapse', 0),
                            'Luck (Over-Record)': row.get('F_Luck', 0),
                            'High-Variance Style': row.get('F_Variance', 0),
                            'Star Dependence': row.get('F_StarDependence', 0),
                            'Conference Bias': row.get('F_Conference', 0),
                        }
                        for label, val in components.items():
                            try:
                                st.progress(float(val) if pd.notna(val) else 0, text=f"{label}: {val:.2f}")
                            except: pass
        else:
            st.info("FraudScore column not found — ensure Seed column is populated and re-run.")
    else:
        st.info("Run analysis to see fraud alerts.")

# ── Tab 4: Conference Strength ────────────────────────────────────────
with tab4:
    st.subheader("🏆 Conference Strength Index")
    path = "outputs/rankings/conference_strength.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(df, use_container_width=True)
        with c2:
            if 'CSI_multiplier' in df.columns and 'Conference' in df.columns:
                chart_df = df.set_index('Conference')[['CSI_multiplier']].sort_values('CSI_multiplier', ascending=True)
                st.bar_chart(chart_df)
        st.caption("Multiplier > 1.0 = stronger conference. B10 penalty reflects historical tournament underperformance vs seed.")
    else:
        st.info("Run analysis to see conference strength.")

# ── Tab 5: Matchup Calculator ────────────────────────────────────────
with tab5:
    st.subheader("🎯 Head-to-Head Matchup Calculator")
    path = "outputs/rankings/power_rankings.csv"
    if os.path.exists(path):
        df = pd.read_csv(path)
        teams = sorted(df['Team'].tolist())
        c1, c2 = st.columns(2)
        with c1:
            team_a_name = st.selectbox("Team A", teams, index=0)
        with c2:
            team_b_name = st.selectbox("Team B", teams, index=min(1, len(teams)-1))

        if st.button("Calculate Matchup"):
            row_a = df[df['Team'] == team_a_name].iloc[0].to_dict()
            row_b = df[df['Team'] == team_b_name].iloc[0].to_dict()

            from engine.win_probability import production_win_probability, predicted_spread, confidence_tier
            p_a = production_win_probability(row_a, row_b)
            spread = predicted_spread(row_a, row_b)
            tier = confidence_tier(p_a)

            st.markdown(f"### {team_a_name} vs {team_b_name}")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric(f"P({team_a_name} wins)", f"{p_a*100:.1f}%")
            mc2.metric("Predicted spread", f"{team_a_name} {'+' if spread>0 else ''}{spread:.1f}")
            mc3.metric("Confidence", tier)

            if row_a.get('FraudLevel') in ['HIGH', 'MEDIUM']:
                st.warning(f"⚠️ {team_a_name} has a {row_a.get('FraudLevel','')} Fraud Score ({row_a.get('FraudScore',0):.2f}) — their win probability may be inflated.")
            if row_b.get('CinderellaAlertLevel') in ['HIGH', 'WATCH']:
                st.info(f"🔴 {team_b_name} has a {row_b.get('CinderellaAlertLevel','')} Cinderella Score ({row_b.get('CinderellaScore',0):.2f}) — this could be an upset.")
    else:
        st.info("Run analysis to use matchup calculator.")

# ── Tab 6: Bracket Simulation ─────────────────────────────────────────
with tab6:
    st.subheader("🎲 Monte Carlo Simulation Results")
    path = "outputs/simulation_results.json"
    if os.path.exists(path):
        with open(path) as f:
            sim = json.load(f)

        rows = []
        for team, rounds in sim.get('results', {}).items():
            rows.append({'Team': team, **rounds})
        df = pd.DataFrame(rows).sort_values('Champion', ascending=False)

        # Format as percentages
        pct_cols = [c for c in df.columns if c != 'Team']
        pct_df = df.copy()
        for col in pct_cols:
            pct_df[col] = (pct_df[col] * 100).round(1).astype(str) + '%'

        st.dataframe(pct_df, use_container_width=True)
        st.caption(f"Based on {sim.get('n_simulations', 10000):,} simulations with seed {sim.get('random_seed', 42)}")
    else:
        st.info("Run full analysis (with bracket file) to see simulation results.")

# ── Tab 7: Bracket Strategies ─────────────────────────────────────────
with tab7:
    st.subheader("📋 Bracket Strategies — All 8 Models")

    strategy = st.selectbox("Strategy", [
        "standard", "favorites", "upsets", "analytics",
        "cinderella", "defensive", "momentum", "experience"
    ])

    bracket_path = f"outputs/brackets/bracket_{strategy}.json"
    if os.path.exists(bracket_path):
        with open(bracket_path) as f:
            bracket = json.load(f)

        c1, c2, c3 = st.columns(3)
        c1.metric("Champion", bracket.get('champion', 'TBD'))
        c2.metric("Strategy", bracket.get('strategy', strategy).title())
        c3.metric("Description", bracket.get('description', '')[:40])

        st.write("**Final Four:**", " | ".join(bracket.get('final_four', [])))

        # Consensus view
        summary_path = "outputs/bracket_summary.json"
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                summary = json.load(f)
            st.subheader("Model Consensus")
            st.write(f"**Champion (most models):** {summary.get('champion_consensus', 'TBD')}")
            st.write(f"**Final Four consensus:** {', '.join(summary.get('final_four_consensus', []))}")

            if st.checkbox("Show Contested Games"):
                contested = summary.get('contested_games', [])
                if contested:
                    for game in contested:
                        st.warning(f"⚖️ {game.get('matchup','')} — {game.get('models_split','')} model split")
    else:
        st.info("Run full analysis to see bracket strategies.")

# ── Tab 8: Pick Sheet ─────────────────────────────────────────────────
with tab8:
    st.subheader("📄 Printable Bracket Pick Sheet")
    path = "outputs/my_bracket_picks.txt"
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        st.code(content, language=None)
        st.download_button("⬇️ Download Pick Sheet", content, "march_madness_picks.txt", "text/plain")
    else:
        st.info("Run full analysis to generate the pick sheet.")
```

---

## Hour 17.5: Probability Calibration (Optional, High-Value)

**File:** `engine/calibration.py`

Isotonic regression calibration on win probabilities is one of the highest-leverage low-effort improvements available. It corrects the raw logistic output so that "70% probability" means wins 70% of the time empirically. Without it, the normal CDF tends to be slightly overconfident at extreme probabilities — exactly where bracket picks go wrong in Elite Eight and Final Four rounds.

**Expected improvement:** ~0.015–0.025 Brier Score reduction vs uncalibrated output.
**Requires:** 3+ years of historical data (ideally 7+) in `data/historical/`. Use Kaggle MMLM dataset (2015–2024 = ~630 tournament games) combined with BartTorvik Time Machine stats.

Functions to implement:

1. `load_historical_probs(years: list[int]) -> list[tuple[float, int]]` — loads (predicted_probability, actual_outcome) pairs from historical tournament games. For each game, compute `blended_win_probability(team_a, team_b)` using that year's pre-tournament stats, pair with `1` if team_a won, `0` if not.

2. `fit_isotonic_calibration(probs: list[float], outcomes: list[int]) -> IsotonicRegression` — fits `sklearn.isotonic.IsotonicRegression(y_min=0.03, y_max=0.97, out_of_bounds='clip')` on the (prob, outcome) pairs.

3. `calibrate_probability(raw_prob: float, model: IsotonicRegression) -> float` — transforms a raw win probability through the fitted calibration curve. Returns clipped to [0.03, 0.97].

4. `save_calibration_model(model: IsotonicRegression, path: str)` — pickles the fitted model to `models/calibration.pkl`.

5. `load_calibration_model(path: str = 'models/calibration.pkl') -> IsotonicRegression | None` — loads a saved model. Returns `None` if file doesn't exist (uncalibrated mode).

```python
from sklearn.isotonic import IsotonicRegression
import pickle, os

def fit_isotonic_calibration(probs, outcomes):
    iso = IsotonicRegression(y_min=0.03, y_max=0.97, out_of_bounds='clip')
    iso.fit(probs, outcomes)
    return iso

def calibrate_probability(raw_prob, model):
    if model is None:
        return raw_prob
    return float(model.predict([raw_prob])[0])
```

**Usage:** After running `scripts/backtest.py`, fit isotonic regression on historical (prob, outcome) pairs. Save model. In production, wrap `blended_win_probability()` output through `calibrate_probability()` before use in Monte Carlo and bracket generation.

**Integration in `main.py`:**
```python
from engine.calibration import load_calibration_model, calibrate_probability

calibration_model = load_calibration_model()
if calibration_model:
    print("  ✓ Calibration model loaded — probabilities will be isotonic-calibrated")
    original_win_prob = production_win_probability
    def calibrated_win_prob(a, b):
        return calibrate_probability(original_win_prob(a, b), calibration_model)
    win_prob_fn = calibrated_win_prob
else:
    print("  ℹ No calibration model — using raw probabilities")
    win_prob_fn = production_win_probability
```

---

## Hour 18: HTML Bracket Visualization Template

**File:** `templates/bracket.html.j2`

Renders a static, self-contained HTML bracket for each strategy. Key requirements:

- 4 region columns (East, West, South, Midwest) using CSS flexbox
- 6 rounds displayed left-to-right within each region
- Winner highlighted in the verdict color system from `UI_OUTPUT_DESIGN.md` Section 2
- Upset marked with ⚡, Fraud team marked with 💀, Cinderella team marked with 🔴
- Win probability shown as small text under each matchup
- Entire file is self-contained (no external dependencies) — open directly in a browser
- Jinja2 template variables: `strategy_name`, `description`, `champion`, `final_four`, `regions` (nested bracket data)

---

## Hour 19: Data Fetch Script + Backtest

**File:** `scripts/fetch_data.py`

Full implementation in `API_DATA_SOURCES.md` Section 9. **Copy it directly.** Key points:
- Uses `cloudscraper.create_scraper()` for Torvik and Massey — required due to Cloudflare protection
- Falls back gracefully if any source fails
- Prints clear ⚠️ warnings for each failed source
- Always computes `Luck` proxy after merge (WinPct − Barthag)

**File:** `scripts/backtest.py`

```bash
python scripts/backtest.py --years 2022 2023 2024
```

Expected output:
```
Year  | Accuracy | Log Loss | Brier | vs Seed-Only Baseline
2022  | 73.2%    | 0.548    | 0.195 | +4.1%
2023  | 71.8%    | 0.562    | 0.201 | +2.3%
2024  | 74.5%    | 0.531    | 0.188 | +5.9%
Avg   | 73.2%    | 0.547    | 0.195 | +4.1%
```

---

## Hour 20: Integration Testing and Polish

**Checklist:**

- [ ] `python scripts/fetch_data.py --year 2026` completes without errors; check that `Luck` column has no nulls
- [ ] `python main.py --mode rankings` generates all 6 ranking CSVs with `FraudScore` and `CinderellaScore` columns
- [ ] `python main.py --mode full` generates all outputs including 8 brackets and pick sheet
- [ ] `python -m pytest tests/` — all tests pass
- [ ] `streamlit run app.py` — all 8 tabs render and are functional
- [ ] 10,000-simulation bracket run completes in < 30 seconds
- [ ] `FraudScore` column is `None`/blank for seeds 7–16 (not zero)
- [ ] `CinderellaScore` column is `None`/blank for seeds 1–8
- [ ] Cinderella rankings only contain seeds ≥ 9
- [ ] Giant Killer rankings only contain seeds ≥ 6
- [ ] Conference strength table covers all conferences in data
- [ ] Injury override sets `OverrideActive = 1` and modifies AdjEM correctly
- [ ] `Luck` column: verify `Luck` is computed from Torvik data (WinPct − Barthag) for all teams — should never be null after ingestion
- [ ] `python main.py --mode update` attempts ESPN fetch without crashing (even if ESPN API is unavailable it should fall back gracefully to manual JSON)
- [ ] Modal bracket has no team appearing in two games in the same round
- [ ] All 8 strategy JSONs have valid `champion` and `final_four` keys
- [ ] `my_bracket_picks.txt` is human-readable and contains all 63 games with verdict labels

---

## Critical Implementation Warnings

### 1. No randomness in defaults
Never use `random.uniform()` for any default value. Use fixed constants from `DATA_SCHEMA.md` Section 1.6.

### 2. SOS normalization direction — previous codebase had this backwards
SOS is a **rank** (1 = hardest schedule). Use `normalize_inverse(SOS, 1, 365)` so rank 1 (hardest) gets the highest score.

### 3. AdjEM derivation first
Always compute `AdjEM = AdjO − AdjD` before any normalization. Many downstream calculations assume it exists.

### 4. Conference weights are a secondary multiplier
CSI is already embedded in AdjEM (Torvik's model solves cross-conference comparison simultaneously). The JSON multipliers are a residual correction only. Do not double-count.

### 5. Win probability clipping
Always clip to `[0.03, 0.97]`. Never allow exactly 0.0 or 1.0.

### 6. Reproducible simulation
Set both `random.seed()` AND `numpy.random.seed()` at the start of `simulate_bracket()`.

### 7. Monte Carlo performance — use dicts not DataFrames in hot loop
Convert DataFrame to `list[dict]` before the simulation loop. Dict key access is ~10× faster than `df.loc[]` over 630,000 iterations.

### 8. Strategy brackets vs simulation — separate outputs
Strategy brackets are deterministic (one predicted winner per game). Monte Carlo produces probability distributions. Build them separately. Do not confuse them.

### 9. Fraud Score scope
`compute_fraud_score()` only runs for `Seed ≤ 6`. For seeds 7–16, set `FraudScore = None` and `FraudLevel = ""`. This is intentional and meaningful — the fraud concept only applies to teams expected to advance deep.

### 10. Luck metric — always computed from Torvik data
`ingestion.py` computes `Luck = WinPct − Barthag` for all teams automatically. The Fraud Score's luck component (15% weight) is always populated. No external dependency required.

### 11. Torvik requires cloudscraper, not requests
Torvik is behind Cloudflare. Simple `requests.get()` returns 403. Use `cloudscraper.create_scraper().get()` everywhere. This is confirmed by live testing. One-line change in `fetch_data.py`.

### 12. ESPN API works from real computers, not CI environments
The ESPN hidden API endpoints (`site.api.espn.com/...`) are blocked in sandboxed/CI environments due to network restrictions. They work correctly from a normal laptop or server. Always wrap every ESPN call in a try/except with a clean fallback. Do not panic-flag ESPN as broken during development if you're running in a restricted environment.

### 13. All data sources are free
No paid subscriptions required. BartTorvik, Massey, and ESPN APIs are all free. Luck is computed from Torvik data (WinPct − Barthag). CompRank averages Torvik_Rank, Massey_Rank, and NET_Rank.

### 14. WAB column name varies by Torvik year
Torvik sometimes exports this column as `WAB`, sometimes as `wAB`. The `normalize_aliases()` function in `ingestion.py` must map `wAB → WAB`. Verify during the first `fetch_data.py` run of the season.

---

## File Creation Order (recommended)

1. `config.json`
2. `.env` (credentials only — already gitignored)
3. `data/coach_scores.json` (add entries for this year's coaches — 15 min)
4. `models/weights.json` (copy all 9 weight dicts from `ALGORITHM.md` Section 2.2)
5. `models/conference_weights.json` (copy from `DATA_SCHEMA.md` Section 6)
6. `engine/ingestion.py` (includes Luck proxy — Warning #10)
7. `engine/normalization.py`
8. `engine/conference.py`
9. `engine/scoring.py` (includes Cinderella Score AND Fraud Score)
10. `engine/win_probability.py` (includes `apply_fraud_adjustment()`)
11. `engine/simulation.py`
12. `engine/bracket_generator.py`
13. `engine/output.py` (includes `write_bracket_pick_sheet()`)
14. `main.py` (core pipeline + `--mode update` stub)
15. `engine/live_results.py` ← full spec in `MID_TOURNAMENT_UPDATES.md` Section 2
16. `engine/tournament_bonus.py` ← full spec in `MID_TOURNAMENT_UPDATES.md` Sections 4 & 5
17. Update `main.py` — fill in `run_tournament_update()` from `MID_TOURNAMENT_UPDATES.md` Section 5
18. `scripts/fetch_data.py` ← full implementation in `API_DATA_SOURCES.md` Section 9 (uses cloudscraper)
19. `app.py` (complete Streamlit UI — 8 tabs as above)
20. Update `app.py` — wire up mid-tournament update sidebar to `run_tournament_update()` from `MID_TOURNAMENT_UPDATES.md` Section 6
21. `templates/bracket.html.j2`
22. `tests/` — unit tests for each engine module
23. `scripts/backtest.py`

---

## Prompt Template for Cursor Sessions

```
I'm building March Mathness, a NCAA tournament prediction engine.
Reference documents: PRD.md, DATA_SCHEMA.md, ALGORITHM.md

Please implement [MODULE_NAME] in [FILE_PATH].

Requirements:
- [function names and signatures from this doc]
- [any special edge cases noted in Critical Implementation Warnings]

The module imports from:
- engine/ingestion.py (already built)
- engine/normalization.py (already built)

Dependencies allowed: pandas, numpy, scipy, scikit-learn, cloudscraper, requests.
Do NOT add any other dependencies.
```

**For mid-tournament modules specifically:**
```
I'm building March Mathness. Please implement engine/live_results.py.
Full spec is in MID_TOURNAMENT_UPDATES.md Section 2.
Key note: wrap every ESPN API call in try/except — the API works from real 
computers but may be blocked in some environments. Always fall back to 
data/tournament_results.json on any failure.
Dependencies: requests only (no cloudscraper needed for ESPN).
```

**For the data fetch script:**
```
I'm building March Mathness. Please implement scripts/fetch_data.py.
Full spec is in API_DATA_SOURCES.md Section 9.
Critical: use cloudscraper.create_scraper().get() for Torvik and Massey
endpoints — simple requests.get() returns 403 due to Cloudflare.
After all merges, compute Luck proxy: df['Luck'] = (Wins/Games) - Barthag
for any rows where Luck is still NaN.
```