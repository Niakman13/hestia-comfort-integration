"""Home synthesis from the room views: it summarises rooms, it never replaces their advice."""
SEVERITY = {"urgent": 4, "action": 3, "benefit": 2, "neutral": 1, "calm": 0}
OPPOSITE = {("E", "O"), ("N", "S"), ("NE", "SO"), ("SE", "NO")}


def _value(view, key):
    reading = view.get("observations", {}).get(key)
    if reading and reading.get("quality") == "valid" and isinstance(reading.get("value"), (int, float)):
        return reading["value"]
    return None


def synthesis(views):
    """Views are the per-room payloads published by the coordinators."""
    rooms = []
    for view in views:
        a = view["assessment"]
        names = view.get("names", {})
        openings = a.get("openings", [])
        rooms.append({"entry_id": view["entry_id"], "title": view["title"], "level": a["level"], "action": a["action"],
                      "temperature": _value(view, "indoor_temperature"), "needs": list(a["needs"]),
                      "open": [names.get(o["entity_id"], o["entity_id"]) for o in openings if o.get("open")],
                      "open_exposures": [o["exposure"] for o in openings if o.get("open") and o.get("exposure")],
                      "sun_entering": [names.get(o["entity_id"], o["entity_id"]) for o in openings if "sun_entering" in o.get("flags", [])],
                      "partial": a["partial"]})
    # The room that needs the most attention leads; a gesture to make beats a mere observation.
    focus = max(rooms, key=lambda r: (SEVERITY.get(r["level"], 0), r["action"] not in ("ok", "unknown")), default=None)
    measured = [r for r in rooms if r["temperature"] is not None]
    hottest = max(measured, key=lambda r: r["temperature"]) if len(measured) > 1 else None
    coolest = min(measured, key=lambda r: r["temperature"]) if len(measured) > 1 else None
    exposures = {e for r in rooms for e in r["open_exposures"]}
    if any((a, b) in OPPOSITE or (b, a) in OPPOSITE for a in exposures for b in exposures):
        crossing = "strong"
    elif len(exposures) > 1:
        crossing = "partial"
    elif exposures:
        crossing = "none"
    else:
        crossing = None
    # Where to start cooling: the warmest room that needs fresh air and can get it now.
    candidates = [r for r in measured if "cool" in r["needs"] and r["action"] == "ouvrir"]
    start = max(candidates, key=lambda r: r["temperature"], default=None)
    outdoor = next((_value(v, "outdoor_temperature") for v in views if _value(v, "outdoor_temperature") is not None), None)
    return {"level": focus["level"] if focus else "neutral",
            "focus": focus["entry_id"] if focus else None,
            "hottest": hottest and {"entry_id": hottest["entry_id"], "title": hottest["title"], "temperature": hottest["temperature"]},
            "coolest": coolest and {"entry_id": coolest["entry_id"], "title": coolest["title"], "temperature": coolest["temperature"]},
            "spread": round(hottest["temperature"] - coolest["temperature"], 1) if hottest and coolest else None,
            "open_rooms": [{"title": r["title"], "open": r["open"]} for r in rooms if r["open"]],
            "crossing": crossing, "start_with": start and start["title"],
            "sun_entering": [{"title": r["title"], "openings": r["sun_entering"]} for r in rooms if r["sun_entering"]],
            "outdoor_temperature": outdoor, "partial": any(r["partial"] for r in rooms)}
