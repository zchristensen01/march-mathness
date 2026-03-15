"""Probability calibration utilities."""

from __future__ import annotations

import pickle
from pathlib import Path

from sklearn.isotonic import IsotonicRegression


def fit_isotonic_calibration(probs: list[float], outcomes: list[int]) -> IsotonicRegression:
    """Fit isotonic regression calibration model."""
    model = IsotonicRegression(y_min=0.03, y_max=0.97, out_of_bounds="clip")
    model.fit(probs, outcomes)
    return model


def calibrate_probability(raw_prob: float, model: IsotonicRegression | None) -> float:
    """Transform raw probability through isotonic model if available."""
    if model is None:
        return raw_prob
    calibrated = float(model.predict([raw_prob])[0])
    return max(0.03, min(0.97, calibrated))


def save_calibration_model(model: IsotonicRegression, path: str = "models/calibration.pkl") -> None:
    """Persist trained isotonic model."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        pickle.dump(model, f)


def load_calibration_model(path: str = "models/calibration.pkl") -> IsotonicRegression | None:
    """Load calibration model if it exists."""
    model_path = Path(path)
    if not model_path.exists():
        return None
    with model_path.open("rb") as f:
        return pickle.load(f)

