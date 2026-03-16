# March Mathness — Algorithm Instructions

This document describes the complete prediction algorithm calibrated to the research audit findings and the data fields available in `teams_input.csv`. Every formula references only columns that exist in the input file. Nothing here requires data we cannot obtain.

---

## 1) Available Data Fields

The input CSV contains 51 columns per team (68 teams total). These are grouped by purpose:

**Identity:** Team, Conference, Record, Wins, Games, Seed

**Efficiency core (opponent-adjusted, from Barttorvik/KenPom):**
AdjO, AdjD, AdjEM, Barthag, Adj_T

**Four factors (offense):** eFG%, TO%, OR%, FTR, FT%, 2P%, 3P%, 3P_Rate, Ast_%

**Four factors (defense):** Opp_eFG%, Opp_TO%, DR%, Opp_OR%, Opp_FTR, 2P_%_D, 3P_%_D, 3P_Rate_D, Op_Ast_%, Blk_%, Blked_%

**Strength of schedule and resume:** SOS, Elite_SOS, WAB, Quad1_Wins

**Rankings (multi-system):** Torvik_Rank, NET_Rank, Massey_Rank, CompRank, AP_Poll_Rank

**Trajectory:** TRank_Early, RankTrajectory

**Situational:** Luck, Last_10_Games_Metric, Conf_Tourney_Champion, Won_Play_In

**Scouting:** Coach_Tourney_Experience, Program_Prestige, Star_Player_Index, Exp, Bench_Minutes_Pct

**Fields we do NOT have** (and the algorithm must not reference): Avg_Hgt, Eff_Hgt, Home/Away/Neutral AdjEM splits, road win percentage, returning tournament minutes.

---

## 2) Key Research-Driven Calibration Changes

These changes are implemented throughout the algorithm based on the full research audit:

**AdjEM weight raised to ~40%.** AdjEM is the single strongest predictor of tournament outcomes across all studies (Kaggle gold solutions, COOPER, FormulaBot 2024 analysis). The old 29% weight significantly undervalued it.

**Barthag weight reduced to ~5%.** Barthag is derived from AdjO and AdjD via a Pythagorean formula (exponent 11.5 for Torvik). Including both AdjEM and Barthag at high weights is confirmed double-counting. The combined efficiency bucket (AdjEM + Barthag) should total 45–50% of the power score, with AdjEM dominant.

**Conference Strength Index multiplier REMOVED.** KenPom, Torvik, and BPI already solve for opponent-adjusted efficiency across all 353 D-I teams simultaneously. Applying an external CSI multiplier to efficiency-derived scores creates confirmed double-counting (Ben Wieland 2024 simulation study, KenPom's own acknowledgment). All model scores are now computed WITHOUT a CSI multiplier.

**Historical conference fraud penalties REMOVED.** The Big Ten penalty (0.65), ACC penalty (0.25), and all other fixed conference penalties are eliminated. Harvard Sports Analysis Collective (2015) found no conference showed statistically significant seeding bias at the 5% level. Conference PASE values show extreme year-to-year variance that makes fixed penalties meaningless.

**Replacement: Seed-vs-metric discrepancy.** Instead of conference penalties, the algorithm uses the gap between a team's NCAA seed and their CompRank implied seed. A 3-seed ranked 22nd on CompRank is more predictive of underperformance than "they're from Conference X."

**Defense weighted slightly over offense (55/45).** Champions from 2008–2017 averaged 3rd-best defense vs 9th-best offense. Balanced teams significantly outperform unbalanced ones (Harvard PASE analysis). Teams where the gap between AdjO rank and AdjD rank exceeds 30 positions are flagged.

**CSI multiplier and conference penalties must be removed from the app code.** The existing codebase computes a Conference Strength Index (WIN50 + non-conference calibration) and multiplies ALL model scores by a CSI_multiplier clipped to [0.75, 1.05]. This must be disabled. Specifically:
- Remove or bypass the CSI computation in Section 4 of the old math (WIN50 rating, non-conference calibration, CSI_multiplier calculation)
- In the scoring engine, change `final_score = round(score_0_100 * CSI_multiplier, 1)` to simply `final_score = round(score_0_100, 1)` — no multiplication
- Remove the `conference_weights.json` override interaction (Section 4.4 of old math)
- Remove the conference fraud prior component from the Fraud score (old Section 8.1 component 7 with B10:0.65, ACC:0.25, etc.)
- Remove the `Conf_Strength_Weight` column from the input schema — it is no longer used
- The `Conference` column is retained for display/grouping purposes only, not for scoring

To compensate for the loss of CSI's schedule-quality signal, SOS_inv weight in the PowerScore is increased from 0.04 to 0.06. This provides proper schedule-quality discrimination through a normalized feature rather than a blunt multiplier. The 0.02 increase is offset by reducing CompRank_inv (0.07→0.06) and NET_Rank_inv (0.03→0.02), since CompRank already incorporates both of those individual rankings.

**Exp integrated into experience-sensitive components.** Generic class-year experience shows near-zero correlation with tournament overperformance (R² = 0.0002, Harvard 2019). However, Exp (minutes-weighted experience from Barttorvik) captures team maturity more meaningfully and is used as a tiebreaker/modifier in Cinderella and Fraud scoring.

**Bench_Minutes_Pct used as depth indicator.** Teams with low bench minutes indicate star-dependent rotations — a vulnerability flag in Fraud detection and a variance amplifier in tournament play.

---

## 3) Data Ingestion and Base Feature Construction

### 3.1 Record parsing

If `Record` exists and `Wins`/`Games` are missing:
- `Wins = int(Record.split("-")[0])`
- `Games = Wins + int(Record.split("-")[1])`

### 3.2 Efficiency construction

- `AdjEM = AdjO - AdjD` (verify/recompute if present)
- `PPP_Off = AdjO / 100`
- `PPP_Def = AdjD / 100`

### 3.3 Luck

If `Luck` is missing:
- `WinPct = Wins / Games`
- `Luck = WinPct - Barthag`

### 3.4 Defaults for missing values

- `Seed=10`, `Conference="Unknown"`
- `Star_Player_Index=5.0`
- `Last_10_Games_Metric=0.65`
- `Massey_Rank=150`
- `Elite_SOS=10.0`
- `Quad1_Wins=3`
- `AP_Poll_Rank=26`
- `Coach_Tourney_Experience=3.0`
- `Program_Prestige=2.0`
- `WAB=2.0`
- `Conf_Tourney_Champion=0`
- `Won_Play_In=0`
- `Exp=2.0` (neutral default)
- `Bench_Minutes_Pct=15.0` (neutral default)

### 3.5 Composite rank (CompRank)

System weights:
- `NET_Rank: 0.45`
- `Massey_Rank: 0.30`
- `Torvik_Rank: 0.25`

`CompRank = weighted_sum / weight_total` using only present ranks.

Confidence: 0 systems → 0.0, 1 → 0.5, 2 → 0.75, 3 → 1.0

### 3.6 Conference tournament champion bonus

If `Conf_Tourney_Champion == 1`:
- `Last_10_Games_Metric = min(Last_10_Games_Metric + 0.05, 1.0)`

---

## 4) Normalization Layer

All model scoring uses features normalized to `[0, 1]`.

### 4.1 Core functions

- Higher-is-better: `normalize(v, min, max) = clip((v - min) / (max - min), 0, 1)`
- Lower-is-better: `normalize_inverse(v, min, max) = clip((max - v) / (max - min), 0, 1)`
- Missing/NaN → `0.5` (neutral)

### 4.2 Feature ranges and directions

| Feature | Min | Max | Direction |
|---------|-----|-----|-----------|
| AdjEM | -20 | 40 | higher |
| AdjO | 95 | 130 | higher |
| AdjD | 80 | 125 | inverse (lower is better) |
| Barthag | 0.20 | 1.00 | higher |
| eFG% | 44 | 62 | higher |
| Opp_eFG% | 40 | 60 | inverse |
| TO% | 10 | 25 | inverse |
| Opp_TO% | 10 | 25 | higher |
| OR% | 18 | 45 | higher |
| DR% | 60 | 86 | higher |
| FTR | 18 | 55 | higher |
| Opp_FTR | 18 | 50 | inverse |
| FT% | 62 | 85 | higher |
| 3P% | 28 | 42 | higher |
| 3P_%_D | 25 | 40 | inverse |
| 2P% | 44 | 62 | higher |
| 2P_%_D | 40 | 58 | inverse |
| 3P_Rate | 25 | 55 | neutral (midpoint = best) |
| 3P_Rate_D | 28 | 52 | inverse |
| Ast_% | 38 | 70 | higher |
| Op_Ast_% | 35 | 65 | inverse |
| Blk_% | 4 | 20 | higher |
| Blked_% | 2 | 14 | inverse |
| SOS | 1 | 365 | inverse |
| CompRank | 1 | 365 | inverse |
| Torvik_Rank | 1 | 365 | inverse |
| Massey_Rank | 1 | 365 | inverse |
| NET_Rank | 1 | 365 | inverse |
| Last_10_Games_Metric | 0.3 | 1.0 | higher |
| Star_Player_Index | 1 | 10 | higher |
| Quad1_Wins | 0 | 15 | higher |
| Elite_SOS | 0 | 50 | higher |
| PPP_Off | 0.88 | 1.30 | higher |
| PPP_Def | 0.80 | 1.22 | inverse |
| Adj_T | 60 | 80 | neutral |
| RankTrajectory | -30 | 30 | higher |
| WinPct | 0 | 1 | higher |
| Coach_Tourney_Experience | 1 | 10 | higher |
| WAB | -13 | 14 | higher |
| Exp | 0.5 | 3.0 | higher |
| Bench_Minutes_Pct | 5 | 30 | neutral (context-dependent) |

---

## 5) Derived Features

All derived features are computed from normalized inputs.

### 5.1 Rank divergence

Primary path (from raw ranks):
- `raw_divergence = Torvik_Rank - NET_Rank`
- `RankDivergence = clip((raw_divergence + 40) / 80, 0, 1)`

Higher divergence → committee signal stronger than efficiency signal. `RankDivergence_inv = 1 - RankDivergence`

### 5.2 Composite derived features

- `CloseGame = (Last_10_Games_Metric + WinPct + 0.5*FT% + 0.5*TO%_inv) / 3.0`
- `ThreePtConsistency = 0.65*3P% + 0.35*3P_%_D_inv`
- `BallMovement = 0.60*Ast_% + 0.40*Op_Ast_%_inv`
- `Physicality = 0.35*OR% + 0.30*Blk_% + 0.35*FTR`
- `InsideScoring = 0.50*2P% + 0.30*OR% + 0.20*FTR`
- `InteriorDefense = 0.45*2P_%_D_inv + 0.35*Blk_% + 0.20*DR%`
- `TournamentReadiness = 0.60*Barthag + 0.40*Quad1_Wins`
- `DefensivePlaymaking = 0.55*Opp_TO% + 0.30*Blk_% + 0.15*Blked_%_inv`
- `NETMomentum = RankTrajectory` (already normalized)

### 5.3 Consistency and volatility

- `Consistency_Score = normalize_inverse(abs(Last_10 - WinPct), 0, 0.4)`
- `Volatility_Score = 0.6*3P_Rate_norm + 0.4*(1 - Consistency_Score)`
- `MomentumDelta = Last_10_Games_Metric - WinPct` (raw domain)

### 5.4 Balance flag

- `AdjO_rank` and `AdjD_rank` from their respective positions among 68 teams
- `Balance_Gap = abs(AdjO_rank - AdjD_rank)`
- Flag if `Balance_Gap > 30` (every champion from 2008–2017 stayed within this threshold)

---

## 6) Seed Mismatch and Implied Seed

Seed-to-rank ranges:
- 1:(1,5), 2:(5,10), 3:(10,16), 4:(16,26), 5:(26,36), 6:(36,50)
- 7:(50,65), 8:(65,80), 9:(80,100), 10:(100,125), 11:(125,155)
- 12:(155,185), 13:(185,225), 14:(225,275), 15:(275,330), 16:(330,365)

`implied_seed(CompRank)` returns the seed bucket.

- `SeedMismatch = clip((actual_seed - implied_seed) / 10, 0, 1)`

Positive values indicate underseeded teams (analytically better than their bracket seed suggests).

---

## 7) Model Scoring Engine

### 7.1 Generic scoring

For a model with weights `{feature: w}`:
1. Look up each feature's normalized or derived value
2. Missing features → 0.5 (neutral)
3. `score = 100 * sum(weight_i * value_i)`

**NO CSI multiplier is applied.** This is the critical change from previous versions. Scores are pure weighted sums.

### 7.2 Weight sets

#### PowerScore (default)

| Feature | Weight | Rationale |
|---------|--------|-----------|
| AdjEM | 0.40 | Raised from 0.29 — strongest single predictor |
| Barthag | 0.05 | Reduced from separate high weight — redundant with AdjEM |
| CompRank_inv | 0.06 | Multi-system consensus (reduced from 0.07 — incorporated into SOS shift) |
| NET_Rank_inv | 0.02 | Committee signal (reduced from 0.03 — CompRank already includes NET) |
| Massey_Rank_inv | 0.02 | Independent validation |
| SOS_inv | 0.06 | Increased from 0.04 to compensate for CSI removal — carries schedule-quality signal |
| eFG% | 0.06 | Shooting efficiency |
| Opp_eFG%_inv | 0.05 | Defensive shooting suppression |
| Opp_TO% | 0.05 | Turnover creation |
| TO%_inv | 0.03 | Ball security |
| OR% | 0.03 | Second chances |
| DR% | 0.02 | Defensive rebounding |
| FTR | 0.02 | Getting to the line |
| FT% | 0.02 | Converting free throws |
| Last_10_Games_Metric | 0.04 | Recent form |
| Quad1_Wins | 0.03 | Resume quality |
| Star_Player_Index | 0.02 | Star talent |
| Coach_Tourney_Experience | 0.02 | March pedigree |
| **Total** | **1.00** | |

#### Defensive model

| Feature | Weight |
|---------|--------|
| AdjD_inv | 0.30 |
| Opp_eFG%_inv | 0.15 |
| Opp_TO% | 0.14 |
| DR% | 0.10 |
| Blk_% | 0.08 |
| InteriorDefense | 0.07 |
| DefensivePlaymaking | 0.06 |
| Opp_FTR_inv | 0.04 |
| 3P_%_D_inv | 0.03 |
| 2P_%_D_inv | 0.03 |

#### Offensive model

| Feature | Weight |
|---------|--------|
| AdjO | 0.30 |
| eFG% | 0.18 |
| PPP_Off | 0.12 |
| InsideScoring | 0.10 |
| 3P% | 0.08 |
| OR% | 0.07 |
| BallMovement | 0.06 |
| FTR | 0.05 |
| FT% | 0.04 |

#### Momentum model

| Feature | Weight |
|---------|--------|
| Last_10_Games_Metric | 0.35 |
| CloseGame | 0.20 |
| AdjEM | 0.15 |
| Opp_TO% | 0.10 |
| Barthag | 0.07 |
| FT% | 0.05 |
| TournamentReadiness | 0.05 |
| NETMomentum | 0.03 |

#### Giant Killer model

| Feature | Weight |
|---------|--------|
| Opp_eFG%_inv | 0.18 |
| Opp_TO% | 0.17 |
| AdjEM | 0.17 |
| CloseGame | 0.12 |
| DefensivePlaymaking | 0.10 |
| Barthag | 0.09 |
| FT% | 0.08 |
| Quad1_Wins | 0.06 |
| InteriorDefense | 0.03 |

#### Cinderella Tournament model (seeds 9–16 only)

| Feature | Weight | Rationale |
|---------|--------|-----------|
| SeedMismatch_norm | 0.25 | Underseeded by analytics — highest signal |
| AdjD_inv | 0.18 | Defense relative to seed |
| Opp_TO% | 0.12 | Turnover margin — key Cinderella trait |
| Barthag | 0.10 | Overall quality floor |
| Adj_T_inv | 0.08 | Slow tempo controls variance (9/11 upset victims were slow-tempo favorites) |
| OR% | 0.06 | Rebounding — physical teams don't suffer upsets |
| Coach_Tourney_Experience | 0.05 | Coach March pedigree is real and measurable |
| Quad1_Wins | 0.05 | Proven against top competition |
| CloseGame | 0.04 | Clutch performance |
| Exp | 0.02 | Team maturity (minutes-weighted) |
| WAB | 0.02 | Wins above bubble |
| RankDivergence_inv | 0.03 | Analytics value signal |

#### Favorites model

| Feature | Weight |
|---------|--------|
| AdjEM | 0.40 |
| Barthag | 0.25 |
| CompRank_inv | 0.15 |
| NET_Rank_inv | 0.03 |
| Massey_Rank_inv | 0.02 |
| eFG% | 0.08 |
| AdjD_inv | 0.07 |

#### Analytics model

| Feature | Weight |
|---------|--------|
| AdjEM | 0.35 |
| Barthag | 0.25 |
| AdjO | 0.15 |
| AdjD_inv | 0.15 |
| SOS_inv | 0.10 |

---

## 8) Cinderella Score (seeds 9–16 only)

If `Seed < 9`: CinderellaScore = 0, CinderellaAlertLevel = "–"

### 8.1 Components

1. **Seed mismatch** — `seed_mis = SeedMismatch` (from Section 6)

2. **Defense signal** (from Torvik_Rank):
   - ≤40 → 1.0
   - ≤80 → 0.65
   - ≤120 → 0.35
   - else → 0.0
   - If `CompRank ≤ 40` and signal < 0.65, promote to 0.65

3. **Turnover margin signal** — `tov_margin = 0.6*Opp_TO% + 0.4*TO%_inv`

4. **Tempo signal** — `tempo_score = normalize_inverse(Adj_T, 60, 80)` (slow tempo = higher score. Research: historically, mid-major teams that make long tournament runs control tempo)

5. **Rebounding** — `reb_score = OR%` (offensive rebounding percentage was a top feature in the Odds Gods LightGBM model)

6. **Rank value signal** — `rank_value = 1 - RankDivergence`

### 8.2 Composite

`CinderellaScore = 0.35*seed_mis + 0.28*defense_signal + 0.19*tov_margin + 0.08*tempo_score + 0.07*reb_score + 0.03*rank_value`

### 8.3 Alert levels

- ≥0.55 → HIGH
- ≥0.40 → WATCH
- else → NONE

---

## 9) Fraud Score (seeds 1–6 only)

If `Seed > 6`: FraudScore = 0, FraudLevel = "–"

### 9.1 Components

1. **Seed deviation** — `overseeded_gap = implied_seed(CompRank) - Seed`, `seed_deviation = clip(overseeded_gap / 4, 0, 1)`. This replaces the old conference-based approach. A 3-seed ranked 22nd on CompRank is the strongest fraud signal.

2. **Offense-defense imbalance** — `imbalance = max(0, AdjO_norm - AdjD_inv_norm)`, `imbalance_score = min(1, imbalance / 0.35)`. If `Adj_T < 65` and `Seed ≤ 4`: add 0.10 (capped at 1). Research: offense-focused teams underperform by 0.15 wins vs seed expectations.

3. **Form collapse** — `form_drop = max(0, WinPct - Last_10_Games_Metric)`, `form_collapse = min(1, form_drop / 0.25)`. Late-season form decline is an empirically validated fraud signal (Odds Gods model).

4. **Luck** — `luck_score = normalize_value(Luck, -0.05, 0.10)`

5. **Variance style** — `variance = 0.6*3P_Rate_norm + 0.4*(1 - Consistency_Score)`. Note: 3-point dependency is a variance flag, NOT a fraud signal (R² ≈ 0.001). It amplifies uncertainty rather than predicting failure.

6. **Star dependence** — `star_norm = normalize(Star_Player_Index, 1, 10)`, `team_depth = normalize(AdjEM, -20, 40)`, `dependence = clip(star_norm - 0.7*team_depth, 0, 1)`. Modified by Bench_Minutes_Pct: if `Bench_Minutes_Pct < 10`, add 0.10 to dependence (capped at 1) — thin rotations are vulnerable.

7. **Defensive FTR allowed** — `ftr_allowed = normalize_value(Opp_FTR, 18, 50)`. Teams allowing high free throw rates become increasingly vulnerable as tournament games tighten. This was flagged as an underused fraud signal in the research.

8. **Rank divergence** — from Section 5.1

### 9.2 Composite

`FraudScore = 0.25*seed_deviation + 0.20*imbalance_score + 0.14*form_collapse + 0.12*luck_score + 0.10*variance + 0.05*dependence + 0.06*ftr_allowed + 0.08*RankDivergence`

**Note:** The old `0.03*conference_penalty` component is REMOVED. No fixed conference penalties are used.

### 9.3 Fraud levels

- ≥0.60 → HIGH
- ≥0.40 → MEDIUM
- ≥0.25 → LOW
- else → NONE

---

## 10) Win Probability Engine

All production probabilities are clipped to `[0.03, 0.97]`.

### 10.1 Predicted spread

- `tempo_avg = (Adj_T_a + Adj_T_b) / 2`
- `predicted_spread = (AdjEM_a - AdjEM_b) * tempo_avg / 100`

### 10.2 Normal CDF model (with fat-tail note)

- `p_normal = Φ(predicted_spread / 11.0)` where 11 is the standard deviation

Research note: COOPER (Nate Silver, 2026) uses a Student's t distribution with 8–10 degrees of freedom instead of a pure normal CDF, providing better calibration for outlier matchups. A normal distribution underestimates upset probability in extreme mismatches. If implementing Student's t: `p_t = T_cdf(predicted_spread / 11.0, df=9)`.

### 10.3 Elo-style logistic model

- `diff = AdjEM_a - AdjEM_b`
- `p_elo = 1 / (1 + 10^(-diff * 30.464 / 400))`

### 10.4 Blend

- `p_blended = 0.60*p_normal + 0.40*p_elo`

The 60/40 blend is defensible and mirrors industry practice. Tournament-specific games may benefit from adjusting toward 50/50 since tournament conditions (neutral courts, concentrated timeframe) make the Elo component relatively more accurate.

### 10.5 Era seed prior blend

Underdog priors for close seed matchups:
- (6,11): 0.52
- (7,10): 0.41
- (8,9): 0.625

`p = (1 - prior_weight) * model + prior_weight * prior` with default `prior_weight = 0.15`

### 10.6 Play-in boost (round 1 only)

If only one side has `Won_Play_In == 1`:
- Play-in winner gets `+0.03` win probability

### 10.7 Historical upset priors

- (1,16): 0.0125
- (2,15): 0.069
- (3,14): 0.144
- (4,13): 0.206
- (5,12): 0.356
- (6,11): 0.388
- (7,10): 0.375
- (8,9): 0.519

The 12-5 matchup is the sweet spot for upsets at ~35.6% historical rate.

---

## 11) Strategy Brackets

Strategies: `standard`, `favorites`, `upsets`, `analytics`, `cinderella`, `defensive`, `momentum`

Each has `model_blends` (weights over model scores), `upset_threshold`, and optional `cinderella_boost`.

### 11.1 Strategy matchup probability

1. `base_prob = production_win_probability(A, B)`
2. Blended model score per team: `score_X = sum(weight_m * model_score_X[m])`
3. Ratio adjustment: `ratio_adj = (score_A / (score_A + score_B) - 0.5) * 0.20`, clipped to `[-0.10, +0.10]`
4. `adjusted = clip(base_prob + ratio_adj, 0.03, 0.97)`
5. Cinderella boost: if underdog has `CinderellaScore > 0.50`, reduce favorite probability by `cinderella_boost`
6. Fraud adjustment: for strategies `{upsets, cinderella, analytics}`, reduce favorite win probability by `0.08 * FraudScore`

### 11.2 Upset decision

- Upset if `(1 - fav_prob) > upset_threshold`
- Hard guard: 16-seed vs 1-seed never upsets if threshold > 0.35

---

## 12) Monte Carlo Simulation

`simulate_bracket(bracket, win_prob_fn, n_sims=10000, seed=42)`

For each simulation:
- Run all 4 regions through R64 → R32 → S16 → E8
- Semi 1: region_winners[0] vs [1]
- Semi 2: region_winners[2] vs [3]
- Championship between semifinal winners

Probabilities: `P(round) = count_reached / n_sims`

---

## 13) Coach Tournament Experience Scoring

Scores follow this rubric (additive, capped at 10):

| Criterion | Points |
|-----------|--------|
| Final Four 2+ times | +3 |
| Won national championship | +2 |
| 15+ NCAA Tournament appearances | +2 |
| Sweet 16 3+ times | +2 |
| 500+ career wins | +1 |

Default for unlisted coaches: 3.0

These scores are provided in the `Coach_Tourney_Experience` column. Key validated scores from Barttorvik PASE data:

- Tom Izzo (Michigan St.): 10 — PASE +13.2, 24 trips, 53-23
- Bill Self (Kansas): 10 — PASE +2.5, 25 trips, 56-23
- John Calipari (Arkansas): 10 — PASE +8.6, 19 trips, 48-18
- Rick Pitino (St. John's): 10 — PASE +1.9, 16 trips, 29-15
- Dan Hurley (Connecticut): 9 — PASE +4.2, 7 trips, 15-5
- Mark Few (Gonzaga): 8 — PASE +3.4, 25 trips, 44-25
- Kelvin Sampson (Houston): 8 — PASE -1.8, 14 trips, 29-14
- Todd Golden (Florida): 7 — PASE +0.9, 3 trips (but includes 2025 championship)
- Tubby Smith (High Point): 6 — PASE -2.1, 12 trips, 15-12

Notable negative PASE coaches (fraud signal amplifiers):
- Tony Bennett (Virginia): PASE -7.1 despite 11 trips
- Jamie Dixon (TCU): PASE -7.1 despite 15 trips
- Rick Barnes (Tennessee): PASE -5.1 despite 22 trips
- Matt Painter (Purdue): PASE -2.5 despite 17 trips
- Randy Bennett (Saint Mary's): PASE -4.5 despite 11 trips

---

## 14) What Makes Interesting Picks (Research Summary)

These findings inform the Cinderella and Fraud algorithms:

**Tempo is the sleeper variable.** 9 of 11 first-round upset victims (2021–2023) ranked outside the top 100 in adjusted tempo. Slow-tempo favorites compress scoring variance and give underdogs a fighting chance. This is captured by `Adj_T_inv` in the Cinderella model.

**Turnover margin differentiates upsets.** In the FDU-over-Purdue 16-1 upset (2023), Purdue turned it over 16 times. `Opp_TO%` and `TO%_inv` are weighted heavily in Cinderella and Giant Killer models.

**Offensive rebounding predicts deep runs.** Florida's 2025 championship was built on being 5th nationally in OR%. UConn 2023 was anchored by glass dominance. `OR%` is in both Cinderella and Physicality derived features.

**Free throw rate allowed (Opp_FTR) is an underused fraud signal.** Teams allowing high FTR become vulnerable as tournament games tighten. Now explicitly included in Fraud scoring.

**3-point dependency is a variance flag, not a fraud flag.** R² ≈ 0.001 for 3PT rate vs tournament underperformance. But in actual upsets, there's a ~7-point swing in 3PT% from season averages. Captured by `Volatility_Score`.

**Experience is nuanced.** Generic class-year experience: R² = 0.0002 (Harvard 2019). But minutes-weighted experience (our `Exp` field) captures team maturity more meaningfully. Used as modifier, not primary driver.

---

## 15) Strength Labels

Rule-based thresholds for narrative output:

- `eFG% ≥ 56` → "Elite shooting efficiency"
- `3P% ≥ 38` → "Elite 3-point shooting"
- `AdjO ≥ 120` → "Elite offense"
- `AdjD ≤ 92` → "Elite defense"
- `Opp_TO% ≥ 22` → "Forces turnovers"
- `Last_10_Games_Metric ≥ 0.85` → "Red-hot form"
- `OR% ≥ 38` → "Dominant on the glass"
- `FT% ≥ 75` → "Clutch free throw shooting"

Return first 4 matching labels per team.

---

## 16) End-to-End Pipeline Order

1. Load teams → aliases, records, AdjEM/PPP, Luck, defaults, rank features, conf champ bonus, overrides
2. Normalize all features (including Exp, Bench_Minutes_Pct)
3. Compute derived features (CloseGame, Physicality, BallMovement, etc.)
4. Add Consistency_Score, Volatility_Score, MomentumDelta, Balance_Gap flag
5. Compute SeedMismatch, inject SeedMismatch_norm
6. **SKIP CSI computation entirely** — do not compute WIN50, non-conference calibration, or CSI_multiplier
7. Score all ranking models as **pure weighted sums** — `final_score = round(score_0_100, 1)` with NO CSI multiplication
8. Compute Cinderella/Fraud scores and text labels (no conference fraud priors)
9. Build bracket teams with stats
10. Probability model (blended CDF + Elo)
11. Monte Carlo simulation and modal bracket
12. Strategy deterministic brackets with upset logic
13. Verdict file + pick sheet + CSV/JSON/HTML outputs

---

## 17) Required App Code Changes (vs. old math.md)

This section summarizes every change the app code must make relative to the previous implementation documented in the old math.md:

**CSI removal (highest priority):**
- Delete or bypass the entire CSI computation block (old Section 4: WIN50, non-conference calibration, CSI_multiplier)
- In `score_team()` or equivalent: remove `* CSI_multiplier` from all model score calculations
- Delete or ignore `models/conference_weights.json` — it is no longer loaded or referenced
- Remove `Conf_Strength_Weight` from the input schema and any column validation

**Fraud score changes:**
- Remove component 7 (conference fraud prior with B10:0.65, ACC:0.25, etc.) — the old `0.03*conference_penalty` weight is eliminated
- Add component 7: defensive FTR allowed (`0.06*ftr_allowed`) — `ftr_allowed = normalize_value(Opp_FTR, 18, 50)`
- Modify component 6 (star dependence): add Bench_Minutes_Pct modifier — if `Bench_Minutes_Pct < 10`, add 0.10 to dependence (capped at 1)
- Reweight composite: `0.25*seed_deviation + 0.20*imbalance + 0.14*form_collapse + 0.12*luck + 0.10*variance + 0.05*dependence + 0.06*ftr_allowed + 0.08*RankDivergence`

**PowerScore weight changes:**
- `AdjEM`: 0.29 → 0.40
- `Barthag`: (was separate high weight) → 0.05
- `CompRank_inv`: 0.07 → 0.06
- `NET_Rank_inv`: 0.03 → 0.02
- `SOS_inv`: (was lower) → 0.06
- All other weights adjusted to sum to 1.00 (see Section 7.2)

**Cinderella score changes:**
- Add `Exp` as a component at 0.02 weight
- Barthag reduced from 0.12 → 0.10

**New input columns:**
- `Exp` (float, 0–3 scale, minutes-weighted experience from Barttorvik)
- `Bench_Minutes_Pct` (float, percentage of total minutes from non-top-7 rotation players)

**Removed input columns:**
- `Conf_Strength_Weight` — no longer used anywhere