import pandas as pd

from engine.scoring import compute_cinderella_score, compute_fraud_score, generate_all_rankings


def test_scope_guards_for_cinderella_and_fraud() -> None:
    c_result = compute_cinderella_score({"Seed": 4, "CompRank": 10, "Adj_T": 68}, {})
    f_result = compute_fraud_score({"Seed": 12, "CompRank": 120}, {})
    assert c_result["CinderellaScore"] == 0.0
    assert f_result["FraudScore"] == 0.0


def test_generate_all_rankings_smoke() -> None:
    df = pd.DataFrame(
        [
            {
                "Team": "A",
                "Seed": 1,
                "Conference": "SEC",
                "Record": "30-3",
                "AdjEM": 25,
                "AdjO": 121,
                "AdjD": 96,
                "Barthag": 0.95,
                "eFG%": 56,
                "Opp_eFG%": 45,
                "TO%": 14,
                "Opp_TO%": 21,
                "OR%": 34,
                "DR%": 75,
                "FTR": 35,
                "FT%": 76,
                "SOS": 20,
                "Adj_T": 68,
                "WAB": 8,
                "Torvik_Rank": 5,
                "NET_Rank": 4,
                "CompRank": 5,
                "AP_Poll_Rank": 2,
                "Exp": 2.0,
                "Coach_Tourney_Experience": 8,
                "Program_Prestige": 9,
                "Last_10_Games_Metric": 0.8,
                "Luck": 0.02,
                "Consistency_Score": 0.7,
                "Volatility_Score": 0.3,
                "CSI": 2.0,
                "CSI_multiplier": 1.0,
                "OverrideActive": 0
            },
            {
                "Team": "B",
                "Seed": 12,
                "Conference": "MVC",
                "Record": "23-10",
                "AdjEM": 8,
                "AdjO": 112,
                "AdjD": 104,
                "Barthag": 0.78,
                "eFG%": 52,
                "Opp_eFG%": 48,
                "TO%": 16,
                "Opp_TO%": 20,
                "OR%": 30,
                "DR%": 71,
                "FTR": 32,
                "FT%": 75,
                "SOS": 120,
                "Adj_T": 64,
                "WAB": 2,
                "Torvik_Rank": 65,
                "NET_Rank": 70,
                "CompRank": 68,
                "AP_Poll_Rank": 26,
                "Exp": 2.2,
                "Coach_Tourney_Experience": 4,
                "Program_Prestige": 2,
                "Last_10_Games_Metric": 0.75,
                "Luck": -0.01,
                "Consistency_Score": 0.6,
                "Volatility_Score": 0.5,
                "CSI": -1.0,
                "CSI_multiplier": 0.92,
                "OverrideActive": 0
            }
        ]
    )
    norms = [
        {"AdjEM": 0.9, "CompRank_inv": 0.95, "SOS_inv": 0.9, "eFG%": 0.8, "Opp_eFG%_inv": 0.85, "Opp_TO%": 0.7, "TO%_inv": 0.7, "OR%": 0.7, "DR%": 0.65, "FTR": 0.6, "FT%": 0.6, "Barthag": 0.9, "Last_10_Games_Metric": 0.75, "Exp": 0.66, "Quad1_Wins": 0.8, "Star_Player_Index": 0.7, "Bench_Minutes_Pct": 0.6, "3P_Rate": 0.5},
        {"AdjEM": 0.45, "CompRank_inv": 0.75, "SOS_inv": 0.65, "eFG%": 0.55, "Opp_eFG%_inv": 0.6, "Opp_TO%": 0.65, "TO%_inv": 0.6, "OR%": 0.55, "DR%": 0.5, "FTR": 0.55, "FT%": 0.56, "Barthag": 0.72, "Last_10_Games_Metric": 0.65, "Exp": 0.73, "Quad1_Wins": 0.4, "Star_Player_Index": 0.5, "Bench_Minutes_Pct": 0.45, "3P_Rate": 0.6}
    ]
    deriveds = [
        {"Physicality": 0.65, "BallMovement": 0.72, "CloseGame": 0.8, "TournamentReadiness": 0.85, "DefensivePlaymaking": 0.7, "InsideScoring": 0.76, "InteriorDefense": 0.74, "NETMomentum": 0.6},
        {"Physicality": 0.52, "BallMovement": 0.58, "CloseGame": 0.66, "TournamentReadiness": 0.62, "DefensivePlaymaking": 0.6, "InsideScoring": 0.59, "InteriorDefense": 0.57, "NETMomentum": 0.55}
    ]
    csi = [1.0, 0.92]
    rankings = generate_all_rankings(df, norms, deriveds, csi)
    assert "power" in rankings
    assert not rankings["power"].empty

