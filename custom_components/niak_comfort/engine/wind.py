"""Wind against the openings: which side the wind hits, where the air goes through, what to open."""
EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
WINDWARD_ANGLE = 60      # wind coming from within 60° of the facade's direction
DRIVEN_RAIN_GUST = 25    # km/h: from there, rain is pushed under a roof overhang


def gap(a: float, b: float) -> float:
    return abs(((a - b + 540) % 360) - 180)


def side(exposure: str | None, bearing: float | None) -> str | None:
    """Bearing is where the wind comes from (meteorological convention)."""
    if exposure not in EXPOSURES or bearing is None:
        return None
    facing = EXPOSURES[exposure]
    if gap(bearing, facing) < WINDWARD_ANGLE:
        return "windward"
    if gap(bearing, (facing + 180) % 360) < WINDWARD_ANGLE:
        return "leeward"
    return "side"


def crossing(openings: list[dict]) -> str | None:
    """How the air crosses the room through the open openings."""
    opened = [o for o in openings if o.get("open")]
    if not opened:
        return None
    sides = {o.get("wind_side") for o in opened}
    if {"windward", "leeward"} <= sides:
        return "wind"
    exposures = {o.get("exposure") for o in opened if o.get("exposure")}
    if any(gap(EXPOSURES[a], EXPOSURES[b]) >= 135 for a in exposures for b in exposures):
        return "opposite"
    return "two_sides" if len(exposures) > 1 else "one_side"


def open_first(openings: list[dict]) -> list[str]:
    """The openings to open for the best sweep: one into the wind and one out of it, else the closed ones."""
    closed = [o for o in openings if o.get("open") is False and not o.get("flags")]
    weight = {"french": 3, "window": 2, "door": 1, "skylight": 0}
    best = lambda items: max(items, key=lambda o: weight.get(o.get("kind"), 1))["entity_id"] if items else None
    into = best([o for o in closed if o.get("wind_side") == "windward"])
    out = best([o for o in closed if o.get("wind_side") == "leeward"])
    if into and out:
        return [into, out]
    return [x for x in (into, out) if x] or [o["entity_id"] for o in closed][:2]
