"""March Mathness engine package."""

FIRST_ROUND_MATCHUPS: list[tuple[int, int]] = [
    (0, 1),
    (2, 3),
    (4, 5),
    (6, 7),
    (8, 9),
    (10, 11),
    (12, 13),
    (14, 15)
]

ROUND_NAMES: list[str] = ["R64", "R32", "S16", "E8", "F4", "Championship", "Champion"]

FINAL_FOUR_REGION_ORDER: tuple[str, str, str, str] = ("East", "West", "South", "Midwest")


def order_final_four_regions(regions: list[str]) -> list[str]:
    """Return region order used for Final Four semifinals.

    If all canonical region names are present, we force canonical order so
    semis are always East vs West and South vs Midwest. Otherwise we preserve
    the caller's order as a safe fallback for custom tournaments.
    """
    canonical_lookup = {name.lower(): name for name in regions}
    canonical_keys = {name.lower() for name in FINAL_FOUR_REGION_ORDER}
    if canonical_keys.issubset(set(canonical_lookup.keys())):
        return [canonical_lookup[name.lower()] for name in FINAL_FOUR_REGION_ORDER]
    return list(regions)

