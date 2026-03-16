# March Mathness — UI & Output Design Specification

**Document 09 — Bracket Decision Interface, Output Formats, and Visual Design**

This document specifies the exact visual design and interaction model for every output the system produces — both the Streamlit UI and the static HTML artifacts. The goal is not just to show data, but to make bracket decisions obvious: a user should be able to look at a matchup card and know in 5 seconds whether to pick the favorite, consider an upset, or flag the game as a toss-up.

---

## 1. Design Philosophy

Three core principles:

1. **Verdict-first.** Every matchup card leads with a clear verdict label (LOCK / LEAN / TOSS-UP / UPSET ALERT / TRAP GAME) before showing any numbers. The numbers exist to explain the verdict, not the other way around.

2. **Progressive disclosure.** The first view shows only what you need to fill a bracket. Numbers, components, and model breakdowns are one click deeper. You should be able to make all 63 picks in 20 minutes at the top level, then drill in where you want to.

3. **Volatility is visible.** Risk is color-coded separately from quality. A team can be excellent AND volatile — that's important information a single score doesn't convey.

---

## 2. Color System

Used consistently throughout all outputs (HTML, Streamlit, terminal):

| Signal | Color | Hex | When Used |
|--------|-------|-----|-----------|
| Strong Favorite / Lock | Dark Green | `#1a7f37` | Win prob ≥ 80% |
| Moderate Favorite / Lean | Light Green | `#2da44e` | Win prob 65–79% |
| Slight Favorite | Yellow-Green | `#8bc34a` | Win prob 55–64% |
| Toss-Up | Amber | `#f59e0b` | Win prob 45–54% |
| Slight Underdog | Orange | `#f97316` | Win prob 35–44% |
| Upset Alert | Red | `#ef4444` | CinderellaScore > 0.40 + win prob < 45% |
| High Cinderella Alert | Bright Red | `#b91c1c` | CinderellaScore > 0.55 |
| Volatile / Boom-or-Bust | Purple | `#9333ea` | VolatilityScore > 0.65 |
| Trap Game | Orange-Red | `#dc2626` | Favorite win prob 65–79% but underdog Cinderella score > 0.40 |
| Eliminated | Gray | `#6b7280` | Post-tournament |
| Override / Injury | Yellow | `#eab308` | Team has active overrides.json entry |

---

## 3. Matchup Verdict Card (Core UI Element)

This is the fundamental unit of the bracket decision interface. One card per matchup in the bracket.

```
┌─────────────────────────────────────────────────────────────────────┐
│  EAST REGION — ROUND OF 64                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐    │
│  │  #1 Kansas               │  │  #16 UMBC                    │    │
│  │  AdjEM: +28.4            │  │  AdjEM: -2.1                 │    │
│  │  PowerScore: 87.3        │  │  PowerScore: 41.2            │    │
│  │  • elite defense         │  │  • forces turnovers          │    │
│  │  • battle-tested         │  │  • slow tempo                │    │
│  └──────────────────────────┘  └──────────────────────────────┘    │
│                                                                     │
│         WIN PROBABILITY:  [■■■■■■■■■■■■■■■■■■■■░]  97%            │
│                           Kansas ◄─────────────── UMBC             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  🔒 LOCK — KANSAS          Spread: Kansas -18.3             │   │
│  │  Confidence: VERY HIGH     Historical: 1-seeds win 98.75%   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [▼ Show model breakdown]   [▼ Show Cinderella analysis]            │
└─────────────────────────────────────────────────────────────────────┘
```

**Expanded view (on click):**
```
┌─────────────────────────────────────────────────────────────────────┐
│  MODEL BREAKDOWN                                                    │
│  ─────────────────────────────────────────────────────────────────  │
│  Model          Kansas  UMBC   Verdict                              │
│  ─────────────────────────────────────────────────────────────────  │
│  Default        87.3    41.2   Kansas (+46.1)                       │
│  Analytics      91.2    38.4   Kansas (+52.8)                       │
│  Defensive      84.1    39.7   Kansas (+44.4)                       │
│  Momentum       82.4    44.3   Kansas (+38.1)                       │
│  ─────────────────────────────────────────────────────────────────  │
│  Consensus: All 8 models pick Kansas. No model signals upset.       │
│                                                                     │
│  ROUND ADVANCEMENT PROBABILITIES (from simulation)                  │
│  Kansas:  R64: 97% | R32: 82% | S16: 68% | E8: 49% | F4: 31%      │
│  UMBC:    R64:  3% | Eliminated after R64 in 97% of simulations    │
└─────────────────────────────────────────────────────────────────────┘
```

**A toss-up matchup card:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  SOUTH REGION — ROUND OF 64                                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌──────────────────────────────┐    │
│  │  #5 Connecticut          │  │  #12 New Mexico State ⚡      │    │
│  │  AdjEM: +16.2            │  │  AdjEM: +11.8                │    │
│  │  PowerScore: 73.1        │  │  PowerScore: 64.8            │    │
│  │  • elite offense         │  │  🔴 CINDERELLA ALERT         │    │
│  │                          │  │  CinderellaScore: 0.61       │    │
│  │  ⚠️ TRAP GAME             │  │  • forces turnovers (elite)  │    │
│  │                          │  │  • veteran squad             │    │
│  └──────────────────────────┘  └──────────────────────────────┘    │
│                                                                     │
│         WIN PROBABILITY:  [■■■■■■■■■■■░░░░░░░░░░]  54%            │
│                           UConn ◄──────────── New Mexico St         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  ⚠️  TRAP GAME — LEAN UCONN (SOFT LEAN)                     │   │
│  │  Spread: UConn -4.1       CinderellaScore: 0.61 (HIGH)      │   │
│  │  Historical: 12-seeds win 35.6% of the time                 │   │
│  │  Upset model: YES (5 of 8 strategies pick New Mexico St)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Verdict Classification Logic

```python
def classify_matchup_verdict(
    team_a: dict,      # favorite (lower seed)
    team_b: dict,      # underdog
    win_prob_a: float, # P(team_a wins)
    cinderella_score_b: float,
    models_picking_upset: int,  # out of 8 strategies
    strategy_consensus: str,
) -> dict:
    """
    Returns verdict dict with label, color, description, and pick recommendation.
    """
    seed_gap = team_b['Seed'] - team_a['Seed']
    
    # Trap Game: favorite looks comfortable but underdog has real upset profile
    if (0.55 <= win_prob_a <= 0.75 and 
        cinderella_score_b >= 0.40 and 
        models_picking_upset >= 3):
        return {
            "label": "TRAP GAME",
            "icon": "⚠️",
            "color": "#dc2626",
            "pick": team_a['Team'],
            "pick_strength": "SOFT",
            "description": f"Lean {team_a['Team']} but this is a genuine upset risk"
        }
    
    # Lock: very high confidence
    if win_prob_a >= 0.85:
        return {
            "label": "LOCK",
            "icon": "🔒",
            "color": "#1a7f37",
            "pick": team_a['Team'],
            "pick_strength": "STRONG",
            "description": f"Strong confidence in {team_a['Team']}"
        }
    
    # Upset Alert: model likes the underdog
    if win_prob_a < 0.50 or (cinderella_score_b >= 0.55 and models_picking_upset >= 4):
        return {
            "label": "UPSET ALERT",
            "icon": "⚡",
            "color": "#ef4444",
            "pick": team_b['Team'],
            "pick_strength": "MEDIUM",
            "description": f"Model leans {team_b['Team']} — strong Cinderella profile"
        }
    
    # Lean: moderate confidence in favorite
    if win_prob_a >= 0.65:
        return {
            "label": "LEAN",
            "icon": "→",
            "color": "#2da44e",
            "pick": team_a['Team'],
            "pick_strength": "MEDIUM",
            "description": f"Lean {team_a['Team']} — solid but not a lock"
        }
    
    # Toss-up: 45-65% range
    return {
        "label": "TOSS-UP",
        "icon": "🎲",
        "color": "#f59e0b",
        "pick": team_a['Team'],  # slight favorite gets default pick
        "pick_strength": "WEAK",
        "description": "Coin flip — check volatility scores before deciding"
    }
```

---

## 5. Streamlit App — Tab-by-Tab Specification

### Tab 1: 📊 Power Rankings

A sortable, filterable table. Primary use: know which teams are legitimately good.

**Key UI elements:**
- Filter by conference, seed range, alert level
- Color gradient on `PowerScore` column (green → red)
- `Volatility_Score` shown as a purple badge (🟣) next to team name when > 0.65
- `Injury Override Active` shown as yellow ⚠️ when team has override applied
- Clicking a team row expands it to show all component scores as a mini bar chart
- Sort by: PowerScore (default), AdjEM, Cinderella Score, Momentum

**Column display order:**
```
Rank | Team [badges] | Seed | Conf | PowerScore [bar] | AdjEM | AdjD | Barthag | Momentum | Strengths
```

### Tab 2: 🔮 Cinderella Scores

Seeds 9+ only. The main upset-hunting view.

**Key UI elements:**
- Alert level filter (HIGH ALERT / WATCH / All)
- Cards layout (not just a table) — each team gets a mini profile card
- Per-component radar chart on hover/click
- "Why this team?" expandable explanation in plain language

**Mini card layout (seeds 9+):**
```
┌────────────────────────────────────────┐
│  🔴 HIGH ALERT                         │
│  New Mexico State  #12 (MVC)           │
│  CinderellaScore: 0.61                 │
│  ─────────────────────────────────────  │
│  Seed Mismatch:  ████████░░  0.78      │
│  Defense:        █████████░  0.85      │
│  Turnover:       ███████░░░  0.71      │
│  Experience:     █████░░░░░  0.62      │
│  Tempo:          ████████░░  0.74      │
│  Rebounding:     ████░░░░░░  0.49      │
│  ─────────────────────────────────────  │
│  "Underseeded by 4 positions. Elite    │
│  defense and forces turnovers. Coach   │
│  has 3 prior tournament appearances."  │
└────────────────────────────────────────┘
```

### Tab 3: 🔮 Cinderella Scores

**Key UI elements:**
- Ranked table for seeds 9+ with `CinderellaScore` and `CinderellaAlertLevel`
- Filter controls: All / HIGH / WATCH
- Expandable component breakdown fields (`C_SeedMismatch`, `C_Defense`, `C_Turnover`, `C_Tempo`, `C_Rebounding`, `C_RankValue`)

### Tab 5: 🎯 Matchup Calculator

An interactive tool: select any two teams and see the full matchup analysis.

**UI elements:**
- Two dropdown selectors (all tournament teams)
- Auto-renders a full Matchup Verdict Card (Section 3) for the selected pair
- Shows: win probability bar, predicted spread, confidence tier, model consensus, historical seed matchup rate
- "Add to my bracket" button that saves to a personal picks session state

### Tab 6: 🎲 Bracket Simulation

The simulation results view. Most important tab for pool strategy.

**UI elements:**
- Strategy selector dropdown (8 strategies)
- Main view: table of all surviving teams sorted by Championship probability
- Shows columns: Team, Seed, R64%, R32%, S16%, E8%, F4%, Champ%, Win%
- Color heat map on probability columns
- "Pre-tournament vs Current" comparison column if mid-tournament update has been run
- Giant killer flag ⚡ next to team name if they've beaten a higher seed in the tournament

**Champion probability bar chart (horizontal):**
```
Duke          ████████████████████  18.3%
Tennessee     ████████████████       14.2%
Kansas        ██████████████         12.8%
Houston       ████████████           10.9%
...
NM State ⚡   ████                    3.2%  ← Giant Killer bonus applied
```

### Tab 7: 📋 Bracket Strategies

A side-by-side bracket visualization.

**UI elements:**
- Strategy selector (tabs or dropdown for each of 8 strategies)
- The bracket itself: 4 regions, 6 rounds, 63 matchups
- Each game box shows: winner, win probability, upset flag
- Color coding per verdict system (Section 2)
- "Consensus view": a summary bracket showing which team each strategy picks per game
  - If 7/8 strategies agree → show in solid green with count badge
  - If 5-6/8 agree → light green
  - If 4/8 agree (split) → amber "SPLIT"
  - If 3 or fewer agree → red "CONTESTED"

**Consensus bracket table (the most useful single output):**
```
Matchup          | Consensus Pick   | Agreement | Model Split
─────────────────────────────────────────────────────────────
1 Duke vs 16 UMBC       | Duke         | 8/8 🟢    | Lock
5 UConn vs 12 NMS       | Split        | 4/8 🔴    | 4 UConn / 4 NM St
3 Tennessee vs 14 SFA   | Tennessee    | 7/8 🟢    | —
...
```

### Tab 8: 📄 Pick Sheet

The injury override editor.

**UI elements:**
- Live JSON editor (use `streamlit-ace` or a simple text area)
- Template button that generates sample JSON structure
- "Apply overrides and re-run" button
- Table showing currently active overrides with before/after AdjEM values
- Warning: "Overrides reset on next data fetch"

---

## 6. Static HTML Dashboard (offline alternative to Streamlit)

When Streamlit is not running, `main.py` generates `tournament_dashboard.html` — a self-contained file with all charts and tables embedded. No server required.

### HTML Dashboard Sections

**Section 1: Header Bar**
- "March Mathness 2026" title
- Last run timestamp
- Quick stats: Teams analyzed, Simulations run, Data source, Override count

**Section 2: Bracket Decision Quick View**
- A compact bracket view showing all 63 matchups
- Each matchup shows: both teams, verdict icon (🔒/⚠️/⚡/🎲), and win probability
- Click opens a modal with the full Matchup Verdict Card

**Section 3: Top Recommendations**
Three panels side by side:
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ 🔒 SAFE PICKS   │  │ 🔴 CINDERELLAS  │  │ 🎲 TOSS-UPS     │
│                 │  │                 │  │                 │
│ Teams with 7/8+ │  │ Seeds 9+ with   │  │ Games where 4+  │
│ model consensus │  │ HIGH ALERT      │  │ models disagree │
│                 │  │                 │  │                 │
│ Duke            │  │ NM State (12)   │  │ UConn vs NMS    │
│ Houston         │  │ Drake (11)      │  │ AZ vs Clemson   │
│ Tennessee       │  │ Samford (13)    │  │ Bama vs Creig.  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Section 4: Power Rankings Table** (full 68-team table)

**Section 5: Simulation Results** (top-20 championship probabilities as chart)

**Section 6: Matchup + strategy outputs (no conference-strength section)**

**Section 7: Strategy Comparison** (8 brackets, one per tab)

---

## 7. Terminal Output (when running `main.py`)

Even without a UI, the terminal should be informative. After running:

```
══════════════════════════════════════════════════════════════════
MARCH MATHNESS 2026 — ANALYSIS COMPLETE
══════════════════════════════════════════════════════════════════

TOP 10 POWER RANKINGS
─────────────────────────────────────────────────────────────────
 #1   Duke           (ACC)   Seed: 1   Score: 89.4   AdjEM: +29.1
 #2   Houston        (Big12) Seed: 1   Score: 86.2   AdjEM: +26.8
 #3   Tennessee      (SEC)   Seed: 2   Score: 84.1   AdjEM: +25.3
 ...

🔴 CINDERELLA ALERTS (HIGH — Score > 0.55)
─────────────────────────────────────────────────────────────────
 NM State     #12 (MVC)   CinderellaScore: 0.61   → Matchup: UConn (#5)
 Drake        #11 (MVC)   CinderellaScore: 0.58   → Matchup: Houston (#6)
 Samford      #13 (SoCon) CinderellaScore: 0.55   → Matchup: Kansas (#4)

⚠️  TRAP GAMES (Favorite may be vulnerable)
─────────────────────────────────────────────────────────────────
 UConn (#5) vs NM State (#12)  — Win prob 54% | Cinderella: 0.61
 Kansas (#3) vs Samford (#13)  — Win prob 64% | Cinderella: 0.55

🎲 TOSS-UPS (45-55% win probability)
─────────────────────────────────────────────────────────────────
 Michigan St (#7) vs Ole Miss (#10)   — 51% Michigan St
 TCU (#8) vs Florida (#9)             — 53% TCU

🏆 CHAMPIONSHIP PROBABILITIES (Top 8)
─────────────────────────────────────────────────────────────────
 Duke           18.3%  ████████████████████
 Houston        14.2%  ████████████████
 Tennessee      12.8%  ██████████████
 Kansas         10.9%  ████████████
 Arizona         9.1%  ██████████
 UConn           7.8%  █████████
 Auburn          6.4%  ███████
 Florida         5.2%  ██████

8 STRATEGY BRACKET CONSENSUS
─────────────────────────────────────────────────────────────────
 Champion consensus:  Duke (6/8 strategies) | Minority: Houston (2/8)
 Final Four consensus: Duke, Houston, Tennessee, [SPLIT between Kansas/Arizona]
 Cinderella consensus: NM State reaches Sweet 16 in 4/8 strategies

Outputs saved to: ./outputs/
 ✓ outputs/rankings/power_rankings.csv
 ✓ outputs/rankings/cinderella_rankings.csv
 ...
 ✓ outputs/brackets/bracket_standard.json
 ...
 ✓ outputs/dashboard/tournament_dashboard.html
══════════════════════════════════════════════════════════════════
```

---

## 8. Bracket Pick Summary Sheet (Printable Output)

Generate `outputs/my_bracket_picks.txt` — a simple, printable bracket decision guide:

```
MARCH MATHNESS 2026 — BRACKET DECISION GUIDE
═══════════════════════════════════════════════════════════════════

EAST REGION
──────────────────────────────────────────────────────────────────
R64  🔒 LOCK    Duke (#1) over UMBC (#16)            Win prob: 97%
R64  🔒 LOCK    Tennessee (#2) over McNeese (#15)    Win prob: 92%
R64  → LEAN    Kansas (#3) over Samford (#13)        Win prob: 64%  ⚠️ Watch
R64  🎲 TOSS-UP Creighton (#4) vs Akron (#13)        Win prob: 56%
R64  ⚡ UPSET  NM State (#12) over UConn (#5)        Win prob: 46%  🔴 Cinderella
R64  → LEAN    Baylor (#6) over Colgate (#11)        Win prob: 69%
R64  🎲 TOSS-UP Michigan St (#7) vs Ole Miss (#10)   Win prob: 51%
R64  🎲 TOSS-UP TCU (#8) vs Florida (#9)             Win prob: 53%

EAST R32 (if favorites advance):
  Duke vs [TCU/Florida winner]          → Duke (84%)
  Tennessee vs [Creighton/Akron winner] → Tennessee (77%)
  NM State vs [Kansas/Samford winner]   → SPLIT — NM State Cinderella or Kansas
  Baylor vs [MSU/Ole Miss winner]       → Baylor (71%)
  ...

──────────────────────────────────────────────────────────────────
EAST CHAMPION PROJECTION:
  Most likely (Standard model):  Duke
  Upset scenario:                NM State to Sweet 16 (61% of simulations)
──────────────────────────────────────────────────────────────────

[WEST, SOUTH, MIDWEST regions follow same format]

═══════════════════════════════════════════════════════════════════
FINAL FOUR CONSENSUS
═══════════════════════════════════════════════════════════════════
  East:    Duke           (6/8 models)
  West:    Houston        (5/8 models) — minority: Arizona (3/8)
  South:   Tennessee      (7/8 models)
  Midwest: Kansas         (4/8 models) — contested: Auburn (4/8)

CHAMPION:  Duke  (6/8 models | 18.3% simulation probability)

═══════════════════════════════════════════════════════════════════
PICKS TO ALWAYS MAKE (8/8 model consensus, seed ≤ 3)
═══════════════════════════════════════════════════════════════════
  Duke (#1 East)       R64, R32, S16
  Houston (#1 South)   R64, R32, S16
  Tennessee (#2 East)  R64, R32

LOCKS TO NEVER PICK (models flagged as traps or coinflips)
═══════════════════════════════════════════════════════════════════
  UConn (#5) to Sweet 16    ← NM State Cinderella danger
  Arizona (#2) to Final 4   ← Model split 4/4; contested
═══════════════════════════════════════════════════════════════════
```

---

## 9. Per-Team Profile Card (HTML, one per team)

For the 68 tournament teams, generate individual profile pages in `outputs/profiles/[team_name].html`:

```
DUKE BLUE DEVILS — #1 SEED (EAST)
══════════════════════════════════════════════════════

POWER SCORE: 89.4 / 100  ████████████████████████░  [ELITE TIER]

EFFICIENCY
  AdjEM:  +29.1   ██████████████████████████░  Rank: #2
  AdjO:   121.4   ████████████████████████░    Rank: #4
  AdjD:    92.3   █████████████████████████░   Rank: #3

FOUR FACTORS (Offense)           FOUR FACTORS (Defense)
  eFG%:  56.2% [Elite]             Opp eFG%:  44.8% [Elite]
  TO%:   14.1% [Good]              Opp TO%:   21.3% [Elite]
  OR%:   34.8% [Good]              DR%:       78.4% [Good]
  FTR:   38.2% [Good]              Opp FTR:   26.1% [Good]

CONTEXT
  SOS Rank:  #7 (Elite)    Experience: 2.4 (Veteran)
  Tempo:     70.2 (Avg)    Coach Score: 9/10 (Jon Scheyer)
  Consistency: 0.81 HIGH   Volatility: 0.28 LOW

TEAM STRENGTHS
  ✓ Elite defense                    ✓ Veteran squad
  ✓ Stifling perimeter defense       ✓ Battle-tested (9 Q1 wins)
  ✓ Exceptional ball movement

CHAMPIONSHIP PROBABILITY:  18.3%
  R64: 97% | R32: 82% | S16: 68% | E8: 49% | F4: 31% | Champ: 18%

POTENTIAL OPPONENTS (by round if chalk holds)
  R64:   UMBC (#16)        Win prob: 97%  🔒 Lock
  R32:   TCU (#8)          Win prob: 84%  🔒 Lock
  S16:   Creighton (#4)    Win prob: 71%  → Lean
  E8:    Tennessee (#2)    Win prob: 55%  🎲 Toss-up
```

---

## 10. Implementation Notes for Cursor

### Streamlit components to use:

```python
# These libraries make the UI significantly better:
pip install streamlit-aggrid      # better data tables with sorting/filtering
pip install streamlit-echarts      # radar charts for Cinderella components
pip install streamlit-extras       # extra UI components like badges, colored headers

# Probability bar (custom component, pure HTML in st.markdown):
def probability_bar(prob: float, label_left: str, label_right: str) -> str:
    filled = int(prob * 20)
    empty = 20 - filled
    return f"""
    <div style="font-family: monospace; font-size: 14px;">
        {label_left} {'█' * filled}{'░' * empty} {label_right}<br>
        <span style="color: gray;">{prob*100:.1f}% → {label_left if prob > 0.5 else label_right}</span>
    </div>
    """
```

### Jinja2 bracket template structure:

The static HTML bracket uses a CSS grid layout. Each matchup is a `div.matchup` with two `div.team` children. Color classes applied dynamically from verdict classification:

```html
<!-- bracket_standard.html structure -->
<div class="bracket">
  <div class="region" id="east">
    <div class="round r64">
      <div class="matchup trap-game">
        <div class="team seed-5 loser">UConn<span class="prob">54%</span></div>
        <div class="team seed-12 winner upset">NM State ⚡<span class="prob">46%</span></div>
        <div class="verdict upset-alert">⚡ UPSET ALERT</div>
      </div>
    </div>
  </div>
</div>
```

### Generate bracket summary JSON first, then UI from it:

The most efficient approach: generate `bracket_summary.json` with all 63 matchup verdicts pre-computed, then both the Streamlit UI and the static HTML template read from that single source of truth. This means the UI doesn't run any math — it's purely a rendering layer.

```json
{
  "matchups": [
    {
      "region": "East",
      "round": "R64",
      "slot": 1,
      "team_a": {"name": "Duke", "seed": 1, "power_score": 89.4, "adjEM": 29.1},
      "team_b": {"name": "UMBC", "seed": 16, "power_score": 41.2, "adjEM": -2.1},
      "win_prob_a": 0.97,
      "predicted_spread": 18.3,
      "verdict": "LOCK",
      "verdict_icon": "🔒",
      "verdict_color": "#1a7f37",
      "pick": "Duke",
      "pick_strength": "STRONG",
      "cinderella_score_b": 0.04,
      "models_picking_upset": 0,
      "historical_upset_rate": 0.0125,
      "simulation_winner_pct_a": 0.97,
      "volatility_flag": false
    }
  ]
}
```