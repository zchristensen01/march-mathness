# March Mathness - Data Schema (Current)

This schema reflects the active pipeline and supersedes legacy schema notes.

## Primary input

`data/teams_input.csv` with one row per team.

## Required ingestion columns

The ingestion guard requires these columns:

- `Team`
- `AdjO`
- `AdjD`
- `Barthag`
- `eFG%`
- `Opp_eFG%`
- `TO%`
- `Opp_TO%`
- `OR%`
- `SOS`
- `Adj_T`

## Active scoring columns

The following columns are used by normalization, derived features, scoring, and probability logic:

- Identity/context: `Team`, `Conference`, `Record`, `Wins`, `Games`, `Seed`
- Efficiency core: `AdjO`, `AdjD`, `AdjEM`, `Barthag`, `Adj_T`
- Four factors + adjacents:
  - `eFG%`, `Opp_eFG%`, `TO%`, `Opp_TO%`, `OR%`, `DR%`, `Opp_OR%`
  - `FTR`, `Opp_FTR`, `FT%`
  - `2P%`, `2P_%_D`, `3P%`, `3P_%_D`, `3P_Rate`, `3P_Rate_D`
  - `Blk_%`, `Blked_%`, `Ast_%`, `Op_Ast_%`
- Resume/ranks: `SOS`, `Elite_SOS`, `WAB`, `Torvik_Rank`, `NET_Rank`, `Massey_Rank`, `CompRank`
- Trend/form: `TRank_Early`, `RankTrajectory`, `Last_10_Games_Metric`, `Luck`
- Tournament/qualitative: `Quad1_Wins`, `Conf_Tourney_Champion`, `Won_Play_In`
- Personnel/context: `Coach_Tourney_Experience`, `Program_Prestige`, `Star_Player_Index`, `Exp`, `Bench_Minutes_Pct`

## Removed or unsupported columns

These are no longer part of the active schema contract:

- `Conf_Strength_Weight`
- `Avg_Hgt`
- `Eff_Hgt`
- `AST_TO` (not required by the current scoring path)

## Defaults

Applied by `engine/ingestion.py` when missing:

- `Seed = 10`
- `Conference = "Unknown"`
- `Star_Player_Index = 5.0`
- `Last_10_Games_Metric = 0.65`
- `Massey_Rank = 150`
- `Elite_SOS = 10.0`
- `Quad1_Wins = 3`
- `AP_Poll_Rank = 26`
- `Coach_Tourney_Experience = 3.0`
- `Program_Prestige = 2.0`
- `WAB = 2.0`
- `Conf_Tourney_Champion = 0`
- `Won_Play_In = 0`
- `Exp = 2.0`
- `Bench_Minutes_Pct = 15.0`

## Coach scores input

`data/coach_scores.json`:

```json
{
  "_default": 3,
  "Team Name": 7.5
}
```

Behavior:
- `main.py` applies this map to overwrite `Coach_Tourney_Experience`
- Teams missing explicit entries receive `_default`

## Injury overrides input

`data/overrides.json`:

```json
{
  "Team Name": {
    "mode": "delta",
    "AdjEM": -3.5,
    "Star_Player_Index": -2.0,
    "note": "optional context"
  }
}
```

Rules:
- `mode` is `delta` or `absolute`
- Numeric keys matching team columns are applied
- `OverrideActive` is set to `1` for modified teams
- `AdjEM` overrides are translated into `AdjO`/`AdjD` adjustments so override effects persist after recomputation

## fetch_data contract

`scripts/fetch_data.py` must keep placeholders for prompt-driven/manual fields:

- `Seed`
- `NET_Rank`
- `Quad1_Wins`
- `Last_10_Games_Metric`
- `Conf_Tourney_Champion`
- `Won_Play_In`
- `Star_Player_Index`
- `Elite_SOS`
- `Exp`
- `Bench_Minutes_Pct`

## Output notes

- Rankings no longer include conference-strength multiplier outputs.
- `conference_strength.csv` is not part of the current required output set.
