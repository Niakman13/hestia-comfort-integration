"""The next hours, from the Niak Weather forecast: when opening will help, when to close, rain coming."""
from datetime import datetime, timedelta


def _at(item) -> datetime | None:
    try:
        return datetime.fromisoformat(item["time"])
    except (KeyError, TypeError, ValueError):
        return None


def slot(hours: list[dict], now: datetime, indoor: float | None, *, hot: bool, cool_now: bool, margin: float,
         horizon: int = 18) -> dict | None:
    """First hour when the outside becomes fresh enough to open, or warmer than inside again (template « créneau »)."""
    if indoor is None or not hot:
        return None
    future = [(t, h) for h in hours if (t := _at(h)) and now < t <= now + timedelta(hours=horizon)
              and isinstance(h.get("temperature"), (int, float))]
    for t, h in sorted(future, key=lambda x: x[0]):
        fresh = h["temperature"] <= indoor - margin
        if (not cool_now and fresh) or (cool_now and h["temperature"] > indoor):
            return {"kind": "close" if cool_now else "open", "time": t.isoformat(), "temperature": h["temperature"],
                    "wind_bearing": h.get("wind_bearing")}
    return None


def rain_soon(hours_until: float | None, limit: float = 1.0) -> float | None:
    """Minutes before the next rain when it is within `limit` hours, else None."""
    if hours_until is None or hours_until < 0 or hours_until > limit:
        return None
    return round(hours_until * 60)
