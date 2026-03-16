# March Mathness — Data Schema & Format Specification
**Version 2.0** — Updated to include all metrics from gap analysis.

This document defines every input and output format in the system. Claude should treat this as the ground truth for all data contracts.

---

## 1. Primary Input: `teams_input.csv`

One row per team. The pipeline accepts up to 365 rows (full D-I season) but operates primarily on 68 post-bracket teams. All numeric values should be in the units specified. Missing values should be left as empty string — the pipeline will substitute documented defaults.

### 1.1 Required Columns (pipeline will error without these)

| Column | Type | Unit/Range | Description | Source |
|--------|------|-----------|-------------|--------|
| `Team` | string | — | Official team name (must match bracket_input.json exactly) | Torvik |
| `Seed` | int | 1–16 | Tournament seed (leave blank pre-bracket) | Manual / ESPN |
| `Conference` | string | — | Conference abbreviation (e.g., `SEC`, `Big12`, `ACC`, `B10`) | Torvik |
| `AdjO` | float | 95–130 | Adjusted offensive efficiency: points per 100 possessions vs avg D-I defense | Torvik |
| `AdjD` | float | 80–125 | Adjusted defensive efficiency: points allowed per 100 possessions vs avg D-I offense | Torvik |
| `AdjEM` | float | -20 to +40 | Adjusted efficiency margin = AdjO − AdjD (computed by pipeline if missing) | Torvik |
| `Barthag` | float | 0.00–1.00 | Pythagorean win expectancy vs avg D-I team on neutral court | Torvik |

### 1.2 Tier-2 Columns (strong predictive signal — include if possible)

| Column | Type | Unit/Range | Direction | Description | Source |
|--------|------|-----------|-----------|-------------|--------|
| `eFG%` | float | 44–62 | Higher better | Effective field goal % offense: (FGM + 0.5×3PM) / FGA × 100 | Torvik |
| `Opp_eFG%` | float | 40–60 | Lower better | Effective FG% allowed (opponent's eFG%) | Torvik |
| `TO%` | float | 10–25 | Lower better | Turnover rate: turnovers per 100 possessions (offense) | Torvik |
| `Opp_TO%` | float | 10–25 | Higher better | Opponent turnover rate forced per 100 possessions (defense) | Torvik |
| `OR%` | float | 18–45 | Higher better | Offensive rebound percentage | Torvik |
| `DR%` | float | 60–86 | Higher better | Defensive rebound percentage (pipeline computes as 100 − Opp_OR% if missing) | Torvik |
| `FTR` | float | 20–55 | Higher better | Free throw rate: FTA / FGA × 100 (offense) | Torvik |
| `Opp_FTR` | float | 20–55 | Lower better | Opponent free throw rate allowed | Torvik |
| `FT%` | float | 62–85 | Higher better | Free throw percentage | Torvik |
| `SOS` | float | 1–365 | Lower number = harder | Strength of schedule rank (1 = hardest schedule) | Torvik |
| `Adj_T` | float | 60–80 | Neutral | Adjusted tempo: possessions per 40 minutes | Torvik |
| `CompRank` | float | 1–365 | Lower better | Composite rank: avg(Torvik_Rank, Massey_Rank, NET_Rank) — pipeline-computed, not an input column | Pipeline |
| `Torvik_Rank` | int | 1–365 | Lower better | BartTorvik T-Rank | Torvik |
| `NET_Rank` | int | 1–365 | Lower better | NCAA Evaluation Tool rank (committee metric) | NCAA |
| `WAB` | float | -10 to +15 | Higher better | Wins Above Bubble: wins above what a bubble team would produce on same schedule | Torvik |

### 1.3 Tier-3 Columns (moderate signal — include if available)

| Column | Type | Unit/Range | Direction | Description | Source |
|--------|------|-----------|-----------|-------------|--------|
| `3P%` | float | 28–42 | Higher better | 3-point field goal percentage (offense) | Torvik |
| `3P_%_D` | float | 28–42 | Lower better | 3-point percentage allowed (defense) | Torvik |
| `2P%` | float | 45–62 | Higher better | 2-point field goal percentage (offense) | Torvik |
| `2P_%_D` | float | 40–58 | Lower better | 2-point percentage allowed (defense) | Torvik |
| `3P_Rate` | float | 25–55 | Neutral | Percentage of FGA that are 3-point attempts (offense) — used in Volatility Score | Torvik |
| `3P_Rate_D` | float | 25–55 | Lower better | Opponent 3-point attempt rate allowed | Torvik |
| `AST_TO` | float | 0.8–2.5 | Higher better | Assist-to-turnover ratio | Torvik |
| `Ast_%` | float | 40–70 | Higher better | Percentage of field goals assisted (offense) | Torvik |
| `Op_Ast_%` | float | 35–65 | Lower better | Opponent assist percentage | Torvik |
| `Blk_%` | float | 4–20 | Higher better | Block percentage (defense) | Torvik |
| `Blked_%` | float | 2–14 | Lower better | Percentage of own FGA blocked by opponent | Torvik |
| `PPP_Off` | float | 0.9–1.3 | Higher better | Points per possession, offense | Torvik |
| `PPP_Def` | float | 0.8–1.2 | Lower better | Points per possession allowed, defense | Torvik |
| `Avg_Hgt` | float | 73–81 | Higher better | Average height of lineup (inches) | Torvik |
| `Eff_Hgt` | float | 75–84 | Higher better | Effective height (weighted by minutes) | Torvik |
| `Raw_T` | float | 60–80 | Neutral | Raw (unadjusted) tempo | Torvik |
| `AP_Poll_Rank` | int | 1–26 | Lower better | Final regular-season AP Poll rank. Unranked = 26. Fetched automatically by fetch_data.py via ESPN API | ESPN free API |
| `Luck` | float | -0.10 to +0.10 | Lower better for favs | Gap between actual win% and efficiency-predicted win% (`WinPct − Barthag`). High positive = regression candidate / fraud risk (15% fraud weight). Year-to-year correlation is just 0.06 — treat as penalty modifier. Computed from Torvik data — always available. | Computed (Torvik data) |

### 1.4 Tier-4 Columns (supplementary — manually added or computed from lookup tables)

| Column | Type | Unit/Range | Direction | Description | Source |
|--------|------|-----------|-----------|-------------|--------|
| `Quad1_Wins` | int | 0–15 | Higher better | Wins vs Quad 1 opponents (top ~75 teams by NET rank, on road/neutral) | Manual/ESPN |
| `Elite_SOS` | float | 0–50 | Higher better | Percentage of games vs top-50 NET opponents | Manual |
| `Last_10_Games_Metric` | float | 0.0–1.0 | Higher better | Win rate over last 10 games including conf tournament (1.0 = 10-0). Include conf tournament wins | Manual |
| `Massey_Rank` | int | 1–365 | Lower better | Massey composite ranking (aggregates 50+ systems) | masseyratings.com |
| `Star_Player_Index` | float | 1–10 | Higher better | Presence/quality of star player(s); 10 = elite NBA prospect. Auto-computed from Torvik player BPM data; override manually for standouts | Auto (Torvik players) |
| `Coach_Tourney_Experience` | float | 0–10 | Higher better | Composite coach tournament experience score. Scoring rubric: +3 Final Four 2x, +2 Natl Champ, +2 won conf tourney 3x, +2 15+ NCAA appearances, +1 500+ career wins. Research: 7 of 10 recent champions had coaches with 24+ years experience | Manual once/year (~15 min) |
| `Program_Prestige` | float | 0–10 | Higher better | Blue blood / program history index. Duke/Kansas/Kentucky = 10, default unlisted = 2. See PROGRAM_PRESTIGE dict in API_DATA_SOURCES.md. Added automatically by fetch_data.py | Static lookup (auto-applied) |
| `TRank_Early` | int | 1–365 | Lower better | Torvik T-Rank snapshot ~4 weeks before Selection Sunday. Used to compute ranking trajectory: `TRank_Early − Torvik_Rank` = positive means team improved. Source: BartTorvik Time Machine endpoint (automated via fetch_data.py) | Auto (Torvik Time Machine) |
| `Won_Play_In` | int | 0/1 | — | 1 if team won a First Four play-in game. Play-in winners receive +3% first-round win probability boost (battle-tested effect). Fill after First Four games (Tues/Wed before R64) | Manual binary flag |
| `Conf_Tourney_Champion` | int | 0/1 | Higher better | 1 if team won their conference tournament. Pipeline adds +0.05 to Last_10_Games_Metric before scoring | Manual binary flag |
| `Record` | string | "W-L" | — | Season record (e.g., "28-5"); used for display only | Torvik (Rec column) |
| `Wins` | int | 0–35 | — | Total wins — parsed from Record | Torvik (auto-parsed) |
| `Games` | int | 0–40 | — | Total games played — parsed from Record | Torvik (auto-parsed) |
| `Conf_Strength_Weight` | float | 0.75–1.05 | — | Manual conference multiplier override (overrides computed CSI if provided) | Manual |

### 1.5 Pipeline-Computed Columns (do NOT include in input — pipeline adds these)

These are computed by the pipeline from the input columns above. Never include them in `teams_input.csv`.

| Column | Formula / Description |
|--------|----------------------|
| `AdjEM` | `AdjO − AdjD` if not provided in input |
| `DR%` | `100 − Opp_OR%` if `DR%` missing but opponent offensive rebound % is present |
| `CompRank` | Average of `Torvik_Rank`, `Massey_Rank`, `NET_Rank` (uses whichever are available) |
| `WinPct` | `Wins / Games` |
| `PowerScore` | Composite power score — main model output from DEFAULT_WEIGHTS |
| `CinderellaScore` | 6-component Cinderella detection score (seeds 9+ only, else 0). Full formula in `ALGORITHM.md` Section 4 |
| `CinderellaAlertLevel` | `HIGH` (≥0.55), `WATCH` (≥0.40), blank (<0.40) — seeds 9+ only |
| `FraudScore` | 7-component structural weakness score (seeds 1–6 only, else 0). Full formula in `ALGORITHM.md` Section 10. Components: seed deviation (25%), offensive-defensive imbalance (25%), recent form collapse (15%), Luck (15%), high-variance style (10%), star dependence (5%), conference bias (5%) |
| `FraudLevel` | `HIGH` (≥0.60), `MEDIUM` (≥0.40), `LOW` (≥0.25), blank — seeds 1–6 only |
| `Consistency_Score` | `normalize_inverse(abs(Last_10_Games_Metric − WinPct), 0, 0.4)` — inverse of game-to-game performance variance. Research: Harvard Cox survival model found consistency significant at 5% level |
| `Volatility_Score` | `0.6 × norm(3P_Rate) + 0.4 × (1 − Consistency_Score)` — risk metric only, NOT used in PowerScore. Shown as warning badge in UI. High = boom-or-bust team |
| `CSI` | Conference Strength Index WIN50 value for team's conference |
| `CSI_multiplier` | Normalized CSI → multiplier in [0.75, 1.05] applied to all model scores |
| `SeedMismatch` | `implied_seed(CompRank) − Seed` (positive = team is underseeded = Cinderella candidate). See seed mapping in `ALGORITHM.md` Section 4.1 |
| `MomentumDelta` | `Last_10_Games_Metric − WinPct` — positive means team is improving toward tournament |
| `RankTrajectory` | `TRank_Early − Torvik_Rank` — positive = team improved in efficiency rankings heading into tournament. Normalized to [-30, 30] range. Feeds into `NETMomentum` derived feature |
| `Strengths` | List of up to 4 plain-language strength labels (e.g., "elite defense", "forces turnovers") |

### 1.6 Default Values for Missing Data (deterministic — no randomness)

**Critical: zero random defaults anywhere in the pipeline.** All defaults are fixed constants.

| Column | Default | Rationale |
|--------|---------|-----------|
| `Seed` | `10` | Middle seed; neutral assumption |
| `Conference` | `"Unknown"` | Flagged for manual review |
| `Star_Player_Index` | `5.0` | Average player quality |
| `Last_10_Games_Metric` | `0.65` | Slight above-.500 default |
| `Massey_Rank` | `150` | Middle of field |
| `Elite_SOS` | `10.0` | Below-average elite SOS |
| `Quad1_Wins` | `3` | Modest Q1 record |
| `Avg_Hgt` | `77.0` | Average D-I height |
| `Eff_Hgt` | `79.0` | Average effective height |
| `AP_Poll_Rank` | `26` | Unranked — just outside AP Top 25 |
| `Coach_Tourney_Experience` | `3.0` | Limited tournament history |
| `Program_Prestige` | `2.0` | Default for unlisted programs |
| `Luck` | computed | Auto-computed as `WinPct − Barthag` — never needs a hardcoded default |
| `WAB` | `2.0` | Modest wins above bubble |
| `Conf_Tourney_Champion` | `0` | Did not win conference tournament |

---

## 2. Bracket Input: `bracket_input.json`

Used for post-bracket Monte Carlo simulation. Populated after Selection Sunday.

### Format

```json
{
  "year": 2026,
  "regions": ["East", "West", "South", "Midwest"],
  "teams": [
    {
      "team": "Duke",
      "seed": 1,
      "region": "East",
      "slot": 1
    },
    {
      "team": "North Carolina",
      "seed": 16,
      "region": "East",
      "slot": 2
    }
  ]
}
```

### Slot numbering convention

Within each region (16 teams, slots 1–16):
- Slots 1 & 2: 1 vs 16
- Slots 3 & 4: 8 vs 9
- Slots 5 & 6: 5 vs 12
- Slots 7 & 8: 4 vs 13
- Slots 9 & 10: 6 vs 11
- Slots 11 & 12: 3 vs 14
- Slots 13 & 14: 7 vs 10
- Slots 15 & 16: 2 vs 15

The bracket proceeds: lower slot number teams play higher slot number teams within each pair. Winner of 1v16 plays winner of 8v9 in R32, etc. (standard NCAA bracket structure).

### First Four

Play-in games produce 4 additional teams (seeds 11 and 16 typically). Represent as:

```json
{
  "team": "Alabama State",
  "seed": 16,
  "region": "East",
  "slot": 2,
  "play_in": true,
  "play_in_opponent": "St. Francis PA"
}
```

The pipeline resolves play-in games first using win probability before running main simulation.

---

## 3. Overrides File: `overrides.json`

Used for injury adjustments and manual corrections. Applied before any scoring runs.

```json
{
  "Duke": {
    "mode": "delta",
    "AdjO": -3.5,
    "AdjD": 1.2,
    "AdjEM": -4.7,
    "Star_Player_Index": -4.0,
    "note": "Flagg out — lose top-5 pick, massive offensive and star-dependence impact"
  },
  "Kansas": {
    "mode": "absolute",
    "AdjEM": 18.5,
    "note": "Reset AdjEM to pre-slump level"
  }
}
```

- `mode: "delta"` — values are added to the team's original stats
- `mode: "absolute"` — values replace the team's original stats entirely
- `note` is optional, shown in output tables next to overridden teams
- Any numeric column from `teams_input.csv` can be overridden (AdjO, AdjD, AdjEM, Star_Player_Index, etc.)

### Star Player Injury Interaction

When a star player is injured, **both** adjustments should be applied:

1. **AdjEM reduction** — the team is objectively weaker without the player. This directly lowers win probability in every game.
2. **Star_Player_Index reduction** — the team's scoring model changes. This affects:
   - The DEFAULT_WEIGHTS model score (Star_Player_Index has 2% weight)
   - The Fraud Score's "star dependence" component (10% of fraud score): a team with a high star index and low bench that LOSES that star becomes even more vulnerable
   - Bracket strategy picks (teams without star power get ranked lower in several strategies)

**Guidelines for Star_Player_Index delta when a player is injured:**

| Injured Player Type | Star_Player_Index Delta | AdjEM Delta |
|---------------------|------------------------|-------------|
| Projected top-5 NBA pick (9-10 rating) | -4 to -5 | -4 to -6 |
| Projected lottery pick (7-8 rating) | -3 to -4 | -2.5 to -4 |
| All-Conference starter (5-6 rating) | -1 to -2 | -1.5 to -3 |
| Rotation player (3-4 rating) | 0 to -1 | -0.5 to -1.5 |
| Player returning from injury (boost) | +1 to +2 | +1 to +2 |

---

## 4. Coach Scores File: `data/coach_scores.json`

Update once per year after the bracket is announced (~15 minutes of lookup).

```json
{
  "_default": 3,
  "Duke": 9,
  "Kansas": 10,
  "Michigan State": 10,
  "Kentucky": 8,
  "UConn": 9,
  "Arizona": 6,
  "Gonzaga": 7,
  "Baylor": 6
}
```

**Scoring rubric for Coach_Tourney_Experience (0–10):**
- +3 pts: Coach has been to Final Four 2+ times
- +2 pts: Coach has won a national championship
- +2 pts: Coach has 15+ NCAA Tournament appearances
- +2 pts: Coach has made the Sweet 16 3+ times
- +1 pt: Coach has 500+ career wins

`_default` is used for any team not listed (new coaches, limited history = 3).

---

## 5. Model Weights: `models/weights.json`

All model weight dictionaries are stored here, not in code. Each model is a JSON object with feature name → weight. Weights in each model must sum to 1.0. Full weight dictionaries with exact values are in `ALGORITHM.md` Section 2.2.

### Summary of models and their key emphases

| Model | Key Features | Used In |
|-------|-------------|---------|
| `defaultWeights` | AdjEM (27%), CompRank (12%), four factors | Power Rankings, Standard bracket |
| `defensiveWeights` | AdjD (30%), Opp_eFG% (15%), Opp_TO% (14%) | Defensive Rankings |
| `offensiveWeights` | AdjO (30%), eFG% (18%), PPP_Off (12%) | Offensive Rankings |
| `momentumWeights` | Last_10 (35%), CloseGame (20%), AdjEM (15%) | Momentum Rankings |
| `giantKillerWeights` | Opp_eFG% (18%), Opp_TO% (17%), AdjEM (15%) | Giant Killer Rankings (seed 6+) |
| `cinderellaWeights` | SeedMismatch (25%), AdjD (18%), Opp_TO% (15%) | Cinderella Rankings (seed 9+) |
| `favoritesWeights` | AdjEM (40%), Barthag (25%), CompRank (20%) | Favorites bracket strategy |
| `analyticsWeights` | AdjEM (35%), Barthag (25%), AdjO/AdjD (30%) | Analytics bracket strategy |
| `experienceWeights` | TournamentReadiness (30%), AdjEM (25%), CloseGame (20%) | Experience bracket strategy |

---

## 6. Conference Multipliers: `models/conference_weights.json`

```json
{
  "SEC": 1.00,
  "Big12": 1.00,
  "ACC": 0.99,
  "B10": 0.98,
  "BE": 0.97,
  "_P12_note": "Pac-12 dissolved before 2024-25. Former members now in B10, Big12, ACC, or WCC.",
  "AAC": 0.91,
  "MWC": 0.90,
  "WCC": 0.89,
  "A10": 0.88,
  "MVC": 0.87,
  "MAC": 0.85,
  "CUSA": 0.84,
  "SBC": 0.83,
  "Horizon": 0.83,
  "CAA": 0.82,
  "WAC": 0.82,
  "OVC": 0.80,
  "SoCon": 0.80,
  "MAAC": 0.79,
  "NEC": 0.78,
  "Patriot": 0.78,
  "BSky": 0.77,
  "SWAC": 0.76,
  "MEAC": 0.75,
  "AEC": 0.78,
  "Summit": 0.82,
  "Unknown": 0.85
}
```

**Important:** These multipliers are a secondary adjustment. The primary conference correction is already embedded in AdjEM (Torvik's model solves cross-conference comparison simultaneously). These multipliers provide a residual correction only. The pipeline uses `max(computed_CSI, conf_weight_override)` — whichever is more conservative — when `Conf_Strength_Weight` is provided in the team row.

---

## 7. Output: Ranking CSV Schema

All 6 ranking CSVs share this column structure (in order):

```
Rank, Team, Seed, Conference, Record, PowerScore, [ModelScore],
AdjEM, AdjO, AdjD, Barthag, eFG%, Opp_eFG%, TO%, Opp_TO%,
OR%, DR%, FTR, FT%, SOS, Adj_T, WAB, Torvik_Rank,
NET_Rank, CompRank, AP_Poll_Rank, Coach_Tourney_Experience,
Program_Prestige, Last_10_Games_Metric, Luck,
CinderellaScore, CinderellaAlertLevel, SeedMismatch,
FraudScore, FraudLevel,
Consistency_Score, Volatility_Score,
CSI, CSI_multiplier, Strengths,
OverrideActive
```

- `[ModelScore]` is the model-specific score column name (e.g., `DefensiveScore` for defensive rankings)
- `CinderellaScore` and `CinderellaAlertLevel` are blank for seeds 1–8
- `FraudScore` and `FraudLevel` are blank for seeds 7–16
- `OverrideActive` is `1` if team has an entry in `overrides.json`, else `0`

---

## 8. Output: Simulation Results JSON

```json
{
  "year": 2026,
  "n_simulations": 10000,
  "random_seed": 42,
  "results": {
    "Duke": {
      "R64": 0.981,
      "R32": 0.856,
      "S16": 0.712,
      "E8": 0.534,
      "F4": 0.387,
      "Championship": 0.241,
      "Champion": 0.162
    }
  },
  "modal_bracket": {
    "East": {
      "R64": [{"winner": "Duke", "prob": 0.981}]
    }
  }
}
```

---

## 9. Output: Bracket Strategy JSON

```json
{
  "strategy": "cinderella",
  "description": "Maximizes Cinderella upsets based on seed mismatch and defensive profile",
  "champion": "San Diego State",
  "final_four": ["San Diego State", "Tennessee", "Duke", "Arizona"],
  "rounds": {
    "East": {
      "R64": [
        {
          "higher_seed_team": "Duke",
          "lower_seed_team": "UTEP",
          "higher_seed_seed": 1,
          "lower_seed_seed": 16,
          "predicted_winner": "Duke",
          "win_probability": 0.981,
          "is_upset": false,
          "upset_flag": null,
          "fraud_flag": null,
          "cinderella_flag": null
        }
      ]
    }
  }
}
```

---

## 10. Output: Matchup Summary JSON (`bracket_matchup_verdicts.json`)

Pre-computed verdict for every possible tournament matchup. Used by the UI — no math runs at render time.

```json
{
  "matchups": [
    {
      "region": "East",
      "round": "R64",
      "slot": 1,
      "team_a": {"name": "Duke", "seed": 1, "power_score": 89.4, "adjEM": 29.1, "fraud_score": 0.12, "fraud_level": ""},
      "team_b": {"name": "UMBC", "seed": 16, "power_score": 41.2, "adjEM": -2.1, "cinderella_score": 0.04, "cinderella_level": ""},
      "win_prob_a": 0.97,
      "predicted_spread": 18.3,
      "verdict": "LOCK",
      "verdict_icon": "🔒",
      "verdict_color": "#1a7f37",
      "pick": "Duke",
      "pick_strength": "STRONG",
      "historical_upset_rate": 0.0125,
      "models_agreeing": 8,
      "volatility_flag": false
    }
  ]
}
```

---

## 11. Column Name Alias Map

The pipeline's `normalize_aliases()` function maps these alternate column names to canonical names:

| Alias | Canonical Name |
|-------|---------------|
| `Adj OE` | `AdjO` |
| `Adj DE` | `AdjD` |
| `AdjOE` | `AdjO` |
| `AdjDE` | `AdjD` |
| `eFG D.` | `Opp_eFG%` |
| `Opp eFG%` | `Opp_eFG%` |
| `TOV%` | `TO%` |
| `TOV% D` | `Opp_TO%` |
| `O Reb%` | `OR%` |
| `D Reb%` | `DR%` |
| `FT Rate` | `FTR` |
| `FT Rate D` | `Opp_FTR` |
| `3P % D.` | `3P_%_D` |
| `2P % D.` | `2P_%_D` |
| `Raw T` | `Raw_T` |
| `Adj. T` | `Adj_T` |
| `PPP Off.` | `PPP_Off` |
| `PPP Def.` | `PPP_Def` |
| `Elite SOS` | `Elite_SOS` |
| `Avg Hgt.` | `Avg_Hgt` |
| `Eff. Hgt.` | `Eff_Hgt` |
| `T_Rank_Early` | `TRank_Early` |
| `T_Rank` | `Torvik_Rank` |
| `wAB` | `WAB` |

---

## 12. Data Completeness Requirements by Run Mode

| Column | Rankings-only | Full simulation | Notes |
|--------|--------------|-----------------|-------|
| Team | ✅ Required | ✅ Required | |
| AdjO, AdjD | ✅ Required | ✅ Required | |
| Barthag | ✅ Required | ✅ Required | |
| eFG%, Opp_eFG% | ✅ Required | ✅ Required | |
| TO%, Opp_TO% | ✅ Required | ✅ Required | |
| OR%, DR% | ✅ Required | ✅ Required | DR% computed if missing |
| SOS | ✅ Required | ✅ Required | |
| Adj_T | ✅ Required | ✅ Required | |
| WAB | ⚪ Optional | ⚪ Optional | Strong signal, include if available |
| Seed | ⚪ Optional | ✅ Required | Required for Cinderella/Fraud scores |
| NET_Rank | ⚪ Optional | ⚪ Optional | Auto-fetched from ESPN |
| Torvik_Rank | ⚪ Optional | ⚪ Optional | |
| Luck | ⚪ Optional | ⚪ Optional | Auto-computed as `WinPct − Barthag` proxy if absent — never null after ingestion |
| AP_Poll_Rank | ⚪ Optional | ⚪ Optional | Auto-fetched by fetch_data.py |
| Coach_Tourney_Experience | ⚪ Optional | ⚪ Optional | From coach_scores.json |
| Program_Prestige | ⚪ Optional | ⚪ Optional | Auto-applied from lookup table |
| All other Tier-3/4 | ⚪ Optional | ⚪ Optional | Defaults applied if missing |
| bracket_input.json | ❌ Not needed | ✅ Required | |
| coach_scores.json | ⚪ Optional | ⚪ Optional | Defaults to 3 for unlisted coaches |