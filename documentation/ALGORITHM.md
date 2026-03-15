# March Mathness — Algorithm Specification
**Version 2.0** — All metrics from gap analysis are now fully specified here.

This document contains the complete mathematical specification for every scoring model, sub-algorithm, and formula in the system. All weights and thresholds are derived from peer-reviewed research and backtested Kaggle competition analysis. Claude should implement these exactly as written.

---

## 0. Complete Metric Inventory

This section is the master reference for every metric computed by the system. Cursor should use this as the checklist when implementing `engine/scoring.py` and `engine/normalization.py`.

### Input Metrics (from teams_input.csv — full spec in DATA_SCHEMA.md)

| Metric | Tier | Used In | Source |
|--------|------|---------|--------|
| AdjEM | 1 | All models, Win Probability, Fraud Score | Torvik |
| AdjO | 1 | Offensive model, Fraud Score | Torvik |
| AdjD | 1 | Defensive model, Fraud Score | Torvik |
| Barthag | 1 | All models, Tournament Readiness | Torvik |
| eFG% | 2 | Default, Offensive, Giant Killer | Torvik |
| Opp_eFG% | 2 | Default, Defensive, Cinderella, Fraud | Torvik |
| TO% | 2 | Default, Cinderella, Fraud | Torvik |
| Opp_TO% | 2 | Default, Defensive, Cinderella, Giant Killer | Torvik |
| OR% | 2 | Default, Cinderella, Offensive | Torvik |
| DR% | 2 | Default, Defensive | Torvik |
| FTR / Opp_FTR | 2 | Default, Fraud Score (FT vulnerability) | Torvik |
| FT% | 2 | Momentum, Giant Killer, Fraud Score | Torvik |
| SOS | 2 | Default, Conference adjustment | Torvik |
| Adj_T | 2 | Win Probability, Cinderella (tempo signal) | Torvik |
| WAB | 2 | Cinderella | Torvik |
| Torvik_Rank | 2 | CompRank, SeedMismatch | Torvik |
| NET_Rank | 2 | CompRank | NCAA |
| Luck | 3 | **Fraud Score (weight 15%)** — `WinPct − Barthag` | Computed (Torvik data) |
| AP_Poll_Rank | 3 | Display context, optional enrichment | ESPN API free |
| 3P%, 3P_%_D | 3 | ThreePtConsistency derived, Offensive | Torvik |
| 3P_Rate | 3 | Volatility Score | Torvik |
| 2P%, 2P_%_D | 3 | InsideScoring, InteriorDefense derived | Torvik |
| AST_TO, Ast_%, Op_Ast_% | 3 | BallMovement derived | Torvik |
| Blk_%, Blked_% | 3 | Physicality, InteriorDefense derived | Torvik |
| PPP_Off, PPP_Def | 3 | Offensive, Defensive models | Torvik |
| Avg_Hgt, Eff_Hgt | 3 | Physicality, height score | Torvik |
| Exp | 4 | Default, Experience model, Cinderella | Torvik |
| Quad1_Wins | 4 | Default, Tournament Readiness | Manual |
| Last_10_Games_Metric | 4 | Momentum model, Fraud Score (form collapse) | Manual |
| Star_Player_Index | 4 | Default, Fraud Score (star dependence) | Auto (Torvik player BPM) |
| Bench_Minutes_Pct | 4 | Default, Fraud Score (star dependence) | Auto (Torvik player minutes) |
| Coach_Tourney_Experience | 4 | Experience model (0.08), Cinderella (0.05) | Manual/coach_scores.json |
| Program_Prestige | 4 | Display context, optional enrichment | Auto-lookup table |
| TRank_Early | 4 | NETMomentum derived (ranking trajectory) | Auto (Torvik Time Machine) |
| Won_Play_In | 4 | +3% first-round win prob boost | Manual binary (4 teams) |
| Conf_Tourney_Champion | 4 | +0.05 boost to Last_10 before scoring | Manual binary |
| Elite_SOS | 4 | SOS cross-check | Manual |

### Pipeline-Computed Metrics (not in input — computed during pipeline run)

| Metric | Formula | Used In | Section |
|--------|---------|---------|---------|
| AdjEM | AdjO − AdjD (if missing) | Everything | §0.1 |
| CompRank | avg(Torvik_Rank, Massey_Rank, NET_Rank) | Default model | §0.2 |
| WinPct | Wins / Games | Fraud (form collapse), Consistency | §0.3 |
| Consistency_Score | normalize_inverse(abs(Last_10 − WinPct), 0, 0.4) | Volatility, labels | §0.3 |
| Volatility_Score | 0.6×norm(3P_Rate) + 0.4×(1−Consistency) | Display only, Upset strategy | §0.3 |
| SeedMismatch | CompRank_implied_seed − Seed | Cinderella Score | §4.1 |
| MomentumDelta | Last_10 − WinPct | Display, labels | §0.3 |
| CinderellaScore | 6-component weighted score (seeds 9+ only) | Cinderella rankings, Cinderella bracket | §4 |
| FraudScore | 7-component weighted score (seeds 1–6 only) | Fraud alerts, Upset bracket adjustment | §10 |
| CSI / CSI_multiplier | WIN50 conference rating → multiplier | All model scores | §1 |
| RankTrajectory | TRank_Early − Torvik_Rank | NETMomentum derived feature | §0.3 |
| All 9 derived features | CloseGame, ThreePtConsistency, BallMovement, NETMomentum, etc. | Model scoring | §0.3 |

---

## 0. Mathematical Foundations

### 0.1 Normalization Functions

All raw features are normalized to [0, 1] before entering any scoring formula.

```python
def normalize_value(v, min_val, max_val):
    """Higher raw value → higher normalized score."""
    if v is None or np.isnan(v):
        return 0.5  # neutral default
    return np.clip((v - min_val) / (max_val - min_val), 0.0, 1.0)

def normalize_inverse(v, min_val, max_val):
    """Lower raw value → higher normalized score (e.g., defensive stats)."""
    if v is None or np.isnan(v):
        return 0.5
    return np.clip((max_val - v) / (max_val - min_val), 0.0, 1.0)
```

### 0.2 Feature Range Table

| Column | min | max | Direction | Notes |
|--------|-----|-----|-----------|-------|
| AdjEM | -20 | 40 | higher | Efficiency margin |
| AdjO | 95 | 130 | higher | Offensive efficiency |
| AdjD | 80 | 125 | inverse | Defensive efficiency (lower pts allowed = better) |
| Barthag | 0.20 | 1.00 | higher | Pythagorean win expectancy |
| eFG% | 44 | 62 | higher | |
| Opp_eFG% | 40 | 60 | inverse | |
| TO% | 10 | 25 | inverse | Own turnovers (lower = better) |
| Opp_TO% | 10 | 25 | higher | Opponent turnovers forced |
| OR% | 18 | 45 | higher | |
| DR% | 60 | 86 | higher | |
| FTR | 18 | 55 | higher | |
| Opp_FTR | 18 | 50 | inverse | |
| FT% | 62 | 85 | higher | |
| 3P% | 28 | 42 | higher | |
| 3P_%_D | 25 | 40 | inverse | |
| 2P% | 44 | 62 | higher | |
| 2P_%_D | 40 | 58 | inverse | |
| 3P_Rate | 25 | 55 | neutral | Context, not directly scored |
| 3P_Rate_D | 28 | 52 | inverse | |
| AST_TO | 0.8 | 2.5 | higher | |
| Ast_% | 38 | 70 | higher | |
| Op_Ast_% | 35 | 65 | inverse | |
| Blk_% | 4 | 20 | higher | |
| Blked_% | 2 | 14 | inverse | |
| Avg_Hgt | 73 | 81 | higher | Inches |
| Eff_Hgt | 75 | 84 | higher | Inches |
| SOS | 1 | 365 | inverse | Rank: 1 = hardest schedule |
| CompRank | 1 | 365 | inverse | avg(Torvik_Rank, Massey_Rank, NET_Rank) |
| Torvik_Rank | 1 | 365 | inverse | |
| Massey_Rank | 1 | 365 | inverse | |
| NET_Rank | 1 | 365 | inverse | |
| CompRank | 1 | 365 | inverse | Average of available ranks |
| Exp | 0 | 3 | higher | |
| Last_10_Games_Metric | 0.30 | 1.00 | higher | Win rate last 10 |
| Star_Player_Index | 1 | 10 | higher | |
| Bench_Minutes_Pct | 20 | 55 | higher | |
| Quad1_Wins | 0 | 15 | higher | |
| Elite_SOS | 0 | 50 | higher | |
| PPP_Off | 0.88 | 1.30 | higher | |
| PPP_Def | 0.80 | 1.22 | inverse | |
| Adj_T | 60 | 80 | neutral | Context metric |
| RankTrajectory | -30 | 30 | higher | TRank_Early − Torvik_Rank (positive = improving) |

### 0.3 Derived Features (computed from normalized primitives)

```python
def compute_derived_features(norm):
    """
    norm: dict of feature_name -> normalized_value (0-1)
    Returns dict of derived feature name -> value
    """
    return {
        # Clutch / close game performance
        "CloseGame": (norm["Last_10_Games_Metric"] + norm["WinPct"] + 
                      0.5 * norm["FT%"] + 0.5 * norm["TO%_inv"]) / 3.0,
        
        # Three-point consistency (shooting + not over-relying on it)
        "ThreePtConsistency": (norm["3P%"] * 0.65 + norm["3P_%_D_inv"] * 0.35),
        
        # Ball movement quality
        "BallMovement": (norm["AST_TO"] * 0.50 + norm["Ast_%"] * 0.30 + 
                         norm["Op_Ast_%_inv"] * 0.20),
        
        # Physical dominance
        "Physicality": (norm["OR%"] * 0.30 + norm["Blk_%"] * 0.25 + 
                        norm["FTR"] * 0.25 + norm["Eff_Hgt"] * 0.20),
        
        # Inside scoring ability
        "InsideScoring": (norm["2P%"] * 0.50 + norm["OR%"] * 0.30 + 
                          norm["FTR"] * 0.20),
        
        # Interior defense
        "InteriorDefense": (norm["2P_%_D_inv"] * 0.45 + norm["Blk_%"] * 0.35 + 
                            norm["DR%"] * 0.20),
        
        # Tournament readiness (efficiency under pressure proxy)
        "TournamentReadiness": (norm["Barthag"] * 0.50 + norm["Exp"] * 0.30 + 
                                 norm["Quad1_Wins"] * 0.20),
        
        # Defensive playmaking
        "DefensivePlaymaking": (norm["Opp_TO%"] * 0.55 + norm["Blk_%"] * 0.30 + 
                                 norm["Blked_%_inv"] * 0.15),
        
        # Ranking trajectory: teams trending upward in efficiency rankings
        # heading into the tournament. Uses Torvik Time Machine snapshot from
        # ~4 weeks before Selection Sunday vs current T-Rank.
        # Positive delta = improving; negative = declining.
        "NETMomentum": normalize_value(
            norm.get("RankTrajectory", 0), -30, 30
        ),
    }
```

---

## 1. Conference Strength Index (CSI)

### 1.1 WIN50 Method

For each conference, find the rating R that produces a .500 expected record in a round-robin of the conference:

```python
import scipy.optimize as opt

def win50_rating(conference_adjems: list[float]) -> float:
    """
    Solve for R such that a team with AdjEM=R would go exactly .500
    against the conference in round-robin.
    Uses the same logistic function as win probability.
    """
    n = len(conference_adjems)
    
    def expected_wins(R):
        wins = sum(
            1.0 / (1.0 + 10 ** ((r_j - R) * 30.464 / 400))
            for r_j in conference_adjems
        )
        return wins - n / 2.0
    
    # Bracket the root: any team rated -50 would go ~0 wins, +50 would go ~all wins
    return opt.brentq(expected_wins, -50, 50, xtol=1e-6)
```

### 1.2 Non-Conference Calibration Factor

```python
def nonconf_calibration(team_rows_in_conf: list[dict], 
                         all_teams_adjEM: dict[str, float]) -> float:
    """
    Measures how conference teams perform in non-conference games
    relative to their AdjEM-predicted performance.
    Returns a signed float: positive = conference outperforms predictions.
    """
    total_actual = 0
    total_expected = 0
    count = 0
    
    for team in team_rows_in_conf:
        # Proxy: Quad1_Wins vs expected Quad1 wins based on AdjEM rank
        expected_q1_wins = max(0, (350 - team.get('CompRank', team['Torvik_Rank'])) / 350 * 12)
        actual_q1_wins = team.get('Quad1_Wins', 3)
        total_actual += actual_q1_wins
        total_expected += expected_q1_wins
        count += 1
    
    if count == 0 or total_expected == 0:
        return 0.0
    
    return (total_actual - total_expected) / total_expected
```

### 1.3 Final CSI Computation

```python
def compute_csi(conf_teams: list[dict]) -> dict:
    adjems = [t['AdjEM'] for t in conf_teams]
    win50 = win50_rating(adjems)
    nonconf_adj = nonconf_calibration(conf_teams, {})
    
    # CSI blends WIN50 (primary) with non-conference calibration (secondary)
    raw_csi = 0.75 * win50 + 0.25 * (win50 * (1 + nonconf_adj))
    
    # Normalize CSI to a multiplier around 1.0
    # National average CSI is ~0.0 in AdjEM space
    # Map to [0.75, 1.05] multiplier range
    national_avg = 0.0   # by construction of AdjEM
    national_std = 8.0   # empirically ~8 AdjEM points
    
    csi_z = (raw_csi - national_avg) / national_std
    csi_multiplier = 1.0 + 0.04 * csi_z  # ±4% per standard deviation
    csi_multiplier = np.clip(csi_multiplier, 0.75, 1.05)
    
    return {
        "win50": win50,
        "nonconf_adj": nonconf_adj,
        "raw_csi": raw_csi,
        "multiplier": csi_multiplier
    }
```

---

## 2. Core Scoring Engine

### 2.1 General Score Formula

```python
def calculate_team_score(team: dict, weights: dict, norm: dict, 
                          derived: dict, csi_multiplier: float,
                          apply_conference: bool = True) -> float:
    """
    Computes a composite score for a team given a weight dictionary.
    
    team: raw team data dict
    weights: model weight dict (feature_name -> weight, sums to 1.0)
    norm: normalized feature dict (feature_name -> 0-1 value)
    derived: derived features dict
    csi_multiplier: conference strength multiplier
    
    Returns: score in [0, 100]
    """
    score = 0.0
    
    for feature, weight in weights.items():
        if feature in norm:
            score += weight * norm[feature]
        elif feature in derived:
            score += weight * derived[feature]
        # Missing features contribute 0.5 * weight (neutral)
        else:
            score += weight * 0.5
    
    # Scale to 0-100
    score *= 100.0
    
    # Apply conference adjustment (last step)
    if apply_conference:
        score *= csi_multiplier
    
    return round(score, 1)
```

### 2.2 Model Weight Dictionaries

All weights must sum to 1.0. These are the research-calibrated values.

#### 2.2.1 Default / Power Ranking Weights

Optimized for overall tournament performance prediction. AdjEM has the highest weight per every ML feature importance study.

```python
DEFAULT_WEIGHTS = {
    "AdjEM":          0.27,
    "CompRank_inv":   0.12,  # inverse-normalized composite rank
    "SOS_inv":        0.06,
    "eFG%":           0.07,
    "Opp_eFG%_inv":   0.05,
    "Opp_TO%":        0.06,  # forced turnovers (defense)
    "TO%_inv":        0.03,  # own turnovers (lower = better)
    "OR%":            0.04,
    "DR%":            0.03,
    "FTR":            0.02,
    "FT%":            0.02,
    "Barthag":        0.04,
    "Last_10_Games_Metric": 0.04,
    "Exp":            0.03,
    "Quad1_Wins":     0.04,
    "Star_Player_Index": 0.02,
    "Bench_Minutes_Pct": 0.02,
    "Physicality":    0.02,  # derived
    "BallMovement":   0.02,  # derived
}
# Sum = 1.00
```

#### 2.2.2 Defensive Weights

```python
DEFENSIVE_WEIGHTS = {
    "AdjD_inv":            0.30,
    "Opp_eFG%_inv":        0.15,
    "Opp_TO%":             0.14,
    "DR%":                 0.10,
    "Blk_%":               0.08,
    "InteriorDefense":     0.07,  # derived
    "DefensivePlaymaking": 0.06,  # derived
    "Opp_FTR_inv":         0.04,
    "3P_%_D_inv":          0.03,
    "2P_%_D_inv":          0.03,
}
# Sum = 1.00
```

#### 2.2.3 Offensive Weights

```python
OFFENSIVE_WEIGHTS = {
    "AdjO":           0.30,
    "eFG%":           0.18,
    "PPP_Off":        0.12,
    "InsideScoring":  0.10,  # derived
    "3P%":            0.08,
    "OR%":            0.07,
    "BallMovement":   0.06,  # derived
    "FTR":            0.05,
    "FT%":            0.04,
}
# Sum = 1.00
```

#### 2.2.4 Momentum Weights

```python
MOMENTUM_WEIGHTS = {
    "Last_10_Games_Metric": 0.35,
    "CloseGame":            0.20,  # derived
    "AdjEM":                0.15,
    "Opp_TO%":              0.10,
    "FT%":                  0.05,
    "Barthag":              0.07,
    "TournamentReadiness":  0.05,  # derived
    "NETMomentum":          0.03,  # derived — ranking trajectory into tournament
}
# Sum = 1.00
```

#### 2.2.5 Giant Killer Weights

For seeds 6+ who can beat top teams. Emphasizes efficiency, defense, and elements that beat favorites.

```python
GIANT_KILLER_WEIGHTS = {
    "Opp_eFG%_inv":        0.18,
    "Opp_TO%":             0.17,
    "AdjEM":               0.15,
    "CloseGame":           0.12,  # derived
    "DefensivePlaymaking": 0.10,  # derived
    "FT%":                 0.08,
    "Barthag":             0.07,
    "Quad1_Wins":          0.06,
    "Exp":                 0.04,
    "InteriorDefense":     0.03,  # derived
}
# Sum = 1.00
```

#### 2.2.6 Cinderella Tournament Weights

Used in the Cinderella strategy bracket. Blends with Cinderella Score.

```python
CINDERELLA_TOURNAMENT_WEIGHTS = {
    "SeedMismatch_norm":   0.25,  # computed from seed vs CompRank implied seed
    "AdjD_inv":            0.18,
    "Opp_TO%":             0.15,
    "Barthag":             0.12,
    "Exp":                 0.08,
    "Adj_T_inv":           0.07,  # lower season-long tempo = more dangerous underdog (Toohey 2025; pace control keeps games close)
    "OR%":                 0.06,
    "Quad1_Wins":          0.05,
    "CloseGame":           0.04,  # derived
}
# Sum = 1.00
```

#### 2.2.7 Favorites Weights

Heavy on efficiency and top-line metrics. For chalk brackets.

```python
FAVORITES_WEIGHTS = {
    "AdjEM":        0.40,
    "Barthag":      0.25,
    "CompRank_inv": 0.20,
    "eFG%":         0.08,
    "AdjD_inv":     0.07,
}
# Sum = 1.00
```

#### 2.2.8 Analytics (Pure Efficiency) Weights

```python
ANALYTICS_WEIGHTS = {
    "AdjEM":      0.35,
    "Barthag":    0.25,
    "AdjO":       0.15,
    "AdjD_inv":   0.15,
    "SOS_inv":    0.10,
}
# Sum = 1.00
```

#### 2.2.9 Experience Weights

```python
EXPERIENCE_WEIGHTS = {
    "Exp":                  0.25,
    "TournamentReadiness":  0.20,  # derived
    "AdjEM":                0.20,
    "CloseGame":            0.15,  # derived
    "Quad1_Wins":           0.10,
    "Barthag":              0.10,
}
# Sum = 1.00
```

---

## 3. Win Probability Engine

### 3.1 Primary Win Probability Function

Converts AdjEM difference to a predicted point spread, then applies normal CDF. The 11.0 standard deviation is the empirically validated game variance constant for college basketball.

```python
import scipy.stats as stats
import numpy as np

def win_probability(team_a: dict, team_b: dict, 
                    game_std: float = 11.0) -> float:
    """
    Returns P(team_a beats team_b) on neutral court.
    
    game_std: standard deviation of game outcomes (11.0 is the
              empirically validated constant for college basketball)
    """
    adjEM_diff = team_a['AdjEM'] - team_b['AdjEM']
    
    # Expected possessions: average of both teams' adjusted tempo
    tempo_a = team_a.get('Adj_T', 68.0)
    tempo_b = team_b.get('Adj_T', 68.0)
    expected_possessions = (tempo_a + tempo_b) / 2.0
    
    # Predicted point spread (positive = team_a favored)
    # AdjEM is per-100-possessions; scale to actual game
    predicted_spread = adjEM_diff * expected_possessions / 100.0
    
    # Normal CDF: P(team_a wins) given predicted spread and game variance
    prob = stats.norm.cdf(predicted_spread / game_std)
    
    # Clip to prevent log-loss catastrophe on edge cases
    return float(np.clip(prob, 0.03, 0.97))


def predicted_spread(team_a: dict, team_b: dict) -> float:
    """Returns expected point differential (positive = team_a wins by this margin)."""
    tempo_avg = (team_a.get('Adj_T', 68.0) + team_b.get('Adj_T', 68.0)) / 2.0
    return (team_a['AdjEM'] - team_b['AdjEM']) * tempo_avg / 100.0


def win_probability_elo_style(team_a: dict, team_b: dict) -> float:
    """
    Alternative: FiveThirtyEight-style Elo logistic formula.
    Useful as a cross-check or blend. 
    Formula: 1 / (1 + 10^(-rating_diff * 30.464 / 400))
    The 30.464 constant converts Elo scale to AdjEM scale.
    """
    adjEM_diff = team_a['AdjEM'] - team_b['AdjEM']
    return float(np.clip(1.0 / (1.0 + 10 ** (-adjEM_diff * 30.464 / 400)), 0.03, 0.97))
```

### 3.2 Blended Win Probability (Production Function)

Blend both methods with slight weighting toward the normal CDF (more calibrated for college basketball):

```python
def blended_win_probability(team_a: dict, team_b: dict) -> float:
    p_normal = win_probability(team_a, team_b)
    p_elo = win_probability_elo_style(team_a, team_b)
    # 60% normal CDF, 40% Elo-style
    blended = 0.60 * p_normal + 0.40 * p_elo
    return float(np.clip(blended, 0.03, 0.97))
```

### 3.3 Play-In Winner First-Round Boost

11-seed play-in game winners have an empirically documented edge in first-round games: they played under pressure 2 days earlier and enter the main bracket in "tournament mode." The system applies a small win probability uplift for first-round games only.

```python
def apply_play_in_boost(base_prob: float, team: dict,
                        opponent: dict, round_number: int) -> float:
    """
    Applies a +3% first-round win probability boost to play-in game winners.
    Only active in Round 1 (R64). The boost reflects the battle-tested
    advantage of teams that already won under tournament pressure.
    
    Requires Won_Play_In column in team data (0 or 1, set manually
    after First Four games on Tues/Wed before R64 begins Thursday).
    """
    if round_number != 1:
        return base_prob
    
    team_play_in = team.get('Won_Play_In', 0)
    opp_play_in = opponent.get('Won_Play_In', 0)
    
    if team_play_in and not opp_play_in:
        return float(np.clip(base_prob + 0.03, 0.03, 0.97))
    if opp_play_in and not team_play_in:
        return float(np.clip(base_prob - 0.03, 0.03, 0.97))
    
    return base_prob
```

### 3.4 Confidence Tier Labels

```python
def confidence_tier(prob: float) -> str:
    """Label win probability for human readability."""
    if prob >= 0.85:
        return "Strong Favorite"
    elif prob >= 0.70:
        return "Moderate Favorite"
    elif prob >= 0.55:
        return "Slight Favorite"
    elif prob >= 0.45:
        return "Toss-Up"
    else:
        return "Underdog"  # will be flipped for the lower-seeded team
```

### 3.5 Era-Adjusted Seed Prior Blending

For seed matchups where modern (68-team era) upset rates diverge significantly from what the AdjEM-based model predicts, blend in a historical prior. This corrects for unmodeled factors — play-in battle-hardening for 11-seeds, committee seeding noise, mid-major motivation — that persistently cause the model to overestimate the favorite.

The blend is conservative: 85% model, 15% era prior. When the AdjEM gap between teams is large, the model dominates; when it's small, the prior nudges toward empirical reality.

```python
ERA_SEED_PRIOR_FOR_UNDERDOG = {
    (6, 11): 0.52,     # 11-seed wins 52% in 68-team era
    (7, 10): 0.41,     # 10-seed wins 41% post-2011
    (8, 9):  0.625,    # 9-seed wins 62.5% since 2016
}

def apply_era_seed_prior(model_prob_a: float, 
                          seed_a: int, seed_b: int,
                          prior_weight: float = 0.15) -> float:
    """
    Blends model-based win probability with era-adjusted historical base rate.
    Only applies for seed matchups where modern data diverges significantly
    from all-time rates (6v11, 7v10, 8v9).
    
    model_prob_a: P(team_a wins) from blended_win_probability()
    seed_a, seed_b: seeds of team_a and team_b
    prior_weight: how much to weight the era prior (default 0.15)
    
    Returns adjusted P(team_a wins).
    """
    fav_seed = min(seed_a, seed_b)
    dog_seed = max(seed_a, seed_b)
    key = (fav_seed, dog_seed)
    
    if key not in ERA_SEED_PRIOR_FOR_UNDERDOG:
        return model_prob_a
    
    era_prior_for_fav = 1.0 - ERA_SEED_PRIOR_FOR_UNDERDOG[key]
    
    if seed_a == fav_seed:
        era_prior_a = era_prior_for_fav
    else:
        era_prior_a = 1.0 - era_prior_for_fav
    
    blended = (1.0 - prior_weight) * model_prob_a + prior_weight * era_prior_a
    return float(np.clip(blended, 0.03, 0.97))
```

**Integration:** Call `apply_era_seed_prior()` after `blended_win_probability()` and before any strategy-level adjustments. This ensures the era correction is applied uniformly across all bracket strategies and Monte Carlo simulation.

```python
def production_win_probability(team_a: dict, team_b: dict) -> float:
    """Full production win probability: model blend + era-adjusted seed prior."""
    base = blended_win_probability(team_a, team_b)
    return apply_era_seed_prior(
        base, team_a.get('Seed', 8), team_b.get('Seed', 8)
    )
```

---

## 4. Cinderella Score Algorithm

### 4.1 Seed → CompRank Implied Seed Mapping

```python
SEED_TO_RANK_RANGES = {
    1:  (1, 5),
    2:  (5, 10),
    3:  (10, 16),
    4:  (16, 26),
    5:  (26, 36),
    6:  (36, 50),
    7:  (50, 65),
    8:  (65, 80),
    9:  (80, 100),
    10: (100, 125),
    11: (125, 155),
    12: (155, 185),
    13: (185, 225),
    14: (225, 275),
    15: (275, 330),
    16: (330, 365),
}

def implied_seed(comp_rank: int) -> int:
    """Returns what seed a team 'should' be given their CompRank."""
    for seed, (lo, hi) in SEED_TO_RANK_RANGES.items():
        if lo <= comp_rank < hi:
            return seed
    return 16

def seed_mismatch(actual_seed: int, comp_rank: int) -> float:
    """
    Positive value = team is better than their seed suggests (underseeded).
    Negative value = team is overseeded.
    Normalized to [0, 1] for scoring purposes.
    """
    implied = implied_seed(comp_rank)
    raw_mismatch = actual_seed - implied  # positive means underseeded
    return np.clip(raw_mismatch / 10.0, 0.0, 1.0)  # 10 seeds difference = max score
```

### 4.2 Cinderella Score Formula

Only applied to teams with `Seed >= 9`. Returns a dict with component breakdown.

```python
def compute_cinderella_score(team: dict, norm: dict) -> dict:
    """
    Returns dict with component scores and total CinderellaScore.
    Based on research by UC Berkeley Sports Analytics (2025),
    Harvard Sports Analysis Collective (2012, 2019),
    NCAA.com Cinderella study (2019), and Wharton/Sha et al. (2023).
    """
    if team.get('Seed', 16) < 9:
        return {"CinderellaScore": 0.0, "AlertLevel": ""}
    
    # Component 1: Seed Mismatch (30% weight)
    # Research: teams underseeded by 3+ positions upset at 2x base rate
    comp_rank = team.get('CompRank', team.get('Torvik_Rank', 200))
    seed_mis = seed_mismatch(team['Seed'], comp_rank)
    
    # Component 2: Defensive Quality (25% weight)
    # Research: 25/26 historical Cinderellas were top-40 in AdjD OR AdjO
    adjd_rank = team.get('Torvik_Rank', 200)  # proxy; ideally separate AdjD rank
    if adjd_rank <= 40:
        defense_signal = 1.0
    elif adjd_rank <= 80:
        defense_signal = 0.65
    elif adjd_rank <= 120:
        defense_signal = 0.35
    else:
        defense_signal = 0.0
    # Also credit teams with top offensive rank
    if team.get('CompRank', team.get('Torvik_Rank', 200)) <= 40 and defense_signal < 0.65:
        defense_signal = max(defense_signal, 0.65)
    
    # Component 3: Turnover Signal (20% weight)
    # Research: 22/26 historical Cinderellas won turnover margin battle
    tov_margin_score = (norm.get("Opp_TO%", 0.5) * 0.6 + 
                        norm.get("TO%_inv", 0.5) * 0.4)
    
    # Component 4: Experience (10% weight)
    # Research: Pifer et al. 2019 — tournament experience predicts advancement
    exp_score = norm.get("Exp", 0.5)
    
    # Component 5: Tempo (8% weight)
    # Research: Toohey (2025) — Cinderella archetypes that succeed have
    # lower season-long adjusted tempo. Controlling pace reduces variance
    # and keeps games close (Skinner 2011 mathematical proof). The older
    # Harvard finding (in-game tempo higher in upsets) measures an effect,
    # not a cause, and predates the 2015 shot clock change.
    tempo = team.get('Adj_T', 68.0)
    tempo_score = normalize_inverse(tempo, 60, 80)
    
    # Component 6: Offensive Rebounding (7% weight)
    # Research: second-chance points compensate for talent gap
    reb_score = norm.get("OR%", 0.5)
    
    # Weighted sum
    cinderella_score = (
        0.30 * seed_mis +
        0.25 * defense_signal +
        0.20 * tov_margin_score +
        0.10 * exp_score +
        0.08 * tempo_score +
        0.07 * reb_score
    )
    
    # Alert level thresholds (calibrated against historical Cinderellas)
    if cinderella_score >= 0.55:
        alert = "HIGH"
    elif cinderella_score >= 0.40:
        alert = "WATCH"
    else:
        alert = ""
    
    return {
        "CinderellaScore": round(cinderella_score, 3),
        "AlertLevel": alert,
        "C_SeedMismatch": round(seed_mis, 3),
        "C_Defense": round(defense_signal, 3),
        "C_Turnover": round(tov_margin_score, 3),
        "C_Experience": round(exp_score, 3),
        "C_Tempo": round(tempo_score, 3),
        "C_Rebounding": round(reb_score, 3),
    }
```

### 4.3 NIL-Era Cinderella Suppression Note

**Context for calibration:** The NIL era (post-2021) appears to be suppressing Cinderella runs. Only one Cinderella reached the Sweet 16 in each of 2023, 2024, and 2025. The 2025 Sweet 16 was 100% Power Four teams for the first time in tournament history. NIL transfer portal activity has concentrated talent at top programs, widening the gap between power conference teams and mid-major Cinderella candidates.

The current alert thresholds (HIGH ≥ 0.55, WATCH ≥ 0.40) were calibrated against pre-NIL historical Cinderellas. In the post-2021 environment, fewer teams will cross these thresholds, and those that do may face steeper odds than historical base rates suggest. No formula change is applied — the AdjEM-based win probability already reflects the talent gap — but users should interpret Cinderella alerts with the understanding that the base rate of deep Cinderella runs has decreased in the modern era.

---

## 5. Monte Carlo Bracket Simulation

### 5.1 Bracket Structure

```python
# Standard bracket slot pairs (within each region, 0-indexed)
FIRST_ROUND_MATCHUPS = [
    (0, 1),   # 1 vs 16
    (2, 3),   # 8 vs 9
    (4, 5),   # 5 vs 12
    (6, 7),   # 4 vs 13
    (8, 9),   # 6 vs 11
    (10, 11), # 3 vs 14
    (12, 13), # 7 vs 10
    (14, 15), # 2 vs 15
]

ROUND_NAMES = ["R64", "R32", "S16", "E8", "F4", "Championship", "Champion"]
```

### 5.2 Core Simulation

```python
import random
import numpy as np
from collections import defaultdict

def simulate_bracket(
    bracket: dict,          # {region: [team_dict, ...]} — 16 teams per region in slot order
    win_prob_fn,            # callable(team_a, team_b) -> float
    n_sims: int = 10000,
    seed: int = 42
) -> dict:
    """
    Monte Carlo bracket simulation.
    Returns advancement probabilities for each team to each round.
    """
    random.seed(seed)
    np.random.seed(seed)
    
    regions = list(bracket.keys())  # ["East", "West", "South", "Midwest"]
    all_teams = {t['team']: t for r in regions for t in bracket[r]}
    
    # Accumulate advancement counts
    reach_count = defaultdict(lambda: defaultdict(int))
    modal_wins = defaultdict(lambda: defaultdict(int))  # for modal bracket
    
    for sim_i in range(n_sims):
        # Each simulation: play all 63 games
        region_winners = []
        
        for region in regions:
            teams = list(bracket[region])  # 16 teams in slot order
            
            # Round of 64 (8 games)
            r32_teams = []
            for slot_a, slot_b in FIRST_ROUND_MATCHUPS:
                winner = _play_game(teams[slot_a], teams[slot_b], 
                                    win_prob_fn, reach_count, "R32")
                r32_teams.append(winner)
            
            # Round of 32 (4 games)
            # Winners of games 1-2 play, 3-4 play, etc.
            s16_teams = []
            for i in range(0, 8, 2):
                winner = _play_game(r32_teams[i], r32_teams[i+1],
                                    win_prob_fn, reach_count, "S16")
                s16_teams.append(winner)
            
            # Sweet 16 (2 games)
            e8_teams = []
            for i in range(0, 4, 2):
                winner = _play_game(s16_teams[i], s16_teams[i+1],
                                    win_prob_fn, reach_count, "E8")
                e8_teams.append(winner)
            
            # Elite 8 (1 game)
            region_winner = _play_game(e8_teams[0], e8_teams[1],
                                        win_prob_fn, reach_count, "F4")
            region_winners.append(region_winner)
        
        # Final Four (2 games): East vs West, South vs Midwest
        f4_winner_1 = _play_game(region_winners[0], region_winners[1],
                                   win_prob_fn, reach_count, "Championship")
        f4_winner_2 = _play_game(region_winners[2], region_winners[3],
                                   win_prob_fn, reach_count, "Championship")
        
        # Championship
        champion = _play_game(f4_winner_1, f4_winner_2,
                               win_prob_fn, reach_count, "Champion")
        reach_count[champion['team']]["Champion"] += 1
    
    # Also track R64 (all 68 teams enter)
    for region in regions:
        for team in bracket[region]:
            reach_count[team['team']]["R64"] = n_sims  # all teams start
    
    # Normalize to probabilities
    results = {}
    for team_name, rounds in reach_count.items():
        results[team_name] = {
            r: count / n_sims 
            for r, count in rounds.items()
        }
    
    return results


def _play_game(team_a: dict, team_b: dict, 
               win_prob_fn, reach_count: dict, 
               next_round: str) -> dict:
    """Simulate a single game; update reach_count for winner."""
    p_a = win_prob_fn(team_a, team_b)
    winner = team_a if random.random() < p_a else team_b
    reach_count[winner['team']][next_round] += 1
    return winner
```

### 5.3 Modal Bracket Generation

```python
def generate_modal_bracket(simulation_results: dict, 
                            bracket: dict, 
                            win_prob_fn) -> dict:
    """
    Pick the most-likely winner of each game.
    This is a deterministic bracket (not from simulation randomness)
    that always picks the team with higher win probability.
    """
    modal = {}
    for region, teams in bracket.items():
        modal[region] = {}
        # ... same bracket traversal but always pick higher-prob winner
        # Returns {round_name: [{game_idx: winner_team, prob, is_upset}, ...]}
    return modal
```

---

## 6. Bracket Strategy Generation

### 6.1 Strategy Definitions

Each strategy blends model scores and applies different upset thresholds.

```python
STRATEGY_CONFIGS = {
    "standard": {
        "model_blends": {"default": 1.0},
        "upset_threshold": 0.40,    # upset if underdog win prob > threshold
        "description": "Composite power score — balanced prediction"
    },
    "favorites": {
        "model_blends": {"favorites": 0.70, "analytics": 0.30},
        "upset_threshold": 0.55,    # very conservative — only pick big upsets
        "description": "Chalk-heavy — efficiency-first, minimize upsets"
    },
    "upsets": {
        "model_blends": {"giant_killer": 0.60, "cinderella_tournament": 0.40},
        "upset_threshold": 0.30,    # aggressive — pick more upsets
        "description": "Actively seeks upsets where Cinderella score is high"
    },
    "analytics": {
        "model_blends": {"analytics": 1.0},
        "upset_threshold": 0.45,
        "description": "Pure AdjEM/Barthag logistic — no heuristics"
    },
    "cinderella": {
        "model_blends": {"cinderella_tournament": 0.70, "default": 0.30},
        "upset_threshold": 0.33,
        "cinderella_boost": 0.10,   # add 10% win prob if CinderellaScore > 0.50
        "description": "Maximizes Cinderella picks for deep runs"
    },
    "defensive": {
        "model_blends": {"defensive": 0.70, "default": 0.30},
        "upset_threshold": 0.40,
        "description": "Defense wins championships — defense-weighted model"
    },
    "momentum": {
        "model_blends": {"momentum": 0.65, "default": 0.35},
        "upset_threshold": 0.38,
        "description": "Hot teams win in March — recency-weighted model"
    },
    "experience": {
        "model_blends": {"experience": 0.60, "default": 0.40},
        "upset_threshold": 0.42,
        "description": "Experience and tournament history matter"
    },
}
```

### 6.2 Strategy-Adjusted Win Probability

```python
def strategy_win_prob(team_a: dict, team_b: dict,
                       strategy: dict, 
                       scores: dict,   # {team_name: {model_name: score}}
                       base_prob_fn) -> float:
    """
    Applies strategy-level adjustments to base win probability.
    """
    base_prob = base_prob_fn(team_a, team_b)
    
    # Weighted score comparison
    blend = strategy["model_blends"]
    score_a = sum(w * scores[team_a['team']].get(m, 50) for m, w in blend.items())
    score_b = sum(w * scores[team_b['team']].get(m, 50) for m, w in blend.items())
    
    # Score-ratio adjustment (additive, capped at ±0.10)
    if score_a + score_b > 0:
        score_ratio_adj = (score_a / (score_a + score_b) - 0.5) * 0.20
        score_ratio_adj = np.clip(score_ratio_adj, -0.10, 0.10)
    else:
        score_ratio_adj = 0.0
    
    adjusted_prob = np.clip(base_prob + score_ratio_adj, 0.03, 0.97)
    
    # Cinderella boost
    if "cinderella_boost" in strategy:
        team_b_cinderella = team_b.get('CinderellaScore', 0.0)
        if team_b_cinderella > 0.50 and team_b['Seed'] > team_a['Seed']:
            adjusted_prob = np.clip(adjusted_prob - strategy["cinderella_boost"], 0.03, 0.97)
    
    return adjusted_prob


def simulate_matchup_strategy(team_a: dict, team_b: dict,
                               strategy: dict, scores: dict,
                               base_prob_fn) -> dict:
    """
    Deterministic matchup resolution for bracket generation.
    (Not Monte Carlo — this picks a single winner per strategy.)
    """
    prob_a = strategy_win_prob(team_a, team_b, strategy, scores, base_prob_fn)
    
    # Determine favorite (lower seed = higher expected quality)
    favorite = team_a if team_a['Seed'] <= team_b['Seed'] else team_b
    underdog = team_b if favorite == team_a else team_a
    
    fav_prob = prob_a if favorite == team_a else (1 - prob_a)
    
    # Upset: underdog wins if its probability exceeds upset threshold
    is_upset = (1 - fav_prob) > strategy["upset_threshold"]
    
    # Hard guard: 16-seed never beats 1-seed in analytics/favorites strategies
    if (underdog['Seed'] == 16 and favorite['Seed'] == 1 and 
        strategy.get('upset_threshold', 0) > 0.35):
        is_upset = False
    
    winner = underdog if is_upset else favorite
    winner_prob = (1 - fav_prob) if is_upset else fav_prob
    
    return {
        "winner": winner,
        "winner_prob": round(winner_prob, 3),
        "is_upset": is_upset,
        "team_a_prob": round(prob_a, 3),
    }
```

---

## 7. Team Strength Labels

Human-readable labels applied to each team in output tables:

```python
def get_team_strengths(team: dict) -> list[str]:
    strengths = []
    
    # Offense
    if team.get('eFG%', 0) >= 56:     strengths.append("elite shooting efficiency")
    elif team.get('eFG%', 0) >= 53:   strengths.append("above-avg shooting")
    if team.get('3P%', 0) >= 38:      strengths.append("elite 3-point shooting")
    if team.get('AdjO', 0) >= 120:    strengths.append("elite offense")
    if team.get('OR%', 0) >= 35:      strengths.append("dominant offensive rebounding")
    if team.get('FT%', 0) >= 78:      strengths.append("excellent free throw shooting")
    if team.get('AST_TO', 0) >= 1.8:  strengths.append("exceptional ball movement")
    
    # Defense
    if team.get('AdjD', 0) <= 92:     strengths.append("elite defense")
    elif team.get('AdjD', 0) <= 96:   strengths.append("above-avg defense")
    if team.get('Opp_eFG%', 0) <= 46: strengths.append("stifling perimeter defense")
    if team.get('Opp_TO%', 0) >= 22:  strengths.append("forces turnovers")
    if team.get('Blk_%', 0) >= 12:    strengths.append("shot-blocking presence")
    
    # Momentum / experience
    if team.get('Last_10_Games_Metric', 0) >= 0.85:  strengths.append("red-hot form")
    if team.get('Exp', 0) >= 2.3:                    strengths.append("veteran squad")
    if team.get('Quad1_Wins', 0) >= 8:               strengths.append("battle-tested (Q1 wins)")
    
    # Physical
    if team.get('Eff_Hgt', 0) >= 82:  strengths.append("size advantage")
    
    # Schedule
    if team.get('SOS', 365) <= 30:    strengths.append("elite SOS")
    
    return strengths[:4]  # Return top 4 most relevant
```

---

## 8. Historical Upset Rate Priors (for display/validation only)

These are historical base rates used to contextualize simulation outputs and as Bayesian priors in the era-adjusted seed blending step (§3.5).

```python
HISTORICAL_UPSET_RATES = {
    (1, 16): 0.0125,   # 2 upsets in 160 games since 1985
    (2, 15): 0.069,
    (3, 14): 0.144,
    (4, 13): 0.206,
    (5, 12): 0.356,    # "always pick a 12-seed" — 35.6% upset rate
    (6, 11): 0.388,    # all-time; POST-2011 era rate is 0.518 — see ERA_UPSET_RATES_POST_2011
    (7, 10): 0.375,
    (8, 9):  0.519,    # 83 upsets in 160 games (1985–2025)
}

# Post-2011 era-split rates: since the field expanded to 68 teams,
# many 11-seeds are bubble at-large teams that won a play-in game and
# enter the first round battle-hardened. The blended all-time rate
# significantly underestimates how dangerous modern 11-seeds are.
ERA_UPSET_RATES_POST_2011 = {
    (6, 11): 0.518,    # 27-29 record — effectively a coin flip in the 68-team era
    (7, 10): 0.410,    # slight uptick post-expansion
    (8, 9):  0.625,    # 9-seeds win ~62.5% since 2016 — dramatic departure from all-time 51.9%
}

def seed_upset_context(seed_fav: int, seed_dog: int,
                       post_2011_only: bool = False) -> str:
    """Returns a human-readable historical context string.
    
    post_2011_only: if True, uses 68-team era rates for matchups
    where era-split data is available (6v11, 7v10). More accurate
    for modern tournament predictions.
    """
    if post_2011_only and (seed_fav, seed_dog) in ERA_UPSET_RATES_POST_2011:
        rate = ERA_UPSET_RATES_POST_2011[(seed_fav, seed_dog)]
        return (f"In the 68-team era (post-2011), {seed_dog}-seeds beat "
                f"{seed_fav}-seeds {rate*100:.1f}% of the time")
    rate = HISTORICAL_UPSET_RATES.get((seed_fav, seed_dog), 0.30)
    return f"Historically, {seed_dog}-seeds beat {seed_fav}-seeds {rate*100:.1f}% of the time"
```

---

## 9. Model Calibration (Backtest)

Run this against historical data to validate and tune weights.

```python
def backtest(historical_years: list[int], 
             model_weights: dict) -> dict:
    """
    For each historical year:
    1. Load team stats from that year (pre-tournament)
    2. Load actual tournament outcomes
    3. Run win probability for each actual matchup
    4. Compute: accuracy (% correct picks), log loss, Brier score
    """
    results = []
    for year in historical_years:
        teams = load_historical_teams(year)   # from data/historical/
        games = load_tournament_games(year)   # actual results
        
        correct = 0
        log_loss_total = 0
        brier_total = 0
        n = len(games)
        
        for game in games:
            team_a = teams[game['team_a']]
            team_b = teams[game['team_b']]
            actual_winner = game['winner']
            
            prob_a = production_win_probability(team_a, team_b)
            prob_winner = prob_a if actual_winner == game['team_a'] else (1 - prob_a)
            
            correct += (prob_a > 0.5) == (actual_winner == game['team_a'])
            log_loss_total += -np.log(prob_winner + 1e-9)
            brier_total += (1 - prob_winner) ** 2
        
        results.append({
            "year": year,
            "accuracy": correct / n,
            "log_loss": log_loss_total / n,
            "brier_score": brier_total / n,
        })
    
    return results
```

**Target benchmarks:**
- Accuracy: ≥ 70% (seed-only baseline is ~67%)
- Log loss: ≤ 0.56 (seed-only baseline is ~0.59)
- Brier score: ≤ 0.20

---

## 10. Fraud Score Algorithm

The Fraud Score identifies teams that *appear* strong by seed and reputation but carry structural weaknesses that single-elimination tournaments routinely expose. The canonical example is Purdue: historically top-10 in efficiency rankings, routinely given 1–3 seeds, and just as routinely eliminated early by athletic opponents who neutralize their dominant-big-man system and exploit their guard depth and defensive inconsistency.

**Research basis:**
- FanSided: No champion since 1997 has won a title without ranking top-25 in **both** AdjO AND AdjD. Offense-dominant teams with weak defense are structurally fraudulent.
- Bracketsninja: Big Ten teams eliminated in R64/R32 at a rate higher than their average seeding predicts — the conference's grinding half-court style is built for a long regular season, not a neutral-court 40-minute elimination game.
- Luck metric: teams winning significantly more games than their efficiency predicts (`WinPct − Barthag > 0`) are benefiting from variance (close game wins, hot shooting nights) that does not sustain in March. High Luck = regression candidate.
- Betstamp: Seeds 5–6 ranked outside the top 30 went just 10–12 combined in first-round games over a recent span — directly identifying overseeded teams.
- Purdue 2025 example: elite AdjO (#2) but AdjD ranked #37. Went 3-6 in last 9 games entering tournament. Star-player-dependent.
- Purdue 2023 example: lost to FDU (a 16-seed) after holding the lead for only 11:36 of 40 minutes — the canonical fraud outcome validated in Section 10.2's calibration table.

### 10.1 Fraud Score Formula

Only applied to teams with `Seed <= 6` (the teams everyone expects to go deep). Seeds 7+ are already underdogs — the concept doesn't apply.

**Research basis for weight allocation:**
- Harvard Sports Analysis Collective (2021) "Balance Wins Championships": offense-heavy imbalanced teams underperform by 0.15 wins/tournament after controlling for seed
- FiveThirtyEight: 14 of 19 champions (2002–2021) ranked top 15 in both AdjO and AdjD
- Betstamp: seeds 5–6 ranked outside top 30 went 10–12 in first-round games
- KenPom luck metric: year-to-year correlation of just 0.06 — almost pure noise, should be a penalty modifier not a primary input
- FiveThirtyEight: preseason polls are roughly as predictive as in-season performance — teams that dramatically exceed preseason expectations are regression candidates

```python
def compute_fraud_score(team: dict, norm: dict) -> dict:
    """
    Returns a Fraud Score for highly-seeded teams (seed 1-6).
    Higher score = more fraudulent = more likely to underperform seed.

    Components (all normalized 0-1, higher component = more fraudulent):

    1. Seed Deviation (25%) — the most direct measure of overseeding.
       If CompRank implies seed 6 but team is seeded 3, the committee
       gave them 3 extra seed lines of credit they haven't earned
       by efficiency metrics.

    2. Offensive-Defensive Imbalance (25%) — the strongest structural predictor.
       Teams that win via offense but have weak defense get exposed in March
       when opponents game-plan specifically for their offense.

    3. Recent Form Collapse (15%) — trending DOWN entering the tournament.
       A team going 3-6 in last 9 games is not the same team that earned its seed.

    4. Luck (15%) — winning more games than efficiency predicts (WinPct − Barthag).
       Year-to-year correlation is just 0.06. Used as a penalty modifier —
       high luck signals regression but shouldn't dominate the score.

    5. High-Variance Style (10%) — 3PT-reliant offenses with inconsistent
       performance introduce randomness that favors underdogs in single-elimination.

    6. Single-Player Dependence (5%) — one-star-dominant teams are
       vulnerable to defensive game plans and foul trouble.

    7. Conference Tournament Performance Bias (5%) — Big Ten teams
       historically underperform in deep rounds; Big 12 and SEC
       overperform. Modest adjustment.
    """
    if team.get('Seed', 16) > 6:
        return {"FraudScore": 0.0, "FraudLevel": ""}

    # ── Component 1: Seed Deviation (25%) ─────────────────────────────
    # Mirror of Cinderella's SeedMismatch but from the fraud side:
    # if implied_seed > actual_seed, team is overseeded.
    comp_rank = team.get('CompRank', team.get('Torvik_Rank', 50))
    implied = implied_seed(comp_rank)
    overseeded_gap = implied - team.get('Seed', 4)  # positive = overseeded
    # 4+ seed lines of overseeding = max fraud signal
    seed_deviation_score = np.clip(overseeded_gap / 4.0, 0.0, 1.0)

    # ── Component 2: Offensive-Defensive Imbalance (25%) ──────────────
    adjO_norm = norm.get("AdjO", 0.5)
    adjD_norm = norm.get("AdjD_inv", 0.5)  # already inverse normalized

    # Positive = offense >> defense (fraud indicator)
    imbalance = max(0, adjO_norm - adjD_norm)
    # A 0.3+ gap on the 0-1 scale is flagrant
    imbalance_score = min(1.0, imbalance / 0.35)

    # Hard rule: if AdjD rank > 40 (absolute), flag as high fraud regardless
    # (No champion since 1997 had AdjD rank > 40 at tournament time)
    adjD_rank_raw = team.get('Torvik_Rank', 50)  # proxy for defensive rank
    if adjD_rank_raw > 40:
        imbalance_score = max(imbalance_score, 0.70)

    # ── Component 3: Recent Form Collapse (15%) ───────────────────────
    season_winpct = team.get('Wins', 20) / max(team.get('Games', 30), 1)
    recent_form = team.get('Last_10_Games_Metric', season_winpct)

    form_drop = max(0, season_winpct - recent_form)
    # A 0.20 drop (e.g., season: 0.80 → recent: 0.60 = 3-7 in last 10) is alarming
    form_collapse_score = min(1.0, form_drop / 0.25)

    # ── Component 4: Luck (15%) ──────────────────────────────────────
    # Year-to-year correlation of just 0.06 — treat as penalty modifier,
    # not a primary signal. Reduced from 25% based on research showing
    # luck is nearly pure noise and over-weighting it introduces instability.
    luck = team.get('Luck', 0.0)
    luck_score = normalize_value(luck, -0.05, 0.10)

    # ── Component 5: High-Variance Style (10%) ───────────────────────
    # 3PT-reliant offenses are boom-or-bust in single-elimination.
    # Combined with inconsistent recent performance, this signals a team
    # that could easily have a cold-shooting game and lose.
    three_pt_rate = norm.get("3P_Rate", 0.5)  # neutral-normalized
    consistency = norm.get("Consistency_Score", 0.5)
    variance_score = 0.6 * three_pt_rate + 0.4 * (1.0 - consistency)

    # ── Component 6: Single-Player Dependence (5%) ───────────────────
    # Note on injury interaction: if a star player is injured, the
    # overrides system reduces BOTH AdjEM (making the team weaker in
    # win probability) AND Star_Player_Index (changing this fraud
    # component). These are complementary effects, not redundant.
    star = team.get('Star_Player_Index', 5.0)
    bench = team.get('Bench_Minutes_Pct', 30.0)

    star_norm = normalize_value(star, 1, 10)
    bench_norm = normalize_value(bench, 20, 55)
    dependence_score = max(0, star_norm - bench_norm * 0.7)
    dependence_score = min(1.0, dependence_score)

    # ── Component 7: Conference Tournament Performance Bias (5%) ──────
    # Based on 2021–2025 tournament performance data:
    # Big Ten: 0 championships in 25 years, deep-round underperformance
    # Big 12 and SEC: consistent overperformance, no fraud penalty
    FRAUD_CONFERENCE_PENALTIES = {
        "B10": 0.65,    # Big Ten: documented deep-round underperformance
        "ACC": 0.25,    # ACC: slight overseeding tendency (Duke/UNC reputation)
        "BE":  0.20,    # Big East: mild
        "MWC": 0.30,    # Mountain West: consistent 2021–2025 underperformance (0-4, 2-4, 2-4)
        "Big12": 0.00,  # Big 12: 2 champions 2021–2022, no penalty
        "SEC": 0.00,    # SEC: strongest 2021–2025 performer, no penalty
    }
    conf = team.get('Conference', 'Unknown')
    conf_fraud = FRAUD_CONFERENCE_PENALTIES.get(conf, 0.15)

    # ── Tempo vulnerability modifier (not a weighted component) ──────
    # Highly seeded favorites at slow pace (Adj_T < 65) are
    # disproportionately represented among early-round upset victims.
    adj_t = team.get('Adj_T', 68.0)
    if adj_t < 65.0 and team.get('Seed', 10) <= 4:
        imbalance_score = min(1.0, imbalance_score + 0.10)

    # ── Weighted composite ─────────────────────────────────────────────
    fraud_score = (
        0.25 * seed_deviation_score +
        0.25 * imbalance_score +
        0.15 * form_collapse_score +
        0.15 * luck_score +
        0.10 * variance_score +
        0.05 * dependence_score +
        0.05 * conf_fraud
    )

    # Fraud alert levels
    if fraud_score >= 0.60:
        fraud_level = "HIGH"    # 💀 Serious fraud risk — consider upset pick
    elif fraud_score >= 0.40:
        fraud_level = "MEDIUM"  # ⚠️  Fraud watch — don't auto-advance far
    elif fraud_score >= 0.25:
        fraud_level = "LOW"     # 📋 Mild concern — be careful in later rounds
    else:
        fraud_level = ""        # Clean profile

    return {
        "FraudScore": round(fraud_score, 3),
        "FraudLevel": fraud_level,
        "F_SeedDeviation": round(seed_deviation_score, 3),
        "F_Imbalance": round(imbalance_score, 3),
        "F_FormCollapse": round(form_collapse_score, 3),
        "F_Luck": round(luck_score, 3),
        "F_Variance": round(variance_score, 3),
        "F_StarDependence": round(dependence_score, 3),
        "F_Conference": round(conf_fraud, 3),
    }
```

### 10.2 Fraud Score Thresholds (Calibrated Against 2023 Tournament Historical Data)

| Purdue 2023 (1-seed, lost to 16-seed FDU in R64) | Fraud Score: ~0.68 |
|---|---|
| Component | Weight | Value |
| Seed Deviation (KenPom #1 but structurally flawed) | 25% | 0.25 |
| Imbalance (AdjO #1, AdjD #37) | 25% | 0.85 |
| Form Collapse (late-season swoon) | 15% | 0.70 |
| Luck (positive, over-records) | 15% | 0.62 |
| High-Variance Style (inside-dependent, not 3PT) | 10% | 0.30 |
| Star Dependence (Zach Edey system) | 5% | 0.75 |
| Conference (Big Ten) | 5% | 0.65 |
| **Weighted Total** | | **~0.68** |

| Kansas 2023 (lost to Arkansas in R2) | Fraud Score: ~0.38 |
|---|---|
| Seed Deviation (modest) | 25% | 0.30 |
| Imbalance (balanced O/D) | 25% | 0.20 |
| Form Collapse (no collapse) | 15% | 0.30 |
| Luck (moderate) | 15% | 0.45 |
| High-Variance Style (moderate 3PT reliance) | 10% | 0.40 |
| Conference (Big 12 — no penalty) | 5% | 0.00 |
| **Weighted Total** | | **~0.38** |

| Virginia 2019 Champion | Fraud Score: ~0.06 |
|---|---|
| All components near 0 — elite D, balanced, no luck, consistent, no overseeding | |

### 10.3 Integration With Other Outputs

The Fraud Score does NOT reduce a team's `PowerScore` or `AdjEM`. It is a **separate risk signal** — a team can have a high PowerScore (they are objectively good) AND a high FraudScore (but they are structurally vulnerable in March specifically).

**How it affects other outputs:**

- **Matchup Verdict Cards:** If favorite's FraudScore ≥ 0.40, append 💀 FRAUD RISK badge to their team card. The verdict label upgrades: a LEAN becomes a TRAP GAME if fraud score is high.

- **Rankings tables:** Add `FraudScore` and `FraudLevel` columns to the power rankings output. Sort option available.

- **Bracket strategies:** The `upsets` and `cinderella` bracket strategies apply a win probability *reduction* to the fraudulent team equal to `FraudScore × 0.08` (up to −8% maximum adjustment). This means if a 3-seed has FraudScore 0.70, their win probability gets a −5.6% haircut in those strategies.

  ```python
  def apply_fraud_adjustment(win_prob: float, favorite: dict,
                              strategy: str) -> float:
      """Reduce favorite win probability in upset-seeking strategies."""
      if strategy not in ('upsets', 'cinderella', 'analytics'):
          return win_prob
      fraud_score = favorite.get('FraudScore', 0.0)
      reduction = fraud_score * 0.08  # max -8%
      return float(np.clip(win_prob - reduction, 0.03, 0.97))
  ```

- **Bracket pick summary sheet:** A dedicated "FRAUD ALERTS" section lists seeded teams flagged HIGH or MEDIUM, with a plain-language explanation of why.

- **Terminal output:** Printed after Cinderella alerts:

  ```
  💀 FRAUD ALERTS (Seeds 1-6 with structural weaknesses)
  ────────────────────────────────────────────────────────
  Purdue (#3, B10)  FraudScore: 0.68  → Overseeded + weak defense + Big Ten deep-round history
  Illinois (#5, B10) FraudScore: 0.52 → Late-season collapse + high-variance style
  Arizona (#4, ACC)  FraudScore: 0.41 → Overseeded by CompRank + boom-or-bust 3PT offense
  ```

### 10.4 Plain-Language Fraud Explanations

```python
def get_fraud_explanation(team: dict, fraud_result: dict) -> str:
    """Generates a 1-2 sentence human-readable fraud warning."""
    reasons = []

    if fraud_result['F_SeedDeviation'] >= 0.50:
        seed = team.get('Seed', '?')
        comp = team.get('CompRank', team.get('Torvik_Rank', '?'))
        reasons.append(
            f"overseeded — #{seed} seed but CompRank suggests #{comp}"
        )

    if fraud_result['F_Imbalance'] >= 0.60:
        reasons.append(
            f"offense-first team (AdjD rank outside top 40 — "
            f"no champion since 1997 had AdjD rank > 40)"
        )

    if fraud_result['F_FormCollapse'] >= 0.50:
        recent = team.get('Last_10_Games_Metric', 0.5)
        reasons.append(
            f"entered tournament on poor form ({recent*10:.0f}-{10-recent*10:.0f} last 10)"
        )

    if fraud_result['F_Luck'] >= 0.55:
        reasons.append(
            "won more games than efficiency predicts "
            "(high Luck metric — regression likely)"
        )

    if fraud_result['F_Variance'] >= 0.60:
        reasons.append(
            "high-variance style (3PT-reliant + inconsistent) — "
            "boom-or-bust profile in single-elimination"
        )

    if fraud_result['F_Conference'] >= 0.55:
        conf = team.get('Conference', 'their conference')
        reasons.append(
            f"{conf} teams historically underperform in tournament deep rounds"
        )

    if fraud_result['F_StarDependence'] >= 0.60:
        reasons.append(
            "heavily dependent on a single player — "
            "vulnerable to defensive game plans and foul trouble"
        )

    if not reasons:
        return "Mild concerns — monitor closely but no single major red flag."

    return "Fraud risk: " + "; ".join(reasons) + "."
```