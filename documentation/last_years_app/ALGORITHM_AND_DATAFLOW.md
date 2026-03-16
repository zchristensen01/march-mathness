# March Mathness: Legacy App Math + Dataflow (Archived)

This document describes the **previous JavaScript app** and is retained for historical reference only.
For the active implementation, use `new_instructions.md`, `documentation/ALGORITHM.md`, and `documentation/DATA_SCHEMA.md`.

---

## 1) End-to-end pipeline

Primary execution path:

1. `tournament_analyzer.js` loads `final_table.csv`.
2. It parses rows via `enhanced_ranking_system.processCSV()`.
3. It computes ranked outputs for multiple models via `runAnalysis()` / `recalculateScores()`.
4. It writes ranking CSVs:
   - `default-rankings.csv`
   - `cinderella-rankings.csv`
   - `defensive-rankings.csv`
   - `offensive-rankings.csv`
   - `momentum-rankings.csv`
   - `giant-killer-rankings.csv`
5. It generates bracket strategies through `bracket_generator.generateBrackets()`.
6. It writes bracket artifacts:
   - `bracket_standard.json`, `bracket_favorites.json`, `bracket_upsets.json`, `bracket_analytics.json`, `bracket_cinderella.json`, `bracket_physical.json`, `bracket_momentum.json`, `bracket_experience.json`
   - matching `bracket_*.html`
   - `bracket_summary.json`
   - `bracket_summary.txt`

Supporting scripts:

- `bracket_generator_runner.js`: runner for bracket generation only.
- `visualization_tool.js`: reads generated CSV/JSON outputs and builds `tournament_dashboard.html`.
- `bracket_visualizer.js`: generates per-strategy bracket HTML visualization.
- `tournament_analysis_tool.js`: alternate analysis script (browser-style `window.fs` usage, not the main Node pipeline).

---

## 2) Raw inputs: what stats go in

Canonical source file:

- `final_table.csv`

Header columns currently present include:

- Identity/context: `Team`, `Seed`, `Conference`, `Conf_Strength_Weight`, `Record`, `Wins`, `Games`
- Efficiency: `AdjEM`, `AdjO`, `AdjD`, `Barthag`, `PPP_Off`, `PPP_Def`
- Shooting: `eFG%`, `Opp_eFG%`, `3P%`, `2P%`, `2P_%_D`, `3P_%_D`
- Possessions/ball control: `TO%`, `Opp_TO%`, `AST_TO`, `Ast_%`, `Op_Ast_%`
- Rebounding/physical: `OR%`, `DR%`, `Blk_%`, `Blked_%`, `Avg_Hgt`, `Eff_Hgt`
- FT and style: `FTR`, `Opp_FTR`, `FT%`, `Tempo`, `Raw_T`, `Adj_T`, `3P_Rate`, `3P_Rate_D`
- Schedule/ranks/form: `SOS`, `Elite_SOS`, `Quad1_Wins`, `Last_10_Games_Metric`, `KenPom_Rank`, `Torvik_Rank`, `Massey_Rank`, `NET_Rank`
- Composition: `Exp`, `Star_Player_Index`, `Bench_Minutes_Pct`

---

## 3) Preprocessing and field mapping

### 3.1 CSV parsing

`processCSV(csvText)`:

- Splits header row and parses each line with `parseCSVLine()` that supports quoted commas.
- Converts numeric-looking strings to numbers.
- Sends each team object through `inspectAndFixTeam()`.

### 3.2 Field aliases normalized by code

`inspectAndFixTeam()` maps alternate names to expected fields, e.g.:

- `Adj OE -> AdjO`
- `Adj DE -> AdjD`
- `eFG D. -> Opp_eFG%`
- `TOV% -> TO%`
- `TOV% D -> Opp_TO%`
- `O Reb% -> OR%`
- `FT Rate -> FTR`
- `FT Rate D -> Opp_FTR`
- `3P % D. -> 3P_%_D`
- `2P % D. -> 2P_%_D`
- `Raw T -> Raw_T`
- `Adj. T -> Adj_T`
- `PPP Off. -> PPP_Off`
- `PPP Def. -> PPP_Def`
- `Elite SOS -> Elite_SOS`
- `Avg Hgt. -> Avg_Hgt`
- `Eff. Hgt. -> Eff_Hgt`
- `Exp. -> Exp`

Also:

- derives `AdjEM = AdjO - AdjD` if missing
- derives `DR% = 100 - Opp_OR%` when possible

### 3.3 Default fallback behavior (important for reproducibility)

When fields are missing, defaults are injected; several use randomness:

- `Seed`: `"10"` if missing
- `Conference`: `"Unknown"` if missing
- `Star_Player_Index`: random `5..10` if missing
- `Bench_Minutes_Pct`: random `20..40` if missing
- `Last_10_Games_Metric`: random `0.5..1.0` if missing

Implication: if source data is incomplete, runs can become non-deterministic.

---

## 4) Core scoring math

The main scoring function is:

- `calculateTeamScore(team, weights, attributeWeightsForModel = {}, applyConference = true)`

### 4.1 Normalization

All component features are normalized to `[0, 1]` using:

- `normalizeValue(v, min, max) = clamp((v - min) / (max - min))`
- `normalizeInverse(v, min, max) = clamp((max - v) / (max - min))` (lower raw is better)

If missing/NaN, normalized value defaults to `0.5`.

Key ranges used in code:

- `AdjEM [-20, 40]`, `AdjO [95, 130]`, `AdjD inverse [80, 125]`
- `eFG% [45, 60]`, `Opp_eFG% inverse [40, 60]`
- `3P% [30, 40]`, `2P% [45, 60]`
- `3P_%_D inverse [25, 40]`, `2P_%_D inverse [40, 55]`
- `TO% inverse [10, 25]`, `Opp_TO% [10, 25]`
- `OR% [20, 40]`, `DR% [65, 85]`
- `FTR [20, 45]`, `Opp_FTR inverse [20, 45]`, `FT% [65, 80]`
- `AST_TO [0.8, 2.1]`, `Ast_% [40, 65]`, `Op_Ast_% inverse [35, 60]`
- `SOS [1, 350]` (code uses normalizeValue; higher numeric SOS gets higher normalized score)
- `Elite_SOS [0, 50]`, `Quad1_Wins [0, 12]`
- `Star_Player_Index [1, 10]`, `Bench_Minutes_Pct [20, 40]`, `Exp [0, 3]`
- `Avg_Hgt [75, 80]`, `Eff_Hgt [77, 83]`
- `Last_10_Games_Metric [0.30, 1.0]`
- average ranking (`KenPom/Torvik/Massey/NET`) inverse-normalized in `[1, 350]`
- `Barthag [0.2, 1.0]`
- `PPP_Off [0.9, 1.25]`, `PPP_Def inverse [0.8, 1.2]`
- `Tempo/Raw_T/Adj_T [60, 75]`
- `3P_Rate [25, 50]`, `3P_Rate_D inverse [30, 50]`
- `Blk_% [5, 20]`, `Blked_% inverse [5, 15]`
- Win% normalized from `wins/games` in `[0.4, 0.95]`

### 4.2 Derived features (computed on top of normalized primitives)

- `closeGamePerformance = (lastTen + winPct + 0.5*ftPct + 0.5*to) / 3`
- `threePtConsistency = (threeP + 0.7*threeRate) / 1.7`
- `tournamentHistory = (barthag + 0.5*experience + 0.5*consistencyRank) / 2`
- `coachExperience = (experience + tournamentHistory) / 2`
- `physicality = (or + blkPct + ftr + 0.5*effHeight) / 3.5`
- `insideScoring = (twoP + or + 0.5*ftr) / 2.5`
- `interiorDefense = (twoPD + blkPct + dr) / 3`

### 4.3 Component formulas

Score starts at zero and accumulates weighted components:

- Core: `AdjEM`, `AdjO`, `AdjD`
- Composite features:
  - Shooting score (model-specific mix of eFG/opp eFG/3P/2P/3P_D/2P_D)
  - Turnover score (model-specific TO vs Opp_TO emphasis)
  - Rebounding score (model-specific OR/DR/height emphasis)
  - Free-throw score (model-specific FTR/Opp_FTR/FT%)
  - Ball movement score: `0.5*AST_TO + 0.3*Ast_% + 0.2*Op_Ast_%_inverse`
  - Height score: `0.4*Avg_Hgt + 0.6*Eff_Hgt`
  - PPP score (offense-only, defense-only, or blended depending on model)
  - Tempo score (slow favored for defensive model, fast for offensive model, softened blend for others)
  - Three-point profile: `0.6*3P_Rate + 0.4*3P_Rate_D_inverse`
  - Defensive playmaking: `0.6*Blk_% + 0.4*Blked_%_inverse`
- Direct terms also include `SOS`, `EliteSOS`, `Quad1Wins`, `StarPower`, `BenchMinutes`, `Experience`, `Momentum`, `Consistency`, `Barthag`

Then:

1. `score = score * 100`
2. If conference adjustment enabled: `score *= conferenceWeights[Conference]` (default 1.0)
3. Rounded to 1 decimal

Final formula shape:

`Calculated_Score = round1( 100 * (Σ(weight_i * component_i) + optional_extra_terms) * conference_weight )`

---

## 5) Model catalog (weights currently implemented)

Weight objects in `enhanced_ranking_system.js`:

1. `defaultWeights`
2. `championshipWeights`
3. `cinderellaWeights`
4. `defensiveWeights`
5. `offensiveWeights`
6. `momentumWeights`
7. `giantKillerWeights`
8. `physicalDominanceWeights`
9. `tournamentExperienceWeights`
10. `clutchPerformanceWeights`
11. `balancedExcellenceWeights`

How they are used:

- Ranking CSVs from `tournament_analyzer.js` currently use:
  - default
  - cinderella
  - defensive
  - offensive
  - momentum
  - giant-killer
- Bracket strategies use mixtures of model outputs (Section 7).

Conference multipliers (`conferenceWeights`) are also applied in scoring, e.g.:

- `SEC: 1.00`, `Big Ten: 0.98`, `Big 12: 0.96`, ..., `MEAC: 0.75`

---

## 6) Additional analysis outputs (beyond straight ranking)

### 6.1 Team strengths text labels

`getTeamStrengths(team)` derives qualitative labels from hard thresholds (examples):

- `3P% > 36` => "excellent 3-point shooting"
- `eFG% > 55` => "efficient shooting"
- `Opp_eFG% < 46` => "strong defensive field goal percentage"
- `TO% < 15`, `Opp_TO% > 20`, `AST_TO > 1.5`, `FT% > 75`, `Last_10_Games_Metric > 0.8`, etc.

These strings are emitted in ranking CSVs and upset summaries.

### 6.2 Upset potential (`identifyUpsetPotential`)

Process:

1. Recalculate scores for all teams.
2. Use hardcoded first-round matchups by region.
3. Compute `upsetPotential = underdogScore / favoriteScore`.
4. Apply per-matchup thresholds:
   - default `0.85`
   - `8/9`: `0.95`
   - `7/10`: `0.90`
   - favorite seed `1` or `2`: `0.75`
5. Return top 5 by upset potential.

### 6.3 Final Four prediction (`predictFinalFour`)

Currently implemented as:

- score all teams (using provided `weights` or default)
- take top 4 ranked teams
- assign them to fixed region order: `East, West, South, Midwest`

It does **not** perform bracket-path simulation for this path.

---

## 7) Bracket generation algorithm

Main function: `bracket_generator.generateBrackets()`.

### 7.1 Strategy definitions (8 generated brackets)

- `standard`
- `favorites`
- `upsets`
- `analytics`
- `cinderella`
- `physical`
- `momentum`
- `experience`

Each strategy defines a linear blend of model scores and an `upsetThreshold`.

Example structure:

- `weightedScore = Σ(strategy_weight_k * modelScore_k) [+ optional adjO/adjD terms]`

### 7.2 Game simulation (`simulateMatchup`)

Given two teams:

1. Favorite/underdog determined by lower/higher seed number.
2. Base favorite probability:
   - `favoriteWinProb = favoriteWeightedScore / (favoriteWeightedScore + underdogWeightedScore)`
3. Seed adjustment:
   - `+ min(0.15, seedDiff * 0.01)` when seed gap > 2
4. Upset-supporting heuristics (subtract from favorite probability):
   - `-0.05` if underdog forces TO (`Opp_TO% > 22`) and favorite turns it over (`TO% > 18`)
   - `-0.05` if underdog shoots 3s well (`3P% > 37` and `3P_Rate > 40`)
   - `-0.03` if underdog experienced (`Exp > 2.3`) and favorite inexperienced (`Exp < 1.8`)
5. Upset decision:
   - upset if `(1 - adjustedFavoriteWinProb) > upsetThreshold`
   - except explicit guard: 16 over 1 blocked

No Monte Carlo randomness is used in matchup resolution; it is deterministic for fixed inputs.

### 7.3 Region bracket progression

Per region:

- Round of 64 -> Round of 32 (`roundOf32` array)
- Round of 32 -> Sweet 16 (`sweet16` array)
- Sweet 16 -> Elite 8 (`elite8` array)
- Elite 8 -> region winner (`finalFour[0]`, `winner`)

Then:

- Final Four semifinals: East vs West, South vs Midwest
- Championship: semifinal winners

---

## 8) Output artifacts: what comes out at each stage

### 8.1 Ranking-stage outputs

- `default-rankings.csv`
- `cinderella-rankings.csv` (filtered to seed >= 6 in `tournament_analyzer.js`)
- `defensive-rankings.csv`
- `offensive-rankings.csv`
- `momentum-rankings.csv`
- `giant-killer-rankings.csv` (filtered to seed >= 6)

Common ranking CSV schema starts with:

- `Rank, Team, Seed, Conference, Calculated_Score, ...`

and includes model inputs plus `Strengths`.

### 8.2 Bracket-stage outputs

- 8 JSON brackets (`bracket_*.json`)
- 8 HTML visualizations (`bracket_*.html`)
- Summary:
  - `bracket_summary.json` with:
    - `finalFourTeams`
    - `champions`
    - `cinderellaTeams`
    - `consistentFinalFour`
    - `consistentChampions`
    - `consistentCinderellas`
    - `totalBrackets`
  - `bracket_summary.txt` human-readable summary

### 8.3 Dashboard output

- `tournament_dashboard.html` generated from summary and ranking files.

---

## 9) Implementation quirks and mismatches (important for plan comparison)

These are current behaviors in code, not hypothetical issues:

1. **Final Four analysis path can produce zero scores**
   - In `tournament_analyzer.js`, `runAnalysis('final4', teams, enhancedRankingSystem.attributeWeights)` passes a non-weight object into `predictFinalFour`.
   - `predictFinalFour` forwards that as `weights` into `recalculateScores`.
   - Because that object lacks expected scalar weight keys (`AdjEM`, `AdjO`, etc.), `Calculated_Score` can become `0` for every team in this path.

2. **`createModifiedWeightSystems()` is currently unused**
   - Called in `generateBrackets()`, but returned enhanced weights are not applied downstream.

3. **Hardcoded bracket mappings differ across functions**
   - `identifyUpsetPotential` and `simulateBracket` use hardcoded team-region lists that are not fully consistent with each other.

4. **Comment-to-code mismatch in Cinderella helper**
   - `identifyCinderellas` comment says double-digit seeds, but filter is `seed >= 8`.
   - Comment says "Top 5 candidates" but code slices 10.

5. **Random defaults can affect outputs when data is missing**
   - Missing `Star_Player_Index`, `Bench_Minutes_Pct`, `Last_10_Games_Metric` inject random values.

6. **`SOS` direction as coded rewards larger numeric SOS**
   - Normalized via `normalizeValue(SOS, 1, 350)` rather than inverse normalization.
   - Whether that is intended depends on how `SOS` is represented in this dataset.

---

## 10) Practical interpretation of current algorithm

In plain terms, the system is:

- a deterministic weighted composite model framework
- with normalization to a common 0..1 feature scale
- plus conference multiplier
- plus strategy-level blending for bracket picks
- plus deterministic upset heuristics
- with many outputs generated as materialized CSV/JSON/HTML artifacts

The strongest "control knobs" today are:

- model weight dictionaries in `enhanced_ranking_system.js`
- strategy blends and upset thresholds in `bracket_generator.js`
- data completeness in `final_table.csv`

---

## 11) Quick reference: main function contracts

- `processCSV(csvText) -> Team[]`
- `calculateTeamScore(team, weights, attributeWeightsForModel?, applyConference?) -> number`
- `recalculateScores(teams, weights, attributeWeightsParam?, applyConference?) -> Team[] sorted desc by Calculated_Score`
- `runAnalysis(type, teams, attributeWeightsParam?) -> Team[] | upset[] | finalFour[]`
- `generateBrackets() -> { brackets, summary, teamMap }`
- `findUpsets(bracket) -> upset[]`
- `generateDashboard() -> "tournament_dashboard.html"`

---

If you want, the next step can be a second MD that is a **gap analysis**: "current implementation vs your new design target", with exact migration actions ranked by impact/risk.
