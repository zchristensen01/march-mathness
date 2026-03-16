# March Mathness - Algorithm Specification (Current)

This is the current algorithm spec aligned to `new_instructions.md`.
If any legacy doc conflicts with this file or `new_instructions.md`, treat the legacy doc as obsolete.

## Source of truth

- Primary: `new_instructions.md`
- Operational summary: this file

## Data model

The model operates on columns available in `data/teams_input.csv`.

Key supported columns:
- Core efficiency: `AdjO`, `AdjD`, `AdjEM`, `Barthag`, `Adj_T`
- Four factors: `eFG%`, `Opp_eFG%`, `TO%`, `Opp_TO%`, `OR%`, `DR%`, `FTR`, `Opp_FTR`, `FT%`, `2P%`, `2P_%_D`, `3P%`, `3P_%_D`, `3P_Rate`, `3P_Rate_D`, `Ast_%`, `Op_Ast_%`, `Blk_%`, `Blked_%`
- Rank systems: `Torvik_Rank`, `NET_Rank`, `Massey_Rank`, `CompRank`
- Resume/form: `SOS`, `Elite_SOS`, `WAB`, `Quad1_Wins`, `Last_10_Games_Metric`, `Luck`
- Tournament features: `Seed`, `Conf_Tourney_Champion`, `Won_Play_In`
- Context: `Coach_Tourney_Experience`, `Program_Prestige`, `Star_Player_Index`, `Exp`, `Bench_Minutes_Pct`

Unavailable metrics are not part of the scoring contract:
- `Avg_Hgt`, `Eff_Hgt`, venue-split efficiencies, road win percentage, returning tournament minutes

## Pipeline order

1. Ingest teams (`engine/ingestion.py`)
2. Apply defaults and alias normalization
3. Apply injury overrides from `data/overrides.json`
4. Apply coach scores from `data/coach_scores.json`
5. Normalize features (`engine/normalization.py`)
6. Compute derived features
7. Compute model rankings (`engine/scoring.py`)
8. Compute Cinderella/Fraud diagnostics
9. Compute win probabilities (`engine/win_probability.py`)
10. Run bracket simulation and strategy brackets
11. Write outputs

## Critical behavior changes

### No CSI multiplier

Conference strength multipliers are removed from ranking math.

Scoring is now:

```python
score = 100 * sum(weight_i * feature_i)
```

There is no `* CSI_multiplier` step.

### Injury override persistence

`AdjEM` overrides are preserved by translating the margin delta into paired `AdjO`/`AdjD` shifts before `AdjEM` recomputation.

### Conference penalties removed from fraud

No conference-prior penalty exists in fraud scoring.

## Normalization rules

- Higher-is-better: `(v - min) / (max - min)`
- Lower-is-better: `(max - v) / (max - min)`
- Missing values: `0.5` neutral

Notable ranges:
- `AdjEM`: [-20, 40], higher
- `AdjD`: [80, 125], inverse
- `SOS`: [1, 365], inverse
- `Star_Player_Index`: [1, 10], higher
- `Exp`: [0.5, 3.0], higher
- `Bench_Minutes_Pct`: [5, 30], neutral

## Core model weights

### PowerScore (`models/weights.json` -> `default`)

- `AdjEM`: 0.40
- `Barthag`: 0.05
- `CompRank_inv`: 0.06
- `NET_Rank_inv`: 0.02
- `Massey_Rank_inv`: 0.02
- `SOS_inv`: 0.06
- `eFG%`: 0.06
- `Opp_eFG%_inv`: 0.05
- `Opp_TO%`: 0.05
- `TO%_inv`: 0.03
- `OR%`: 0.03
- `DR%`: 0.02
- `FTR`: 0.02
- `FT%`: 0.02
- `Last_10_Games_Metric`: 0.04
- `Quad1_Wins`: 0.03
- `Star_Player_Index`: 0.02
- `Coach_Tourney_Experience`: 0.02

### Cinderella tournament model

- Includes `SeedMismatch_norm` as highest-weight signal (0.25)
- Includes `Exp` (0.02)
- Uses tempo suppression via `Adj_T_inv`

## Fraud score (seeds 1-6 only)

Composite:

```text
0.25*seed_deviation
+ 0.20*imbalance
+ 0.14*form_collapse
+ 0.12*luck
+ 0.10*variance
+ 0.05*dependence
+ 0.06*ftr_allowed
+ 0.08*rank_divergence
```

Where:
- `dependence` is increased by +0.10 (capped) if `Bench_Minutes_Pct < 10`
- `ftr_allowed` is normalized from `Opp_FTR` on [18, 50]

## Win probability

Primary win probability:

- `p_normal`: spread-based normal CDF
- `p_elo`: AdjEM logistic
- Blend: `0.60 * p_normal + 0.40 * p_elo`
- Clipped to `[0.03, 0.97]`

Additional adjustments:
- Historical seed priors
- Round-1 play-in bonus for `Won_Play_In`

## Outputs

Primary ranking outputs:
- `power_rankings.csv`
- `defensive_rankings.csv`
- `offensive_rankings.csv`
- `momentum_rankings.csv`
- `cinderella_rankings.csv`
- `giant_killer_rankings.csv`

No `conference_strength.csv` output is required in the current algorithm.
