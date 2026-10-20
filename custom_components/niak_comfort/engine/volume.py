"""Rooms open onto each other share one air: their openings are common and they never give opposite gestures.

Each room still reads its own sensors and finds its own needs. When two rooms of one volume disagree
(one says close, the other open or keep open), the weightier reason speaks for the whole volume; the
other room says whom it follows instead of contradicting it.
"""

# Weather on the shared openings, then a need for air, then comfort reasons to close, then the rest.
SAFETY = ("rain_open_windows", "gust_open_windows", "rain_soon")
HARD = {"storm", "vigilance", "pollution", "rain", "rain_soon"}
AIR = ("air_needed", "short_air_change")
COMFORT_CLOSE = ("exchange_harmful", "rehumidification_risk", "heat_needed", "sun_entering", "opening_blocked")
OPEN = ("cooling_possible", "drying_possible", "precool_possible")


def weight(assessment: dict) -> int:
    reason, action = assessment.get("reason"), assessment.get("action")
    if reason in SAFETY or (reason == "opening_blocked" and action == "fermer" and HARD & set(assessment.get("constraints", ()))):
        return 4
    if reason in AIR:
        return 3
    if reason in COMFORT_CLOSE and action == "fermer":
        return 2
    if reason in OPEN:
        return 1
    return 0


def _side(assessment: dict) -> str | None:
    """« shut », « open » (keeping an open window open counts), or None when the room asks no window gesture."""
    action = assessment.get("action")
    if action == "fermer":
        return "shut"
    if action == "ouvrir" or (action == "ok" and assessment.get("reason") in AIR + OPEN):
        return "open"
    return None


def arbitrate(own: dict, partners: list[tuple[str, dict]]) -> dict:
    """`own` and each partner's assessment as computed alone; returns `own`, followed when a partner outweighs it.

    Only opposite gestures are settled; two rooms asking the same thing both keep their words."""
    mine = _side(own)
    if mine is None:
        return own
    lead = None
    for title, other in partners:
        theirs = _side(other)
        if theirs is None or theirs == mine or weight(other) <= weight(own):
            continue
        if lead is None or weight(other) > weight(lead[1]):
            lead = (title, other)
    if lead is None:
        return own
    title, other = lead
    action = other["action"]
    if action == "ouvrir" and any(o.get("open") for o in own.get("openings", ())):
        action = "ok"  # the shared window is already open: keep it so
    features = {**own.get("features", {}), "volume": {"lead": title, "reason": other["reason"], "action": other["action"]}}
    return {**own, "action": action, "reason": "shared_volume", "level": other["level"], "features": features,
            "open_first": tuple(other.get("open_first", ())) if action == "ouvrir" else ()}
