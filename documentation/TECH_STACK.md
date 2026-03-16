# March Mathness — Tech Stack

**Guiding constraint:** Solo build, ~20 hours, zero infrastructure cost, maximum algorithmic sophistication.

---

## Decision Summary

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | **Python 3.11+** | Scientific computing ecosystem; scikit-learn, scipy, numpy all needed |
| Entry point | **`main.py`** CLI | Simple, portable, no server required for core pipeline |
| UI | **Streamlit** | ~2 hours to build a world-class interactive UI; or static HTML if preferred |
| Data | **pandas** | CSV ingestion, manipulation, normalization |
| Math | **numpy + scipy** | Matrix ops, normal CDF, optimization (WIN50) |
| Probability calibration | **scikit-learn** | `LogisticRegression`, `IsotonicRegression` |
| Bracket viz | **Jinja2 templates** | Renders bracket HTML artifacts without frontend framework |
| Config | **JSON** | Human-editable config files; no YAML complexity |
| Output | **CSV + JSON + HTML** | Maximum compatibility; no DB required |
| Dependency mgmt | **pip + requirements.txt** | No conda, no Docker |

---

## Why Python, Not Node/JS

The previous system used Node.js. For a math-heavy pipeline, Python is strongly preferred because:
- `scipy.stats.norm.cdf()` — exact normal CDF for win probability (in Node you'd implement it manually)
- `scipy.optimize.brentq()` — needed for WIN50 conference rating solver
- `sklearn.linear_model.LogisticRegression` — calibrated probability model
- `sklearn.isotonic.IsotonicRegression` — probability calibration
- `numpy` vectorized operations — 10,000 Monte Carlo simulations run in <5 seconds

If a web frontend is desired beyond Streamlit, the Python pipeline can expose a simple Flask/FastAPI endpoint that the frontend hits. But for a 20-hour build, Streamlit is the highest-leverage UI choice.

---

## Directory Structure

```
march_mathness/
├── main.py                    # CLI entry point: runs full pipeline
├── config.json                # All tunable parameters
├── requirements.txt
│
├── data/
│   ├── teams_input.csv        # Primary input (assembled from Torvik + ESPN + Massey)
│   ├── bracket_input.json     # Post-bracket: seeds, regions, slots
│   ├── overrides.json         # Injury/manual adjustments
│   └── historical/            # Past tournament CSVs for calibration
│       ├── 2023_teams.csv
│       ├── 2024_teams.csv
│       └── ...
│
├── engine/
│   ├── __init__.py
│   ├── ingestion.py           # CSV parsing, validation, alias normalization
│   ├── normalization.py       # Min-max normalization, inverse normalization
│   ├── conference.py          # Legacy/unused in active scoring pipeline
│   ├── scoring.py             # All model scoring (power, cinderella, etc.)
│   ├── win_probability.py     # AdjEM-based logistic win prob function
│   ├── simulation.py          # Monte Carlo bracket simulation
│   ├── bracket_generator.py   # 8 strategy bracket builders
│   └── calibration.py        # Isotonic regression calibration (optional)
│
├── models/
│   ├── weights.json           # All model weight dictionaries (external, tunable)
│   └── conference_weights.json # Legacy config (not used by active pipeline)
│
├── outputs/                   # All generated artifacts land here
│   ├── rankings/
│   ├── brackets/
│   └── dashboard/
│
├── templates/
│   ├── bracket.html.j2        # Jinja2 bracket visualization template
│   └── dashboard.html.j2      # Main dashboard template
│
└── tests/
    ├── test_scoring.py
    ├── test_win_probability.py
    └── test_simulation.py
```

---

## `requirements.txt`

```
pandas==2.2.0
numpy==1.26.4
scipy==1.12.0
scikit-learn==1.4.0
streamlit==1.31.0
jinja2==3.1.3
requests==2.31.0
cloudscraper==1.2.71
python-dotenv==1.0.0
pytest==8.0.0
```

`cloudscraper` is required for Torvik and Massey (Cloudflare protection). Everything installs in under 2 minutes with:

```bash
pip install -r requirements.txt
```

---

## Module Responsibilities

### `engine/ingestion.py`
- `load_teams(csv_path, overrides_path) -> pd.DataFrame`
- `validate_columns(df) -> List[str]`  (returns list of missing required columns)
- `apply_overrides(df, overrides_dict) -> pd.DataFrame`
- `normalize_aliases(df) -> pd.DataFrame`  (maps alternate column names to canonical names)

### `engine/normalization.py`
- `normalize_value(v, min_val, max_val) -> float`  (0-1, higher is better)
- `normalize_inverse(v, min_val, max_val) -> float`  (0-1, lower raw is better)
- `normalize_all_features(df) -> pd.DataFrame`  (applies correct direction per feature)
- Defines `FEATURE_RANGES: Dict[str, Tuple[float, float, str]]`  (name → (min, max, direction))

### `engine/conference.py`
- Legacy module kept for historical reference; current scoring path does not call it

### `engine/scoring.py`
- `score_all_teams(df, weights_dict, model_name) -> pd.DataFrame`
- `score_team(team_row, weights, norm_df) -> float`
- `compute_cinderella_score(team_row, norm_df) -> Dict`  (returns component breakdown)
- `get_team_strengths(team_row) -> List[str]`  (plain-language labels)
- `generate_all_rankings(df) -> Dict[str, pd.DataFrame]`  (all 6 tables)

### `engine/win_probability.py`
- `win_probability(team_a: dict, team_b: dict) -> float`  (P that team_a wins)
- `predicted_spread(team_a, team_b) -> float`  (expected point differential)
- `win_prob_from_adjEM(adjEM_diff: float, avg_tempo: float, std_dev=11.0) -> float`
- `all_matchup_probabilities(teams: List[dict]) -> pd.DataFrame`  (n×n matrix)

### `engine/simulation.py`
- `simulate_bracket(bracket: List[dict], win_prob_fn, n_sims=10000, seed=42) -> Dict`
- Returns: `{team_name: {round_name: probability}}` for all rounds
- Also returns: `modal_bracket` (most likely winner per game across simulations)

### `engine/bracket_generator.py`
- `generate_all_brackets(teams, simulation_results, strategy_configs) -> Dict`
- `generate_bracket(teams, simulation_results, strategy: str) -> Dict`
- `strategy_configs` loaded from `models/weights.json`

---

## CLI Usage

```bash
# Full pipeline (rankings + brackets)
python main.py --mode full

# Rankings only (no bracket needed)
python main.py --mode rankings

# Run with a specific random seed for reproducibility
python main.py --mode full --seed 123

# Launch Streamlit UI
streamlit run app.py
```

---

## Streamlit UI Structure (if building UI)

```
app.py
├── Sidebar: Upload CSV, upload bracket, upload overrides, Run button
├── Tab 1: 📊 Power Rankings  (sortable table, color-coded scores)
├── Tab 2: 📈 Team Traits  (single-metric leaderboards)
├── Tab 3: 🔮 Cinderella Scores  (filtered to seed 9+, alert badges)
├── Tab 4: 💀 Fraud Alerts  (seeds 1-6)
├── Tab 5: 🎯 Matchup Calculator  (two-team selector → win probability)
├── Tab 6: 🎲 Bracket Simulation  (strategy selector, round probs)
├── Tab 7: 📋 Bracket Strategies
└── Tab 8: 📄 Pick Sheet
```

---

## Static HTML Alternative (if not using Streamlit)

If skipping Streamlit, `main.py` generates a standalone `tournament_dashboard.html` via Jinja2 that includes all tables and bracket visualizations as inline HTML/CSS/JS. This file can be opened directly in a browser with no server. Chart.js is loaded from CDN for any charts.

---

## Data Source Tools (one-time setup)

**⚠️ Torvik and Massey require `cloudscraper` — plain `requests.get()` returns 403 Forbidden (Cloudflare protection).**

The official data fetching path is `scripts/fetch_data.py` (full implementation in `API_DATA_SOURCES.md` Section 9). It handles all sources, merging, and saving to `data/teams_input.csv`. Run it once before the main pipeline.

Quick-test snippet (requires `cloudscraper`):

```python
import cloudscraper, pandas as pd, io

def fetch_torvik(year=2026):
    scraper = cloudscraper.create_scraper()
    url = f"http://barttorvik.com/{year}_team_results.csv"
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))
```

---

## Testing Strategy

- `pytest tests/` runs all unit tests
- Key test: `test_win_probability.py` validates that P(1-seed beats 16-seed) > 0.97 and P(8-seed beats 9-seed) is between 0.45 and 0.55
- Key test: `test_scoring.py` validates score ranges and that higher-ranked teams get higher scores
- Key test: `test_simulation.py` validates that simulation probabilities sum to 1.0 across all teams per round
- Historical backtest: `scripts/backtest.py` runs the model against 2022, 2023, 2024 tournaments and reports accuracy vs seed-only baseline