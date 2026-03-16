"""Streamlit UI for March Mathness."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.ingestion import load_bracket, load_teams
from engine.simulation import simulate_bracket
from engine.win_probability import confidence_tier, predicted_spread, production_win_probability

st.set_page_config(
    page_title="March Mathness",
    page_icon="🏀",
    layout="wide",
)

OUTPUTS = Path("outputs")
DATA_DIR = Path("data")
PIPELINE_HINT = "Generate outputs first with `python main.py --mode full` (or `--mode rankings`)."
ROUND_ORDER = ["R64", "R32", "S16", "E8"]
ROUND_WEIGHTS = {"R64": 1.0, "R32": 2.0, "S16": 3.0, "E8": 4.0}
ROUND_URGENCY = {"R64": 4.0, "R32": 3.0, "S16": 2.0, "E8": 1.0}
ROUND_POINTS = {"R64": 1, "R32": 2, "S16": 4, "E8": 8, "F4": 16, "Championship": 32}
ROUND_WIN_KEY = {
    "R64": "R32",
    "R32": "S16",
    "S16": "E8",
    "E8": "F4",
    "F4": "Championship",
    "Championship": "Champion",
}
PATH_ROUND_ORDER = ["R64", "R32", "S16", "E8", "F4", "Championship"]


def _build_metric_leaderboards(power_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create sortable leaderboards for single-dimension team traits."""
    base_cols = ["Team", "Seed", "Conference"]
    working = power_df.copy()

    for col in ["AdjO", "AdjD", "Adj_T", "OR%", "Blk_%", "FTR", "eFG%", "Opp_TO%", "TO%", "Barthag"]:
        if col in working.columns:
            working[col] = pd.to_numeric(working[col], errors="coerce")

    # Physicality blends board control, rim protection, and foul pressure.
    physicality_parts: list[pd.Series] = []
    for col in ["OR%", "Blk_%", "FTR"]:
        if col in working.columns:
            col_series = working[col]
            span = col_series.max() - col_series.min()
            if pd.notna(span) and float(span) > 0:
                norm_col = (col_series - col_series.min()) / span
                physicality_parts.append(norm_col.fillna(0.5))
    if physicality_parts:
        working["Physicality_Index"] = sum(physicality_parts) / len(physicality_parts)

    metric_specs: list[tuple[str, str, bool, str]] = [
        ("Strongest Offense", "AdjO", False, "{:.1f}"),
        ("Strongest Defense", "AdjD", True, "{:.1f}"),
        ("Fastest Pace", "Adj_T", False, "{:.1f}"),
        ("Most Physical", "Physicality_Index", False, "{:.3f}"),
        ("Best Shooting", "eFG%", False, "{:.1f}%"),
        ("Best Ball Security", "TO%", True, "{:.1f}%"),
        ("Most Turnover Pressure", "Opp_TO%", False, "{:.1f}%"),
        ("Best Offensive Rebounding", "OR%", False, "{:.1f}%"),
        ("Best Overall Efficiency", "Barthag", False, "{:.3f}")
    ]

    leaderboards: dict[str, pd.DataFrame] = {}
    for label, metric_col, ascending, value_fmt in metric_specs:
        if metric_col not in working.columns:
            continue
        metric_view = (
            working[base_cols + [metric_col]]
            .dropna(subset=[metric_col])
            .sort_values(metric_col, ascending=ascending)
            .copy()
        )
        if metric_view.empty:
            continue
        metric_view["Rank"] = range(1, len(metric_view) + 1)
        metric_view["Value"] = metric_view[metric_col].map(value_fmt.format)
        leaderboards[label] = metric_view[["Rank"] + base_cols + ["Value"]]

    return leaderboards


def _build_bracket_with_stats(
    bracket: dict, team_lookup: dict[str, dict]
) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for region, teams in bracket["teams_by_region"].items():
        region_list = []
        for team in teams:
            name = str(team["team"])
            merged = dict(team_lookup.get(name, {
                "Team": name, "AdjEM": 0.0, "Adj_T": 68.0,
                "Seed": team.get("Seed", 16),
            }))
            merged["Team"] = name
            merged["Seed"] = int(team.get("Seed", merged.get("Seed", 16)))
            merged["slot"] = int(team.get("slot", 16))
            region_list.append(merged)
        result[region] = sorted(region_list, key=lambda t: int(t.get("slot", 99)))
    return result


def _read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _branch_action(prob: float) -> tuple[str, str, str]:
    """Map winner probability to lock/branch action and portfolio split."""
    if prob >= 0.85:
        return "LOCK", "100/0", "Very high confidence"
    if prob >= 0.72:
        return "LEAN", "85/15", "Strong edge, tiny hedge only"
    if prob >= 0.60:
        return "BRANCH", "70/30", "Meaningful upset risk"
    if prob >= 0.55:
        return "BRANCH", "60/40", "Near coin flip"
    return "BRANCH", "55/45", "True toss-up"


def _build_team_influence(
    sim_payload: dict | None,
    power_df: pd.DataFrame | None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Compute team influence and expected tournament points from simulation + power rank."""
    sim_points: dict[str, float] = {}
    if sim_payload:
        sim_results = sim_payload.get("results", {})
        if isinstance(sim_results, dict):
            for team, rounds in sim_results.items():
                if not isinstance(rounds, dict):
                    continue
                expected_points = (
                    ROUND_POINTS["R64"] * float(rounds.get("R32", 0.0))
                    + ROUND_POINTS["R32"] * float(rounds.get("S16", 0.0))
                    + ROUND_POINTS["S16"] * float(rounds.get("E8", 0.0))
                    + ROUND_POINTS["E8"] * float(rounds.get("F4", 0.0))
                    + ROUND_POINTS["F4"] * float(rounds.get("Championship", 0.0))
                    + ROUND_POINTS["Championship"] * float(rounds.get("Champion", 0.0))
                )
                sim_points[str(team)] = float(expected_points)

    sim_max = max(sim_points.values()) if sim_points else 0.0
    sim_norm = {
        team: (points / sim_max if sim_max > 0 else 0.0)
        for team, points in sim_points.items()
    }

    power_norm: dict[str, float] = {}
    if power_df is not None and not power_df.empty and "Team" in power_df.columns:
        rank_col = "Rank" if "Rank" in power_df.columns else None
        if rank_col:
            ranked = power_df[["Team", rank_col]].copy()
            ranked[rank_col] = pd.to_numeric(ranked[rank_col], errors="coerce")
            ranked = ranked.dropna(subset=[rank_col])
            if not ranked.empty:
                max_rank = float(ranked[rank_col].max())
                min_rank = float(ranked[rank_col].min())
                span = max(1.0, max_rank - min_rank)
                for _, row in ranked.iterrows():
                    team = str(row["Team"])
                    rank = float(row[rank_col])
                    power_norm[team] = 1.0 - ((rank - min_rank) / span)

    teams = set(sim_norm.keys()) | set(power_norm.keys())
    influence: dict[str, float] = {}
    for team in teams:
        influence[team] = 0.7 * float(sim_norm.get(team, 0.0)) + 0.3 * float(power_norm.get(team, 0.0))

    return influence, sim_points


def _remaining_expected_points(round_name: str, team: str, sim_payload: dict | None) -> float:
    """Expected remaining bracket points for picking a team from this round onward."""
    if not sim_payload:
        return 0.0
    sim_results = sim_payload.get("results", {})
    if not isinstance(sim_results, dict) or team not in sim_results:
        return 0.0
    rounds = sim_results.get(team, {})
    if not isinstance(rounds, dict):
        return 0.0

    order = ["R64", "R32", "S16", "E8", "F4", "Championship"]
    if round_name not in order:
        return 0.0
    start_idx = order.index(round_name)
    expected = 0.0
    for r in order[start_idx:]:
        next_key = ROUND_WIN_KEY[r]
        expected += ROUND_POINTS[r] * float(rounds.get(next_key, 0.0))
    return float(expected)


def _build_branch_plan_df(
    summary_payload: dict | None,
    sim_payload: dict | None,
    power_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Build branch-priority table focused on early exits for influential teams."""
    if not summary_payload:
        return pd.DataFrame()
    regions = summary_payload.get("modal_bracket", {}).get("regions", {})
    if not isinstance(regions, dict):
        return pd.DataFrame()
    influence_map, sim_points_map = _build_team_influence(sim_payload, power_df)

    rows: list[dict[str, object]] = []
    for region, rounds in regions.items():
        if not isinstance(rounds, dict):
            continue
        for round_name, games in rounds.items():
            if round_name not in ROUND_WEIGHTS or not isinstance(games, list):
                continue
            for game in games:
                team_a = str(game.get("team_a", ""))
                team_b = str(game.get("team_b", ""))
                winner = str(game.get("winner", ""))
                prob = float(game.get("prob", 0.5))
                if not team_a or not team_b or not winner:
                    continue

                other_team = team_b if winner == team_a else team_a
                uncertainty = 1.0 - abs(prob - 0.5) / 0.5
                upset_prob = 1.0 - prob
                influence_primary = float(influence_map.get(winner, 0.0))
                influence_counter = float(influence_map.get(other_team, 0.0))
                remaining_points = _remaining_expected_points(round_name, winner, sim_payload)
                # Root objective: early high-impact elimination risk for influential teams.
                impact_score = upset_prob * max(0.1, influence_primary) * remaining_points * ROUND_URGENCY[round_name]
                branch_score = impact_score + (uncertainty * 0.75) + (influence_counter * 0.5)
                action, split, note = _branch_action(prob)
                rows.append(
                    {
                        "Round": round_name,
                        "Region": region,
                        "Matchup": f"{team_a} vs {team_b}",
                        "Primary Pick": winner,
                        "Counter Pick": other_team,
                        "Primary Win %": round(prob * 100, 1),
                        "Counter Win %": round((1.0 - prob) * 100, 1),
                        "Action": action,
                        "Recommended Split": split,
                        "Branch Score": round(branch_score, 2),
                        "Expected Pts Team": round(float(sim_points_map.get(winner, 0.0)), 2),
                        "Pts At Risk": round(impact_score, 2),
                        "Reason": note + "; early exit risk weighted",
                    }
                )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    round_rank = {name: idx for idx, name in enumerate(ROUND_ORDER)}
    df["round_rank"] = df["Round"].map(round_rank).fillna(99)
    df = df.sort_values(by=["Branch Score", "round_rank"], ascending=[False, True]).drop(columns=["round_rank"])
    df.insert(0, "Priority", range(1, len(df) + 1))
    return df


def _branch_table_html(df: pd.DataFrame) -> str:
    """Render branch plan as an HTML table for quick scanning."""
    if df.empty:
        return "<p>No branch-plan rows available.</p>"

    color_map = {
        "LOCK": "#1a7f37",
        "LEAN": "#2da44e",
        "BRANCH": "#f59e0b",
    }
    header = (
        "<thead><tr>"
        "<th>Priority</th><th>Round</th><th>Region</th><th>Matchup</th>"
        "<th>Primary</th><th>Primary %</th><th>Counter</th><th>Counter %</th>"
        "<th>Action</th><th>Split</th><th>Score</th><th>Pts@Risk</th><th>ExpPts(Primary)</th><th>Reason</th>"
        "</tr></thead>"
    )

    body_rows: list[str] = []
    for _, row in df.iterrows():
        action = str(row["Action"])
        action_color = color_map.get(action, "#64748b")
        body_rows.append(
            "<tr>"
            f"<td>{int(row['Priority'])}</td>"
            f"<td>{escape(str(row['Round']))}</td>"
            f"<td>{escape(str(row['Region']))}</td>"
            f"<td>{escape(str(row['Matchup']))}</td>"
            f"<td><strong>{escape(str(row['Primary Pick']))}</strong></td>"
            f"<td>{float(row['Primary Win %']):.1f}%</td>"
            f"<td>{escape(str(row['Counter Pick']))}</td>"
            f"<td>{float(row['Counter Win %']):.1f}%</td>"
            f"<td><span style='color:{action_color};font-weight:700'>{escape(action)}</span></td>"
            f"<td>{escape(str(row['Recommended Split']))}</td>"
            f"<td>{float(row['Branch Score']):.2f}</td>"
            f"<td>{float(row['Pts At Risk']):.2f}</td>"
            f"<td>{float(row['Expected Pts Team']):.2f}</td>"
            f"<td>{escape(str(row['Reason']))}</td>"
            "</tr>"
        )

    styles = """
    <style>
      .branch-wrap { overflow-x: auto; border: 1px solid #334155; border-radius: 10px; }
      .branch-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
      .branch-table th, .branch-table td { padding: 8px 10px; border-bottom: 1px solid #334155; text-align: left; white-space: nowrap; }
      .branch-table thead th { position: sticky; top: 0; background: #0f172a; color: #e2e8f0; z-index: 1; }
      .branch-table tbody tr:nth-child(even) { background: #111827; }
      .branch-table tbody tr:nth-child(odd) { background: #0b1220; }
    </style>
    """
    table = (
        f"{styles}<div class='branch-wrap'><table class='branch-table'>"
        f"{header}<tbody>{''.join(body_rows)}</tbody></table></div>"
    )
    return table


def _difficulty_info(win_prob: float) -> tuple[str, str]:
    """Map team win probability to difficulty label and color."""
    if win_prob >= 0.75:
        return "Favorable", "#1a7f37"
    if win_prob >= 0.55:
        return "Competitive", "#f59e0b"
    return "Tough", "#ef4444"


st.title("🏀 March Mathness - Tournament Prediction Engine")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    [
        "📊 Power Rankings",
        "📈 Team Traits",
        "🔮 Cinderella Scores",
        "💀 Fraud Alerts",
        "🎯 Matchup Calculator",
        "🎲 Bracket Simulation",
        "📋 Bracket Strategies",
        "🌿 Branching Plan",
        "🛣️ Tournament Paths",
    ]
)

with tab1:
    st.subheader("Power Rankings")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None:
        st.info(f"No rankings found. {PIPELINE_HINT}")
    else:
        c1, c2 = st.columns(2)
        with c1:
            conferences = sorted([c for c in power_df.get("Conference", pd.Series(dtype=str)).dropna().unique().tolist()])
            conf_filter = st.multiselect("Conference", conferences)
        with c2:
            seed_range = st.slider("Seed range", 1, 16, (1, 16))
        view = power_df.copy()
        if conf_filter:
            view = view[view["Conference"].isin(conf_filter)]
        if "Seed" in view.columns:
            view = view[pd.to_numeric(view["Seed"], errors="coerce").between(seed_range[0], seed_range[1])]
        st.dataframe(view, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Team Trait Leaderboards")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None:
        st.info(f"No team traits found. {PIPELINE_HINT}")
    else:
        leaderboards = _build_metric_leaderboards(power_df)
        if not leaderboards:
            st.info("No supported metric columns found in `power_rankings.csv`.")
        else:
            c1, c2 = st.columns([3, 1])
            with c1:
                metric_name = st.selectbox("Ranking category", list(leaderboards.keys()))
            with c2:
                max_teams = max(5, len(power_df))
                top_n = st.slider("Teams shown", 5, max_teams, min(16, max_teams))
            st.dataframe(
                leaderboards[metric_name].head(top_n),
                use_container_width=True,
                hide_index=True
            )

with tab3:
    st.subheader("Cinderella + Giant Killer Rankings")
    cind_df = _read_csv(OUTPUTS / "rankings" / "cinderella_rankings.csv")
    giant_df = _read_csv(OUTPUTS / "rankings" / "giant_killer_rankings.csv")
    if cind_df is None:
        st.info(f"No Cinderella rankings found. {PIPELINE_HINT}")
    else:
        st.markdown("**Cinderella table (seeds 9+)**")
        alert = st.selectbox("Alert filter", ["All", "HIGH", "WATCH"])
        view = cind_df.copy()
        if alert != "All" and "CinderellaAlertLevel" in view.columns:
            view = view[view["CinderellaAlertLevel"] == alert]
        # Use the same 0-1 CinderellaScore shown in terminal alerts to avoid
        # mixing it with the model ranking score scale (~0-100).
        if "CinderellaScore" in view.columns:
            view = view.sort_values("CinderellaScore", ascending=False)
        display_cols = [
            "Rank",
            "Team",
            "Seed",
            "Conference",
            "Record",
            "CinderellaScore",
            "CinderellaAlertLevel",
            "PowerScore",
            "ModelScore",
            "AdjEM",
            "MomentumDelta",
        ]
        present_cols = [col for col in display_cols if col in view.columns]
        if present_cols:
            view = view[present_cols]
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Giant killer table (best upset profiles)**")
    if giant_df is None:
        st.info(f"No giant killer rankings found. {PIPELINE_HINT}")
    else:
        # Giant killer rankings are intentionally restricted to likely upset seeds.
        seed_min, seed_max = st.slider("Giant killer seed range", 6, 16, (8, 13))
        giant_view = giant_df.copy()
        if "Seed" in giant_view.columns:
            giant_view = giant_view[
                pd.to_numeric(giant_view["Seed"], errors="coerce").between(seed_min, seed_max)
            ]
        st.dataframe(giant_view, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Fraud Alerts (Seeds 1-6)")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None or "FraudLevel" not in power_df.columns:
        st.info(f"No fraud alerts found. {PIPELINE_HINT}")
    else:
        fraud = power_df[power_df["FraudLevel"].isin(["HIGH", "MEDIUM", "LOW"])].sort_values("FraudScore", ascending=False)
        st.dataframe(fraud, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Matchup Calculator")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    verdicts_data = _read_json(OUTPUTS / "bracket_matchup_verdicts.json")
    if power_df is None:
        st.info(f"No matchup data found. {PIPELINE_HINT}")
    else:
        if verdicts_data and verdicts_data.get("matchups"):
            st.markdown("**Round of 64 Matchups**")
            matchups_list = verdicts_data["matchups"]
            regions_in_data = []
            seen = set()
            for m in matchups_list:
                r = m.get("region", "")
                if r and r not in seen:
                    regions_in_data.append(r)
                    seen.add(r)
            for region in regions_in_data:
                region_matchups = [m for m in matchups_list if m.get("region") == region]
                if not region_matchups:
                    continue
                st.markdown(f"##### {region}")
                for m in region_matchups:
                    ta = m["team_a"]
                    tb = m["team_b"]
                    pick_name = m["pick"]
                    win_prob_a = float(m["win_prob_a"])
                    # Always display probability for the displayed pick, not team_a.
                    prob = (win_prob_a if pick_name == ta["name"] else 1.0 - win_prob_a) * 100
                    icon = m["verdict_icon"]
                    verdict = m["verdict"]
                    pick = pick_name
                    spread_val = m.get("predicted_spread", 0)
                    col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
                    with col1:
                        st.markdown(f"**({ta['seed']}) {ta['name']}**")
                    with col2:
                        st.markdown(f"vs **({tb['seed']}) {tb['name']}**")
                    with col3:
                        st.markdown(f"{icon} **{verdict}**")
                    with col4:
                        st.markdown(f"Pick: **{pick}** ({prob:.0f}%)")

        st.divider()
        st.markdown("**Custom Matchup**")
        teams = sorted(power_df["Team"].dropna().tolist())
        c1, c2 = st.columns(2)
        with c1:
            team_a_name = st.selectbox("Team A", teams, index=0)
        with c2:
            team_b_name = st.selectbox("Team B", teams, index=min(1, len(teams) - 1))
        if st.button("Calculate", type="secondary"):
            row_a = power_df[power_df["Team"] == team_a_name].iloc[0].to_dict()
            row_b = power_df[power_df["Team"] == team_b_name].iloc[0].to_dict()
            p_a = production_win_probability(row_a, row_b)
            spread = predicted_spread(row_a, row_b)

            if p_a >= 0.5:
                fav_name, dog_name, fav_prob = team_a_name, team_b_name, p_a
            else:
                fav_name, dog_name, fav_prob = team_b_name, team_a_name, 1.0 - p_a
            tier = confidence_tier(fav_prob)
            spread_abs = abs(spread)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"P({team_a_name} wins)", f"{p_a*100:.1f}%")
            m2.metric(f"P({team_b_name} wins)", f"{(1.0 - p_a)*100:.1f}%")
            m3.metric("Predicted spread", f"{fav_name} by {spread_abs:.1f}")
            m4.metric("Pick", f"{fav_name} — {tier}")

with tab6:
    st.subheader("Monte Carlo Simulation")
    st.caption("Simulate the entire tournament thousands of times to estimate each team's probability of advancing.")

    ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 2])
    with ctrl1:
        n_sims = st.slider(
            "Number of simulations", 1000, 50000, 10000, step=1000,
            help="More sims = more stable probabilities but slower. 10K is a good balance.",
        )
    with ctrl2:
        sim_seed = st.number_input(
            "Random seed", value=42, step=1,
            help="Fix this for reproducible results. Change to see alternative outcomes.",
        )
    with ctrl3:
        st.markdown("")
        st.markdown("")
        run_sim = st.button("🎲 Run Simulation", type="primary", use_container_width=True)

    if run_sim:
        csv_path = DATA_DIR / "teams_input.csv"
        bracket_path = DATA_DIR / "bracket_input.json"
        overrides_path = DATA_DIR / "overrides.json"

        if not csv_path.exists():
            st.error("Missing `data/teams_input.csv`. Prepare inputs and run `python main.py --mode full` first.")
        elif not bracket_path.exists():
            st.error("Missing `data/bracket_input.json`. Prepare inputs and run `python main.py --mode full` first.")
        else:
            with st.spinner(f"Simulating {n_sims:,} tournaments..."):
                df = load_teams(str(csv_path), str(overrides_path) if overrides_path.exists() else None)
                bracket = load_bracket(str(bracket_path))
                team_lookup = {str(row["Team"]): row.to_dict() for _, row in df.iterrows()}
                bracket_with_stats = _build_bracket_with_stats(bracket, team_lookup)

                sim_results = simulate_bracket(
                    bracket_with_stats,
                    production_win_probability,
                    n_sims=int(n_sims),
                    seed=int(sim_seed),
                )

            out_path = OUTPUTS / "simulation_results.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps({"results": sim_results, "n_sims": n_sims, "seed": int(sim_seed)}, indent=2),
                encoding="utf-8",
            )
            st.success(f"Completed {n_sims:,} simulations.")

    st.divider()
    sim_payload = _read_json(OUTPUTS / "simulation_results.json")
    if sim_payload is None:
        st.info("Configure settings above and click **Run Simulation** to generate advancement probabilities.")
    else:
        meta1, meta2 = st.columns(2)
        stored_sims = sim_payload.get("n_sims")
        stored_seed = sim_payload.get("seed")
        with meta1:
            st.caption(f"Simulations: **{stored_sims:,}**" if isinstance(stored_sims, int) else "Simulations: **?**")
        with meta2:
            st.caption(f"Seed: **{stored_seed}**" if stored_seed is not None else "Seed: **?**")

        rows = []
        for team, rounds in sim_payload.get("results", {}).items():
            rows.append({"Team": team, **rounds})
        sim_df = pd.DataFrame(rows)
        if not sim_df.empty and "Champion" in sim_df.columns:
            sim_df = sim_df.sort_values("Champion", ascending=False)
            pct_cols = [c for c in sim_df.columns if c != "Team"]
            for col in pct_cols:
                sim_df[col] = (sim_df[col] * 100).round(1)
            sim_df = sim_df.rename(columns={c: f"{c} %" for c in pct_cols})
        st.dataframe(sim_df, use_container_width=True, hide_index=True)

with tab7:
    st.subheader("Bracket Strategies")
    summary_payload = _read_json(OUTPUTS / "bracket_summary.json")

    if summary_payload:
        st.markdown("**Cross-Strategy Consensus**")
        cons_cols = st.columns(2)
        with cons_cols[0]:
            st.metric("Consensus Champion", summary_payload.get("champion_consensus", "N/A"))
            champ_counts = summary_payload.get("champion_counts", {})
            if champ_counts:
                total = summary_payload.get("n_strategies", 1)
                parts = [f"{t} ({c}/{total})" for t, c in sorted(champ_counts.items(), key=lambda x: -x[1])]
                st.caption("Champion picks: " + ", ".join(parts))
        with cons_cols[1]:
            ff_consensus = summary_payload.get("final_four_consensus", [])
            st.metric("Consensus Final Four", ", ".join(ff_consensus[:4]) if ff_consensus else "N/A")
            ff_counts = summary_payload.get("final_four_counts", {})
            if ff_counts:
                total = summary_payload.get("n_strategies", 1)
                parts = [f"{t} ({c}/{total})" for t, c in sorted(ff_counts.items(), key=lambda x: -x[1])[:8]]
                st.caption("FF appearances: " + ", ".join(parts))
        st.divider()

    strategy_names = ["standard", "favorites", "upsets", "analytics", "cinderella", "defensive", "momentum"]
    strategy = st.selectbox("Explore Strategy", strategy_names)
    bracket_payload = _read_json(OUTPUTS / "brackets" / f"bracket_{strategy}.json")
    if bracket_payload is None:
        st.info("Run full analysis to generate strategy brackets.")
    else:
        st.markdown(f"*{bracket_payload.get('description', '')}*")
        c1, c2 = st.columns(2)
        c1.metric("Champion", bracket_payload.get("champion", "TBD"))
        c2.metric("Runner-Up", bracket_payload.get("runner_up", "TBD"))

        ff_teams = bracket_payload.get("final_four", [])
        st.markdown(f"**Final Four:** {', '.join(ff_teams)}")

        ff_games = bracket_payload.get("final_four_games", [])
        champ_game = bracket_payload.get("championship_game", [])
        if ff_games or champ_game:
            st.markdown("---")
            if ff_games:
                st.markdown("**Semifinal Matchups**")
                for g in ff_games:
                    prob_pct = g["win_probability"] * 100
                    upset_tag = " ⚡ UPSET" if g.get("is_upset") else ""
                    st.markdown(
                        f"- ({g['higher_seed_seed']}) {g['higher_seed_team']} vs "
                        f"({g['lower_seed_seed']}) {g['lower_seed_team']} "
                        f"&rarr; **{g['predicted_winner']}** ({prob_pct:.0f}%){upset_tag}"
                    )
            if champ_game:
                st.markdown("**Championship**")
                for g in champ_game:
                    prob_pct = g["win_probability"] * 100
                    st.markdown(
                        f"- ({g['higher_seed_seed']}) {g['higher_seed_team']} vs "
                        f"({g['lower_seed_seed']}) {g['lower_seed_team']} "
                        f"&rarr; 🏆 **{g['predicted_winner']}** ({prob_pct:.0f}%)"
                    )

        rounds_data = bracket_payload.get("rounds", {})
        total_upsets = sum(
            1 for region_rounds in rounds_data.values()
            for games in region_rounds.values()
            for g in games if g.get("is_upset")
        )
        total_games = sum(
            len(games)
            for region_rounds in rounds_data.values()
            for games in region_rounds.values()
        )
        st.markdown(f"**Upsets predicted:** {total_upsets} / {total_games} games")

        with st.expander("Region-by-region detail"):
            for region, region_rounds in rounds_data.items():
                st.markdown(f"##### {region}")
                for round_name, games in region_rounds.items():
                    upsets_in_round = [g for g in games if g.get("is_upset")]
                    if upsets_in_round:
                        for g in upsets_in_round:
                            st.markdown(
                                f"- ⚡ **{round_name}**: ({g['lower_seed_seed']}) {g['lower_seed_team']} "
                                f"over ({g['higher_seed_seed']}) {g['higher_seed_team']} "
                                f"({g['win_probability']*100:.0f}%)"
                            )

with tab8:
    st.subheader("Branching Plan (Locks vs Splits)")
    st.caption(
        "Use this as your multi-entry map: keep LOCK games identical across brackets, "
        "then split only at high-priority BRANCH nodes."
    )

    summary_payload = _read_json(OUTPUTS / "bracket_summary.json")
    sim_payload = _read_json(OUTPUTS / "simulation_results.json")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if summary_payload is None:
        st.info(f"No branch data found. {PIPELINE_HINT}")
    else:
        branch_df = _build_branch_plan_df(summary_payload, sim_payload, power_df)
        if branch_df.empty:
            st.info("No branchable games found in the modal bracket path.")
        else:
            c1, c2 = st.columns([2, 2])
            with c1:
                include_locks = st.checkbox("Include LOCK rows", value=True)
            with c2:
                min_score = st.slider("Minimum branch score", 0.0, 4.0, 1.0, 0.1)

            view = branch_df.copy()
            if not include_locks:
                view = view[view["Action"] != "LOCK"]
            view = view[view["Branch Score"] >= min_score]

            st.markdown(_branch_table_html(view), unsafe_allow_html=True)
            st.download_button(
                "Download branch plan (HTML)",
                data=_branch_table_html(view),
                file_name="branching_plan.html",
                mime="text/html",
            )

with tab9:
    st.subheader("Tournament Path Matchups (Top 20 Teams)")
    st.caption(
        "For each top-20 power team, this shows all possible opponents by round in its bracket path. "
        "Final Four and Championship are capped to the 6 most likely opponents."
    )
    path_payload = _read_json(OUTPUTS / "matchup_paths" / "team_paths.json")
    if path_payload is None:
        st.info(f"No tournament path output found. {PIPELINE_HINT}")
    else:
        team_paths = path_payload.get("team_paths", {})
        if not isinstance(team_paths, dict) or not team_paths:
            st.info("Tournament path file is empty. Run `python main.py --mode full` to regenerate.")
        else:
            team_names = sorted(
                team_paths.keys(),
                key=lambda name: (
                    int(team_paths.get(name, {}).get("power_rank") or 999),
                    name,
                ),
            )
            selected_team = st.selectbox("Select team", team_names)
            selected_payload = team_paths.get(selected_team, {})
            rank_val = selected_payload.get("power_rank")
            seed_val = selected_payload.get("seed")
            region_val = selected_payload.get("region")
            slot_val = selected_payload.get("slot")
            st.markdown(
                f"**{selected_team}**  |  Rank: **{rank_val}**  |  Seed: **{seed_val}**  |  "
                f"Region: **{region_val}**  |  Slot: **{slot_val}**"
            )

            rounds = selected_payload.get("rounds", {})
            for round_name in PATH_ROUND_ORDER:
                st.markdown(f"#### {round_name}")
                if round_name in {"F4", "Championship"}:
                    st.caption("Showing top 6 most likely opponents by meeting probability.")
                rows = rounds.get(round_name, [])
                if not rows:
                    st.write("No valid opponents found for this round.")
                    continue

                table_rows: list[dict[str, object]] = []
                for row in rows:
                    win_prob = float(row.get("win_prob", 0.0))
                    meet_prob = float(row.get("meeting_prob", 0.0))
                    difficulty, _ = _difficulty_info(win_prob)
                    table_rows.append(
                        {
                            "Opponent": row.get("team", ""),
                            "Seed": int(row.get("seed", 16)),
                            "Win Prob %": round(win_prob * 100, 1),
                            "Meeting Prob %": round(meet_prob * 100, 2),
                            "Power Rank": row.get("power_rank", ""),
                            "AdjEM": row.get("adjEM", 0.0),
                            "Difficulty": difficulty,
                        }
                    )

                table_df = pd.DataFrame(table_rows)

                def _style_row(r: pd.Series) -> list[str]:
                    _, color = _difficulty_info(float(r.get("Win Prob %", 0.0)) / 100.0)
                    return [f"background-color: {color}22" if c == "Difficulty" else "" for c in r.index]

                st.dataframe(
                    table_df.style.apply(_style_row, axis=1),
                    use_container_width=True,
                    hide_index=True,
                )
