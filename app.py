"""Streamlit UI for March Mathness."""

from __future__ import annotations

import json
import subprocess
import sys
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
    initial_sidebar_state="expanded"
)

OUTPUTS = Path("outputs")
DATA_DIR = Path("data")


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


def _run_pipeline(mode: str) -> tuple[bool, str]:
    cmd = [sys.executable, "main.py", "--mode", mode]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, proc.stdout
    return False, proc.stderr


st.title("🏀 March Mathness - Tournament Prediction Engine")

with st.sidebar:
    st.header("⚙️ Configuration")
    st.caption("Upload your data files, then click **Run Analysis** to generate all predictions.")

    uploaded_csv = st.file_uploader(
        "Team stats CSV",
        type=["csv"],
        help="teams_input.csv — one row per tournament team with stats columns from Torvik/KenPom"
    )
    uploaded_bracket = st.file_uploader(
        "Bracket structure JSON",
        type=["json"],
        help="bracket_input.json — defines seeds, regions, and slots. Required for bracket simulation."
    )

    st.divider()
    st.subheader("🩹 Injury / Adjustment Overrides")
    st.caption("Adjust team efficiency for injuries, suspensions, or other factors.")
    override_text = st.text_area(
        "overrides.json",
        value='{\n  "TeamName": {\n    "mode": "delta",\n    "AdjEM": -2.5\n  }\n}',
        height=120,
        help="Use delta mode to shift a team's AdjEM. Negative = weaker (e.g. key player out)."
    )

    st.divider()
    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.subheader("🔄 Mid-Tournament Update")
    st.caption("Pulls live results from ESPN and re-scores surviving teams with tournament bonuses.")
    update_button = st.button("Fetch and Re-Score", use_container_width=True)

if run_button and uploaded_csv is not None:
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "teams_input.csv").write_bytes(uploaded_csv.getvalue())
    if uploaded_bracket is not None:
        (data_dir / "bracket_input.json").write_bytes(uploaded_bracket.getvalue())
    try:
        override_payload = json.loads(override_text)
        (data_dir / "overrides.json").write_text(json.dumps(override_payload, indent=2), encoding="utf-8")
    except Exception as exc:
        st.warning(f"Overrides JSON ignored: {exc}")
    mode = "full" if uploaded_bracket is not None else "rankings"
    with st.spinner("Running pipeline..."):
        ok, log_text = _run_pipeline(mode)
    if ok:
        st.success("Analysis completed.")
    else:
        st.error("Pipeline failed.")
        st.code(log_text[-2000:])

if update_button:
    with st.spinner("Running update mode..."):
        ok, log_text = _run_pipeline("update")
    if ok:
        st.success("Mid-tournament update completed.")
    else:
        st.error("Update failed.")
        st.code(log_text[-2000:])

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
    [
        "📊 Power Rankings",
        "📈 Team Traits",
        "🔮 Cinderella Scores",
        "💀 Fraud Alerts",
        "🏆 Conference Strength",
        "🎯 Matchup Calculator",
        "🎲 Bracket Simulation",
        "📋 Bracket Strategies",
        "📄 Pick Sheet"
    ]
)

with tab1:
    st.subheader("Power Rankings")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None:
        st.info("Run analysis to generate rankings.")
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
        st.info("Run analysis to generate team trait leaderboards.")
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
        st.info("Run analysis to generate Cinderella rankings.")
    else:
        st.markdown("**Cinderella table (seeds 9+)**")
        alert = st.selectbox("Alert filter", ["All", "HIGH", "WATCH"])
        view = cind_df
        if alert != "All" and "CinderellaAlertLevel" in view.columns:
            view = view[view["CinderellaAlertLevel"] == alert]
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Giant killer table (best upset profiles)**")
    if giant_df is None:
        st.info("Run analysis to generate giant killer rankings.")
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
        st.info("Run analysis to generate fraud alerts.")
    else:
        fraud = power_df[power_df["FraudLevel"].isin(["HIGH", "MEDIUM", "LOW"])].sort_values("FraudScore", ascending=False)
        st.dataframe(fraud, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Conference Strength")
    conf_df = _read_csv(OUTPUTS / "rankings" / "conference_strength.csv")
    if conf_df is None:
        st.info("Run analysis to generate conference strengths.")
    else:
        st.dataframe(conf_df, use_container_width=True, hide_index=True)
        if "Conference" in conf_df.columns and "CSI_multiplier" in conf_df.columns:
            st.bar_chart(conf_df.set_index("Conference")[["CSI_multiplier"]])

with tab6:
    st.subheader("Matchup Calculator")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    verdicts_data = _read_json(OUTPUTS / "bracket_matchup_verdicts.json")
    if power_df is None:
        st.info("Run analysis first.")
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
            tier = confidence_tier(p_a)
            m1, m2, m3 = st.columns(3)
            m1.metric(f"P({team_a_name} wins)", f"{p_a*100:.1f}%")
            m2.metric("Predicted spread", f"{team_a_name} {spread:+.1f}")
            m3.metric("Confidence", tier)

with tab7:
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
            st.error("Missing `data/teams_input.csv`. Upload team stats and run analysis first.")
        elif not bracket_path.exists():
            st.error("Missing `data/bracket_input.json`. Upload bracket JSON and run analysis first.")
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

with tab8:
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

with tab9:
    st.subheader("Pick Sheet")
    pick_path = OUTPUTS / "my_bracket_picks.txt"
    if not pick_path.exists():
        st.info("Run full analysis to generate pick sheet.")
    else:
        content = pick_path.read_text(encoding="utf-8")
        st.code(content)
        st.download_button("Download Pick Sheet", content, "march_mathness_picks.txt", "text/plain")

