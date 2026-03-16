# March Mathness

Research-backed NCAA tournament prediction engine that ingests team-level stats, computes multi-model scores, estimates matchup win probabilities, runs Monte Carlo bracket simulations, and produces ranked outputs + bracket artifacts for decision support.

For a chronological, command-by-command operator guide, start with:

- `documentation/START_HERE.md`

## Tech Stack

- Python 3.11+
- `pandas`, `numpy`, `scipy`, `scikit-learn`
- `Streamlit` for interactive UI
- `Jinja2` for static bracket HTML rendering
- `cloudscraper` for Torvik/Massey ingestion (Cloudflare-protected sources)

## Project Structure

```text
march-mathness/
├── app.py
├── main.py
├── config.json
├── requirements.txt
├── engine/
│   ├── ingestion.py
│   ├── normalization.py
│   ├── conference.py
│   ├── scoring.py
│   ├── win_probability.py
│   ├── simulation.py
│   ├── bracket_generator.py
│   ├── output.py
│   ├── calibration.py
│   ├── live_results.py
│   └── tournament_bonus.py
├── scripts/
│   ├── fetch_data.py
│   └── backtest.py
├── models/
│   ├── weights.json
│   └── conference_weights.json
├── data/
│   └── historical/
├── outputs/
│   ├── rankings/
│   ├── brackets/
│   └── dashboard/
├── templates/
│   └── bracket.html.j2
└── tests/
```

## Quick Start

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Fetch season data (Selection Sunday flow):

```bash
python scripts/fetch_data.py --year 2026
```

4. Add/verify:
- `data/teams_input.csv` seed values
- `data/bracket_input.json`
- `data/overrides.json` (optional injuries)
- `data/coach_scores.json` (optional but recommended)

5. Run full pipeline:

```bash
python main.py --mode full
```

6. Launch UI:

```bash
streamlit run app.py
```

## CLI Usage

```bash
# rankings only
python main.py --mode rankings

# full pipeline (rankings + simulation + strategy brackets)
python main.py --mode full

# simulate mode (expects bracket + rankings input data available)
python main.py --mode simulate

# mid-tournament update mode
python main.py --mode update

# reproducibility overrides
python main.py --mode full --seed 123 --sims 20000
```

## Data Contracts

### Required inputs

- `data/teams_input.csv`
- `data/bracket_input.json` (for full/simulate/update modes)

### Optional inputs

- `data/overrides.json` for injury/manual adjustments
- `data/tournament_results.json` fallback for mid-tournament updates
- `data/coach_scores.json`

### Core validation behavior

- Strict required-column checks in `engine/ingestion.py`
- Alias normalization for known source variations (`wAB -> WAB`, etc.)
- Deterministic defaults (no random defaults)
- Explicit errors for malformed bracket payloads and seed ranges

## Engine Pipeline

1. **Ingestion**: alias mapping, default filling, luck computation, override application, schema validation
2. **Normalization**: direction-correct min/max normalization and derived feature computation
3. **Scoring Prep**: ranking feature prep and derived metrics (no CSI multiplier)
4. **Scoring**: 9 weight models + Cinderella and Fraud meta-signals
5. **Win probability**: normal-CDF + Elo blend + era seed priors + clipping
6. **Simulation**: Monte Carlo advancement probabilities
7. **Bracket generation**: deterministic 8-strategy bracket outputs
8. **Output**: ranking CSVs, bracket JSON/HTML, simulation JSON, pick sheet, matchup verdicts

## Outputs

Generated under `outputs/`:

- `outputs/rankings/*_rankings.csv`
- `outputs/brackets/bracket_<strategy>.json`
- `outputs/brackets/bracket_<strategy>.html`
- `outputs/simulation_results.json`
- `outputs/bracket_summary.json`
- `outputs/bracket_matchup_verdicts.json`
- `outputs/my_bracket_picks.txt`

## Mid-Tournament Updates

`main.py --mode update`:

- Pulls completed games from ESPN API when available
- Falls back to manual `data/tournament_results.json`
- Applies giant-killer / momentum bonuses for surviving teams
- Re-runs scores and simulation on updated field

## Testing

Run all tests:

```bash
pytest tests/
```

Current test coverage includes:

- normalization directions and bounds
- probability clipping and seed-prior blending behavior
- score scope guards (Cinderella/Fraud seed bounds)
- simulation probability sanity checks

## Backtesting

Place historical inputs in:

- `data/historical/<year>_teams.csv`
- `data/historical/<year>_games.csv`

Run:

```bash
python scripts/backtest.py --years 2022 2023 2024
```

## Performance Notes

- Simulation loop is dict-based and seeded (`random` + `numpy`) for reproducibility
- Probability clipping prevents pathological overconfidence
- CSI multiplier is residual (not a replacement for AdjEM)
- Outputs are precomputed to keep UI rendering lightweight

## Security and Operational Notes

- No secrets are hardcoded
- Environment-specific settings can be supplied via `.env` as needed
- Error handling is explicit for malformed data contracts and fetch failures
- ESPN fetches are wrapped with fallback behavior for restricted environments

