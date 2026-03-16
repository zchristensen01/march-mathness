# Full Pipeline Integrity Audit

Run this audit end-to-end. Do NOT skip steps. Report every finding.

## Context

This project is a March Madness prediction engine. Data flows from automated fetching + Claude Research prompts → CSV/JSON files → ingestion → normalization → scoring → simulation. Multiple structural bugs were found and fixed on 2026-03-15 (missing _inv aliases, PPP never computed, coach_scores.json never loaded, placeholder columns missing). This audit verifies nothing else is broken.

## Step 1: Trace every model weight input to a data source

Open `models/weights.json`. For every key across all 9 models (default, defensive, offensive, momentum, giant_killer, cinderella_tournament, favorites, analytics, experience), answer:
- Where does this value come from? (auto-fetched in fetch_data.py, computed in ingestion.py, prompt output, derived in normalization.py)
- If it ends in `_inv`, does the base key exist in `FEATURE_RANGES` and does an alias get created in `normalize_team()` in `engine/normalization.py`?
- If it's a derived feature name (like Physicality, BallMovement, etc.), verify all its sub-inputs resolve to real data, not 0.5 defaults.

Flag any weight input that resolves to a constant value for all teams (zero discriminating power).

## Step 2: Trace every prompt output into the code

For each prompt file in `documentation/prompts/01-06`:
1. Read the prompt and identify the exact output columns/format
2. Read the "WHAT TO DO WITH THE OUTPUT" section and identify where data goes
3. Verify the destination file is actually loaded by `main.py` or `engine/ingestion.py`
4. Verify the column names in the prompt match the column names the code expects (check `FEATURE_RANGES`, `DEFAULTS`, `REQUIRED_COLUMNS`, `ALIAS_MAP` in ingestion.py)
5. Verify the column exists as a placeholder in `teams_input.csv` (check `SCHEMA_COLUMNS` and `PLACEHOLDER_COLUMNS` in `scripts/fetch_data.py`)

## Step 3: Verify config.json paths are all used

Read `config.json`. For each file path key (data_file, bracket_file, overrides_file, coach_scores_file, results_file), verify `main.py` actually reads and uses that file. Report any config keys that point to files that are never loaded.

## Step 4: Verify ingestion defaults vs normalization ranges

Read `DEFAULTS` in `engine/ingestion.py` and `FEATURE_RANGES` in `engine/normalization.py`. For each default value, verify it falls within the normalization range. A default outside the range would normalize to 0.0 or 1.0 which is wrong for a "neutral" default.

## Step 5: Run the verification code

```python
import pandas as pd
import json
import sys
sys.path.insert(0, '.')
from engine.ingestion import load_teams
from engine.normalization import (
    normalize_team, compute_derived_features, FEATURE_RANGES,
    normalize_all_teams, compute_consistency_score, compute_volatility_score,
    normalize_value
)
from engine.scoring import generate_all_rankings, seed_mismatch

df = load_teams('data/teams_input.csv')

# Check 1: All FEATURE_RANGES keys that are "inverse" have _inv aliases
duke = df[df['Team'] == 'Duke'].iloc[0]
norm = normalize_team(duke.to_dict())
for feature, (lo, hi, direction) in FEATURE_RANGES.items():
    if direction == "inverse":
        inv_key = f"{feature}_inv"
        if inv_key not in norm:
            print(f"WARNING: {inv_key} not in normalized output")

# Check 2: All model weight keys resolve (after adding SeedMismatch_norm)
weights = json.loads(open('models/weights.json').read())
seed_val = pd.to_numeric(pd.Series([duke.get("Seed")]), errors="coerce").iloc[0]
comp_val = pd.to_numeric(pd.Series([duke.get("CompRank")]), errors="coerce").iloc[0]
if pd.notna(seed_val) and pd.notna(comp_val):
    norm["SeedMismatch_norm"] = normalize_value(
        seed_mismatch(int(seed_val), int(comp_val)), 0, 1
    )
derived = compute_derived_features(norm)
all_norm = {**norm, **derived}
for model_name, model_weights in weights['models'].items():
    for key in model_weights:
        if key not in all_norm:
            print(f"MISSING: model '{model_name}' references '{key}' which is not in normalized+derived output")
        elif abs(all_norm[key] - 0.5) < 0.001:
            print(f"FLAT: model '{model_name}' key '{key}' = 0.5 (no discriminating power)")

# Check 3: PPP_Off and PPP_Def exist
assert 'PPP_Off' in df.columns, "PPP_Off missing from ingested data"
assert 'PPP_Def' in df.columns, "PPP_Def missing from ingested data"

# Check 4: All prompt-output columns exist in CSV
prompt_cols = ['Seed', 'NET_Rank', 'Quad1_Wins', 'Last_10_Games_Metric',
               'Conf_Tourney_Champion', 'Star_Player_Index']
for col in prompt_cols:
    assert col in df.columns, f"Prompt-output column '{col}' missing from CSV"

# Check 5: coach_scores.json is loaded by main.py
main_src = open('main.py').read()
assert 'coach_scores' in main_src, "main.py does not reference coach_scores"

# Check 6: Full scoring produces non-degenerate output
norms = normalize_all_teams(df)
deriveds_list = [compute_derived_features(n) for n in norms]
for i, (_, row) in enumerate(df.iterrows()):
    row_dict = row.to_dict()
    norms[i]['Consistency_Score'] = compute_consistency_score(row_dict)
    norms[i]['Volatility_Score'] = compute_volatility_score(row_dict, norms[i])
    s = pd.to_numeric(pd.Series([row_dict.get("Seed")]), errors="coerce").iloc[0]
    c = pd.to_numeric(pd.Series([row_dict.get("CompRank")]), errors="coerce").iloc[0]
    if pd.notna(s) and pd.notna(c):
        norms[i]["SeedMismatch_norm"] = normalize_value(seed_mismatch(int(s), int(c)), 0, 1)

rankings = generate_all_rankings(df, norms, deriveds_list)
for model_name, rdf in rankings.items():
    score_col = 'PowerScore' if model_name == 'power' else 'ModelScore'
    if score_col in rdf.columns:
        std = rdf[score_col].std()
        if std < 1.0:
            print(f"DEGENERATE: model '{model_name}' has std={std:.3f} (scores too similar)")

print("Audit complete.")
```

## Step 6: Check bracket_input.json schema

Read `engine/ingestion.py load_bracket()` and verify the required fields match what prompt 02 asks Claude to produce. Check: team, seed, region, slot, play_in, play_in_opponent.

## Step 7: Check overrides.json schema

Read `engine/ingestion.py apply_overrides()` and verify the expected JSON structure matches what prompt 05 asks Claude to produce. Check: mode (delta vs absolute), field names, nested structure.

## What to report

For each step, report:
- ✓ if everything checks out
- ✗ with specific details if something is broken
- ⚠ with explanation if something defaults but is acceptable

Do NOT silently skip any step. If a check passes, say so explicitly.
