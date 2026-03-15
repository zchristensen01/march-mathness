"""Streamlit UI for March Mathness."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.win_probability import confidence_tier, predicted_spread, production_win_probability

st.set_page_config(
    page_title="March Mathness",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

OUTPUTS = Path("outputs")


def _read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _run_pipeline(mode: str, sims: int, seed: int) -> tuple[bool, str]:
    cmd = [sys.executable, "main.py", "--mode", mode, f"--sims={sims}", f"--seed={seed}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, proc.stdout
    return False, proc.stderr


st.title("🏀 March Mathness - Tournament Prediction Engine")

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_csv = st.file_uploader("Upload teams_input.csv", type=["csv"])
    uploaded_bracket = st.file_uploader("Upload bracket_input.json", type=["json"])
    n_sims = st.slider("Monte Carlo simulations", 1000, 50000, 10000, step=1000)
    seed = st.number_input("Random seed", value=42, step=1)

    st.header("🩹 Injury Overrides")
    override_text = st.text_area(
        "Paste overrides.json payload",
        value='{\n  "TeamName": {\n    "mode": "delta",\n    "AdjEM": -2.5\n  }\n}',
        height=140
    )

    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.header("🔄 Mid-Tournament Update")
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
        ok, log_text = _run_pipeline(mode, int(n_sims), int(seed))
    if ok:
        st.success("Analysis completed.")
    else:
        st.error("Pipeline failed.")
        st.code(log_text[-2000:])

if update_button:
    with st.spinner("Running update mode..."):
        ok, log_text = _run_pipeline("update", int(n_sims), int(seed))
    if ok:
        st.success("Mid-tournament update completed.")
    else:
        st.error("Update failed.")
        st.code(log_text[-2000:])

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "📊 Power Rankings",
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
    st.subheader("Cinderella Rankings (Seeds 9+)")
    cind_df = _read_csv(OUTPUTS / "rankings" / "cinderella_rankings.csv")
    if cind_df is None:
        st.info("Run analysis to generate Cinderella rankings.")
    else:
        alert = st.selectbox("Alert filter", ["All", "HIGH", "WATCH"])
        view = cind_df
        if alert != "All" and "CinderellaAlertLevel" in view.columns:
            view = view[view["CinderellaAlertLevel"] == alert]
        st.dataframe(view, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Fraud Alerts (Seeds 1-6)")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None or "FraudLevel" not in power_df.columns:
        st.info("Run analysis to generate fraud alerts.")
    else:
        fraud = power_df[power_df["FraudLevel"].isin(["HIGH", "MEDIUM", "LOW"])].sort_values("FraudScore", ascending=False)
        st.dataframe(fraud, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Conference Strength")
    conf_df = _read_csv(OUTPUTS / "rankings" / "conference_strength.csv")
    if conf_df is None:
        st.info("Run analysis to generate conference strengths.")
    else:
        st.dataframe(conf_df, use_container_width=True, hide_index=True)
        if "Conference" in conf_df.columns and "CSI_multiplier" in conf_df.columns:
            st.bar_chart(conf_df.set_index("Conference")[["CSI_multiplier"]])

with tab5:
    st.subheader("Matchup Calculator")
    power_df = _read_csv(OUTPUTS / "rankings" / "power_rankings.csv")
    if power_df is None:
        st.info("Run analysis first.")
    else:
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

with tab6:
    st.subheader("Simulation Results")
    sim_payload = _read_json(OUTPUTS / "simulation_results.json")
    if sim_payload is None:
        st.info("Run full analysis with bracket input.")
    else:
        rows = []
        for team, rounds in sim_payload.get("results", {}).items():
            rows.append({"Team": team, **rounds})
        sim_df = pd.DataFrame(rows)
        if not sim_df.empty and "Champion" in sim_df.columns:
            sim_df = sim_df.sort_values("Champion", ascending=False)
        st.dataframe(sim_df, use_container_width=True, hide_index=True)

with tab7:
    st.subheader("Bracket Strategies")
    strategy = st.selectbox(
        "Strategy",
        ["standard", "favorites", "upsets", "analytics", "cinderella", "defensive", "momentum", "experience"]
    )
    bracket_payload = _read_json(OUTPUTS / "brackets" / f"bracket_{strategy}.json")
    summary_payload = _read_json(OUTPUTS / "bracket_summary.json")
    if bracket_payload is None:
        st.info("Run full analysis to generate strategy brackets.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Champion", bracket_payload.get("champion", "TBD"))
        c2.metric("Strategy", bracket_payload.get("strategy", strategy).title())
        c3.metric("Final Four Teams", len(bracket_payload.get("final_four", [])))
        st.write("Final Four:", ", ".join(bracket_payload.get("final_four", [])))
        if summary_payload:
            st.caption(f"Champion consensus: {summary_payload.get('champion_consensus', 'N/A')}")

with tab8:
    st.subheader("Pick Sheet")
    pick_path = OUTPUTS / "my_bracket_picks.txt"
    if not pick_path.exists():
        st.info("Run full analysis to generate pick sheet.")
    else:
        content = pick_path.read_text(encoding="utf-8")
        st.code(content)
        st.download_button("Download Pick Sheet", content, "march_mathness_picks.txt", "text/plain")

