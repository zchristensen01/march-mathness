import pandas as pd

from engine.ingestion import compute_rank_features


def test_compute_rank_features_weighted_composite_and_confidence() -> None:
    df = pd.DataFrame(
        [
            {"Team": "A", "NET_Rank": 8, "Massey_Rank": 14, "Torvik_Rank": 18},
            {"Team": "B", "Massey_Rank": 22, "Torvik_Rank": 30},
            {"Team": "C", "Torvik_Rank": 40},
        ]
    )
    out = compute_rank_features(df)

    expected_a = (8 * 0.45 + 14 * 0.30 + 18 * 0.25) / (0.45 + 0.30 + 0.25)
    expected_b = (22 * 0.30 + 30 * 0.25) / (0.30 + 0.25)

    assert abs(float(out.loc[0, "CompRank"]) - expected_a) < 1e-9
    assert abs(float(out.loc[1, "CompRank"]) - expected_b) < 1e-9
    assert abs(float(out.loc[2, "CompRank"]) - 40.0) < 1e-9

    assert float(out.loc[0, "CompRank_Confidence"]) == 1.0
    assert float(out.loc[1, "CompRank_Confidence"]) == 0.75
    assert float(out.loc[2, "CompRank_Confidence"]) == 0.5


def test_compute_rank_features_respects_raw_availability() -> None:
    df = pd.DataFrame(
        [
            {"Team": "A", "NET_Rank": 8, "Massey_Rank": 150, "Torvik_Rank": 18},
        ]
    )
    # Simulate a default-filled Massey value that was actually missing in source.
    raw_availability = {
        "NET_Rank": pd.Series([True]),
        "Massey_Rank": pd.Series([False]),
        "Torvik_Rank": pd.Series([True]),
    }
    out = compute_rank_features(df, rank_availability=raw_availability)
    expected = (8 * 0.45 + 18 * 0.25) / (0.45 + 0.25)
    assert abs(float(out.loc[0, "CompRank"]) - expected) < 1e-9
    assert float(out.loc[0, "CompRank_Confidence"]) == 0.75
