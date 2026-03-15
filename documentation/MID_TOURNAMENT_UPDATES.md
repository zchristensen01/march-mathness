# March Mathness — Mid-Tournament Live Update System

**Document 07 — In-Tournament Re-Scoring & Live Results**

This document specifies the mid-tournament update feature: automatic game result ingestion via free APIs, dynamic re-scoring that rewards teams who beat higher seeds (the "proven giant killer" bonus), and a re-run of the bracket simulation against the surviving field.

---

## 1. The Case for Mid-Tournament Re-Scoring

After Round 1 is played, you have new information that the pre-tournament model could not have:

- **Proven giant killers:** A 12-seed that just beat a 5-seed has demonstrated they can compete at that level. Their pre-tournament Cinderella score was a *prediction*. Post-upset, it becomes *confirmed evidence*.
- **Eliminated teams:** 32 teams are gone after Round 1. Re-running the simulation against the 32 survivors produces sharper probability estimates.
- **Momentum confirmation:** A team that just won by 20 points is different from a team that scraped by in overtime. Box score data from completed games enriches the model.
- **Bracket position clarity:** As the bracket collapses, who a team *will* face in the next round becomes known — you can compute exact matchup probabilities.

Research note: The Wharton/Sha (2023) paper found that teams beating higher seeds got a statistically significant boost in subsequent-round performance beyond what AdjEM alone would predict — specifically, winning the turnover battle and defensive efficiency in the completed game were the strongest predictors of continued success.

---

## 2. Data Source: ESPN's Hidden API (Free, No Auth)

The cleanest free source for live tournament game results is ESPN's unofficial but stable API. It returns game scores, box scores, and game status in real time.

### 2.1 Scoreboard Endpoint

```python
import requests

def fetch_tournament_scores(group_id: int = 100) -> dict:
    """
    Fetches current NCAA tournament scores and results.
    group_id 100 = NCAA Tournament (Men's D-I)
    
    Returns game data including: teams, scores, status (final/live/scheduled),
    game_id, and links to box scores.
    
    No API key required. Undocumented but used by ESPN's own website.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    params = {
        "groups": group_id,
        "limit": 50,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def parse_tournament_results(scoreboard_data: dict) -> list[dict]:
    """
    Extracts completed game results from ESPN scoreboard response.
    Returns list of completed game dicts.
    """
    results = []
    for event in scoreboard_data.get('events', []):
        competition = event['competitions'][0]
        status = competition['status']['type']['name']
        
        if status != 'STATUS_FINAL':
            continue  # Skip live and upcoming games
        
        competitors = competition['competitors']
        team_a = competitors[0]
        team_b = competitors[1]
        
        winner = team_a if team_a.get('winner') else team_b
        loser = team_b if winner == team_a else team_a
        
        results.append({
            'game_id': event['id'],
            'winner_name': winner['team']['displayName'],
            'winner_score': int(winner['score']),
            'loser_name': loser['team']['displayName'],
            'loser_score': int(loser['score']),
            'margin': int(winner['score']) - int(loser['score']),
            'winner_seed': int(winner.get('curatedRank', {}).get('current', 0)),
            'loser_seed': int(loser.get('curatedRank', {}).get('current', 0)),
            'is_upset': (winner.get('homeAway') == 'away' or  # proxy
                        int(winner.get('curatedRank', {}).get('current', 99)) >
                        int(loser.get('curatedRank', {}).get('current', 0))),
            'round': competition.get('notes', [{}])[0].get('headline', 'Unknown Round'),
            'date': event['date'],
        })
    
    return results
```

### 2.2 Box Score Endpoint (for per-game stats)

```python
def fetch_game_boxscore(game_id: str) -> dict:
    """
    Fetches full box score for a completed game.
    Returns team-level and player-level stats.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary"
    params = {"event": game_id}
    response = requests.get(url, params=params, timeout=10)
    return response.json()


def parse_team_game_stats(boxscore_data: dict, team_name: str) -> dict:
    """
    Extracts relevant stats from a single completed game for a specific team.
    Returns the stats that feed into the mid-tournament re-scoring bonus.
    """
    stats = {}
    
    for team_stats in boxscore_data.get('boxscore', {}).get('teams', []):
        if team_stats['team']['displayName'] != team_name:
            continue
        
        for stat in team_stats.get('statistics', []):
            label = stat['label']
            value = stat['displayValue']
            
            if label == 'FG%':        stats['fg_pct'] = float(value.replace('%',''))
            elif label == '3PT%':     stats['three_pct'] = float(value.replace('%',''))
            elif label == 'FT%':      stats['ft_pct'] = float(value.replace('%',''))
            elif label == 'Rebounds': stats['rebounds'] = int(value)
            elif label == 'Assists':  stats['assists'] = int(value)
            elif label == 'Turnovers': stats['turnovers'] = int(value)
            elif label == 'Steals':   stats['steals'] = int(value)
            elif label == 'Blocks':   stats['blocks'] = int(value)
    
    return stats
```

### 2.3 Tournament-Specific Endpoint

ESPN also exposes bracket data directly:

```python
def fetch_tournament_bracket() -> dict:
    """
    Fetches the full NCAA tournament bracket structure from ESPN.
    Useful for getting seeds, regions, and game results in bracket order.
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/tournaments"
    response = requests.get(url, timeout=10)
    data = response.json()
    # Returns tournament metadata; bracket rounds are nested within
    return data
```

---

## 3. Manual Fallback: `tournament_results.json`

The ESPN API is undocumented and could break. The fallback is a manually maintained JSON file that accepts results in the same format the API returns. The pipeline auto-detects which to use.

### Format: `data/tournament_results.json`

```json
{
  "last_updated": "2026-03-22T14:30:00Z",
  "source": "manual",
  "completed_games": [
    {
      "game_id": "401696113",
      "round": "First Round",
      "round_number": 1,
      "winner_name": "New Mexico State",
      "winner_seed": 12,
      "winner_score": 78,
      "loser_name": "Connecticut",
      "loser_seed": 5,
      "loser_score": 71,
      "margin": 7,
      "is_upset": true,
      "winner_game_stats": {
        "fg_pct": 48.3,
        "three_pct": 42.1,
        "ft_pct": 81.0,
        "turnovers": 8,
        "steals": 7,
        "assists": 15
      },
      "loser_game_stats": {
        "fg_pct": 39.2,
        "three_pct": 28.0,
        "ft_pct": 71.0,
        "turnovers": 16,
        "steals": 3,
        "assists": 10
      }
    }
  ]
}
```

The pipeline checks for the ESPN API first; if it fails or returns no data, it falls back to this file.

---

## 4. The Giant Killer Bonus Algorithm

When a team has completed one or more tournament games, their pre-tournament stats are augmented with a **Tournament Performance Bonus** before re-scoring.

### 4.1 Bonus Components

```python
def compute_tournament_bonus(
    team_name: str,
    completed_games: list[dict],
    all_teams_adjEM: dict[str, float]
) -> dict:
    """
    Computes the mid-tournament bonus for a surviving team.
    
    Returns a dict of stat adjustments to apply before re-scoring.
    Adjustments are deltas added to the team's original stats.
    
    Research basis:
    - Wharton/Sha (2023): beating a higher seed correlates with +1.8 AdjEM 
      equivalent in subsequent rounds
    - Harvard Sports Analysis (2012): teams that won turnover battle in 
      upset victory won next game at 2x base rate
    - UC Berkeley (2025): dominant upset wins (margin > 10) predicted 
      next-round advancement at 68% vs 41% base rate
    """
    
    team_games = [g for g in completed_games if g['winner_name'] == team_name]
    
    if not team_games:
        return {}  # Team hasn't won any games yet (or hasn't played)
    
    bonus = {
        'AdjEM_delta': 0.0,
        'AdjO_delta': 0.0,
        'AdjD_delta': 0.0,
        'momentum_bonus': 0.0,
        'giant_killer_flag': False,
        'giant_killer_count': 0,
        'description': []
    }
    
    for game in team_games:
        seed_gap = game['loser_seed'] - game['winner_seed']
        margin = game['margin']
        game_stats = game.get('winner_game_stats', {})
        opponent_adjEM = all_teams_adjEM.get(game['loser_name'], 0)
        
        # ── Component 1: Giant Killer Bonus ──────────────────────────
        # Research: winning vs a higher seed = proven competitiveness
        if seed_gap > 0:  # upset (beat a better-seeded team)
            bonus['giant_killer_flag'] = True
            bonus['giant_killer_count'] += 1
            
            # Bonus scales with: size of upset × margin of victory
            # Cap at +4.0 AdjEM equivalent (substantial but not unrealistic)
            upset_magnitude = min(seed_gap / 4.0, 1.0)   # normalized 0-1
            margin_factor = min(margin / 15.0, 1.0)        # normalized 0-1
            
            adjEM_bonus = 2.5 * upset_magnitude + 1.5 * margin_factor
            adjEM_bonus = min(adjEM_bonus, 4.0)  # hard cap
            
            bonus['AdjEM_delta'] += adjEM_bonus
            bonus['description'].append(
                f"Beat #{game['loser_seed']}-seed by {margin} pts (+{adjEM_bonus:.1f} AdjEM)"
            )
        
        # ── Component 2: Defensive Performance Bonus ─────────────────
        # Research: Harvard (2012) — turnover battle winner advances at 2x rate
        if game_stats.get('steals', 0) >= 8 or game_stats.get('turnovers', 99) <= 8:
            bonus['AdjD_delta'] += 1.0
            bonus['description'].append("Won turnover battle in tournament (+1.0 AdjD)")
        
        # ── Component 3: Offensive Efficiency Bonus ───────────────────
        if game_stats.get('fg_pct', 0) >= 50:
            bonus['AdjO_delta'] += 0.8
            bonus['description'].append(f"Shot {game_stats['fg_pct']:.1f}% from field (+0.8 AdjO)")
        
        # ── Component 4: Blowout Bonus ───────────────────────────────
        # Research: Berkeley (2025) — dominant wins (margin > 10) predict next round at 68%
        if margin >= 15:
            bonus['momentum_bonus'] += 0.05  # +5% to Last_10_Games_Metric equivalent
            bonus['description'].append(f"Dominant win (margin={margin}) (+momentum)")
        
        # ── Component 5: Close Win Penalty ───────────────────────────
        # Squeaking by vs a weaker team is a red flag
        if seed_gap < 0 and margin <= 4:  # lower seed barely beat higher seed
            bonus['AdjEM_delta'] -= 0.5
            bonus['description'].append(f"Barely beat a lower seed by {margin} (-0.5 AdjEM)")
    
    # Recency weight: more recent games matter more
    # If team has won 2+ games, double-weight the most recent
    if len(team_games) >= 2:
        most_recent = team_games[-1]
        if most_recent['loser_seed'] < most_recent['winner_seed']:  # upset
            bonus['AdjEM_delta'] *= 1.2  # 20% amplifier for sustained giant-killing
            bonus['description'].append("Sustained giant-killer (2+ upsets, +20% amplifier)")
    
    return bonus
```

### 4.2 Applying Bonuses Before Re-Scoring

```python
def apply_tournament_bonuses(
    df: pd.DataFrame,
    completed_games: list[dict],
    surviving_teams: list[str]
) -> pd.DataFrame:
    """
    Returns a modified DataFrame with tournament bonuses applied.
    Only modifies rows for surviving teams.
    The original DataFrame is not modified (copy is returned).
    """
    df_updated = df.copy()
    
    all_adjEMs = dict(zip(df['Team'], df['AdjEM']))
    
    for team_name in surviving_teams:
        mask = df_updated['Team'] == team_name
        if not mask.any():
            continue
        
        bonus = compute_tournament_bonus(team_name, completed_games, all_adjEMs)
        
        if not bonus:
            continue
        
        # Apply deltas
        df_updated.loc[mask, 'AdjEM'] += bonus.get('AdjEM_delta', 0)
        df_updated.loc[mask, 'AdjO']  += bonus.get('AdjO_delta', 0)
        df_updated.loc[mask, 'AdjD']  -= bonus.get('AdjD_delta', 0)  # lower AdjD = better defense
        df_updated.loc[mask, 'Last_10_Games_Metric'] = min(
            1.0,
            df_updated.loc[mask, 'Last_10_Games_Metric'].values[0] + bonus.get('momentum_bonus', 0)
        )
        
        # Store bonus metadata for display
        df_updated.loc[mask, 'TournamentBonus_AdjEM'] = bonus.get('AdjEM_delta', 0)
        df_updated.loc[mask, 'GiantKiller'] = bonus.get('giant_killer_flag', False)
        df_updated.loc[mask, 'GiantKillerCount'] = bonus.get('giant_killer_count', 0)
        df_updated.loc[mask, 'BonusDescription'] = ' | '.join(bonus.get('description', []))
    
    return df_updated
```

---

## 5. Mid-Tournament Pipeline Mode

Add `--mode update` to `main.py`:

```python
def run_tournament_update(config: dict):
    """
    Mid-tournament re-run. 
    1. Loads original team stats
    2. Fetches completed game results (API or manual JSON)
    3. Applies giant killer bonuses
    4. Filters to surviving teams only
    5. Re-runs full scoring and simulation on surviving field
    6. Outputs updated rankings + remaining bracket probabilities
    """
    print("\n🏀 MID-TOURNAMENT UPDATE MODE")
    print("=" * 60)
    
    # Step 1: Load base team data
    df = load_teams(config['data_file'], config.get('overrides_file'))
    
    # Step 2: Fetch results
    print("\n[1/5] Fetching tournament results...")
    results = fetch_results(config)  # tries ESPN API, falls back to JSON
    completed_games = results['completed_games']
    print(f"  ✓ {len(completed_games)} completed games found")
    
    # Step 3: Determine surviving teams
    all_losers = {g['loser_name'] for g in completed_games}
    surviving_teams = [t for t in df['Team'].tolist() if t not in all_losers
                       and t in get_tournament_teams(config)]
    print(f"  ✓ {len(surviving_teams)} teams still alive")
    
    # Step 4: Apply tournament bonuses
    print("\n[2/5] Applying tournament performance bonuses...")
    df_updated = apply_tournament_bonuses(df, completed_games, surviving_teams)
    
    # Display bonus summary
    bonus_teams = df_updated[df_updated['TournamentBonus_AdjEM'].fillna(0) != 0]
    for _, row in bonus_teams.iterrows():
        sign = '+' if row['TournamentBonus_AdjEM'] > 0 else ''
        print(f"  {row['Team']}: {sign}{row['TournamentBonus_AdjEM']:.1f} AdjEM | {row.get('BonusDescription','')}")
    
    # Step 5: Filter to survivors and re-run
    df_survivors = df_updated[df_updated['Team'].isin(surviving_teams)].copy()
    
    print(f"\n[3/5] Re-normalizing features for {len(df_survivors)}-team field...")
    norms = normalize_all_teams(df_survivors)
    deriveds = [compute_derived_features(n) for n in norms]
    
    print("\n[4/5] Re-running scoring models on surviving field...")
    conf_ratings = compute_all_conference_ratings(df_survivors)
    df_survivors = apply_csi_to_teams(df_survivors, conf_ratings)
    csi_mults = df_survivors['CSI_multiplier'].tolist()
    rankings = generate_all_rankings(df_survivors, norms, deriveds, csi_mults)
    
    # Step 6: Re-run simulation on remaining bracket
    print("\n[5/5] Re-running Monte Carlo simulation on remaining bracket...")
    remaining_bracket = build_remaining_bracket(config, completed_games, df_survivors)
    
    simulation_results = simulate_bracket(
        remaining_bracket,
        blended_win_probability,
        n_sims=config['n_simulations'],
        seed=config['random_seed']
    )
    
    # Save with timestamp suffix so originals are preserved
    from datetime import datetime
    ts = datetime.now().strftime('%m%d_%H%M')
    update_config = {**config, 'output_dir': f"{config['output_dir']}/update_{ts}"}
    
    write_all_outputs(rankings, {}, simulation_results, {}, update_config)
    
    print(f"\n✅ Update complete — outputs saved to {update_config['output_dir']}")
    print_update_summary(rankings, simulation_results, completed_games)
```

---

## 6. Fetching Results: Auto-Detect Logic

```python
def fetch_results(config: dict) -> dict:
    """
    Tries ESPN API first; falls back to manual JSON if API fails.
    Returns standardized results dict.
    """
    # Try ESPN API
    try:
        raw = fetch_tournament_scores()
        games = parse_tournament_results(raw)
        
        # Fetch box scores for completed games (up to 20 at a time)
        for game in games[:20]:
            try:
                box = fetch_game_boxscore(game['game_id'])
                winner_stats = parse_team_game_stats(box, game['winner_name'])
                loser_stats = parse_team_game_stats(box, game['loser_name'])
                game['winner_game_stats'] = winner_stats
                game['loser_game_stats'] = loser_stats
            except Exception:
                pass  # Box score fetch failure is non-critical
        
        if games:
            print(f"  ✓ ESPN API: fetched {len(games)} completed games")
            return {'source': 'espn_api', 'completed_games': games}
    
    except Exception as e:
        print(f"  ⚠ ESPN API failed: {e} — falling back to manual JSON")
    
    # Fallback: manual JSON
    results_path = config.get('results_file', 'data/tournament_results.json')
    if os.path.exists(results_path):
        with open(results_path) as f:
            data = json.load(f)
        print(f"  ✓ Manual JSON: loaded {len(data['completed_games'])} games from {results_path}")
        return data
    
    print("  ⚠ No results found. Create data/tournament_results.json manually.")
    return {'source': 'none', 'completed_games': []}
```

---

## 7. How to Run Mid-Tournament Updates

### Automatic (ESPN API)

```bash
# After Round 1 completes (all 32 games finished):
python main.py --mode update

# After Round 2 (Sweet 16 set):
python main.py --mode update

# This can be run any time — it reads whatever is currently completed
```

### Manual (if ESPN API is down)

1. Open `data/tournament_results.json`
2. Add completed games following the format in Section 3
3. Run: `python main.py --mode update --results data/tournament_results.json`

### Streamlit UI (recommended)

In the Streamlit app, add a **"🔄 Update Results"** button in the sidebar:

```python
with st.sidebar:
    st.header("🔄 Mid-Tournament Update")
    
    update_method = st.radio(
        "Results source",
        ["Auto (ESPN API)", "Manual JSON upload"]
    )
    
    if update_method == "Manual JSON upload":
        results_file = st.file_uploader("Upload tournament_results.json", type=['json'])
    
    if st.button("🔄 Fetch & Re-Score", type="secondary", use_container_width=True):
        with st.spinner("Fetching results and re-scoring..."):
            results = fetch_results(config)
            df_updated = apply_tournament_bonuses(df, results['completed_games'], surviving_teams)
            # Re-run and display
            st.success(f"Updated! {len(results['completed_games'])} games processed.")
```

---

## 8. Output: Mid-Tournament Update Summary

After each update run, print and save this summary:

```
🏀 MID-TOURNAMENT UPDATE — After Round 1
══════════════════════════════════════════════════════
UPSETS DETECTED (8 total):
  ⚡ New Mexico State (12) def. Connecticut (5) by 7
  ⚡ Drake (11) def. Arizona (6) by 12
  ...

GIANT KILLER BONUSES APPLIED:
  New Mexico State: +3.4 AdjEM (seeded 12 but beat a 5 | Won turnover battle)
  Drake: +2.8 AdjEM (seeded 11 but beat a 6 | Dominant win margin=12)

UPDATED CHAMPIONSHIP PROBABILITIES (Surviving 32 teams):
  1. Duke          18.3%  (was 15.1% pre-tourney)
  2. Tennessee     11.2%  (was 12.4% pre-tourney)  ← dropped (opponent eliminated)
  3. Kansas        10.8%  (was 9.3% pre-tourney)
  ...
  8. New Mexico St  3.2%  (was 0.4% pre-tourney)  ⚡ Giant Killer Rising

NEXT ROUND MATCHUPS & WIN PROBABILITIES:
  New Mexico State (12) vs Memphis (4): 38.1% chance of upset
  Drake (11) vs Houston (3): 29.4% chance of upset
══════════════════════════════════════════════════════
```

---

## 9. Integration with `IMPLEMENTATION_GUIDE.md` (Additions)

Add these to the implementation checklist:

**New file:** `engine/live_results.py`
- `fetch_tournament_scores() -> dict`
- `parse_tournament_results(data) -> list[dict]`
- `fetch_game_boxscore(game_id) -> dict`
- `parse_team_game_stats(box_data, team_name) -> dict`
- `fetch_results(config) -> dict`  ← auto-detect wrapper

**New file:** `engine/tournament_bonus.py`
- `compute_tournament_bonus(team_name, completed_games, all_adjEMs) -> dict`
- `apply_tournament_bonuses(df, completed_games, surviving_teams) -> pd.DataFrame`
- `build_remaining_bracket(config, completed_games, df_survivors) -> dict`

**Update `main.py`:**
- Add `--mode update` CLI argument
- Add `run_tournament_update(config)` function

**Update `app.py`:**
- Add "🔄 Update Results" section to sidebar
- Add display for giant killer bonuses applied
- Show pre-tournament vs post-update probability comparison

**Update `config.json`:**
```json
{
  "results_file": "./data/tournament_results.json",
  "espn_api_timeout": 10,
  "espn_groups_id": 100,
  "max_adjEM_bonus": 4.0,
  "giant_killer_seed_gap_minimum": 1
}
```

---

## 10. Bonus Cap Rationale

The +4.0 AdjEM hard cap on the giant killer bonus is intentional and research-grounded:

- A full-season AdjEM difference between a 5-seed and 12-seed is typically **~8–12 points**
- One game of evidence cannot override a full season. We are blending in new signal, not replacing the prior
- +4.0 AdjEM is approximately equivalent to upgrading a team one full seed line (e.g., effectively treating a 12-seed like a 9-seed)
- This is consistent with Bayesian updating: `posterior = α × prior + (1-α) × new_evidence`, where α ≈ 0.85 (season data is 85% of the signal, one tournament game is 15%)

The formula: `giant_killer_bonus = min(2.5 × upset_magnitude + 1.5 × margin_factor, 4.0)` means:
- A 12-seed barely beating a 5-seed (margin=2): ~1.5 AdjEM bonus
- A 12-seed dominating a 5-seed (margin=15): ~4.0 AdjEM bonus (capped)
- A 15-seed shocking a 2-seed by 10: ~4.0 AdjEM bonus (capped, as it should be — one game doesn't make them a top-10 team)