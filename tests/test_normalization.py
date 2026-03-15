from engine.normalization import normalize_inverse, normalize_value


def test_normalize_value_bounds() -> None:
    assert normalize_value(40, -20, 40) == 1.0
    assert normalize_value(-20, -20, 40) == 0.0
    assert normalize_value(None, 0, 1) == 0.5


def test_normalize_inverse_bounds() -> None:
    assert normalize_inverse(80, 80, 125) == 1.0
    assert normalize_inverse(125, 80, 125) == 0.0


def test_sos_direction_inverse() -> None:
    hardest = normalize_inverse(1, 1, 365)
    easiest = normalize_inverse(365, 1, 365)
    assert hardest > easiest

