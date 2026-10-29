"""The comfort review of the home, read from Home Assistant's long-term statistics (engine/review.py grades it).

The recorder keeps detailed states for ten days only, but hourly means for months: a year of them is read for each
room's temperature, humidity and CO₂ and for the outdoor temperature, at most once an hour.
"""
from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .engine import review

REVIEW_DAYS = 365
REVIEW_REFRESH = timedelta(hours=1)
DATA_REVIEW = f"{DOMAIN}_review"
DATA_PERIODS = f"{DOMAIN}_periods"
# The home card's periods: a month of hourly means, and a week before it for the running mean outdoors.
PERIODS_DAYS = 37
MEASURES = {"temperature": "indoor_temperature", "humidity": "indoor_humidity", "co2": "co2"}


def _rooms(hass):
    return sorted((e for e in hass.config_entries.async_entries(DOMAIN)
                   if e.state is ConfigEntryState.LOADED and not e.data.get("home") and getattr(e, "runtime_data", None)),
                  key=lambda e: e.title)


async def _statistics(hass, entity_ids, start, end):
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period
    # Temperatures in °C whatever the sensor's unit: the standard's ranges are in °C.
    return await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, set(entity_ids), "hour", {"temperature": "°C"}, {"mean"})


def _points(rows):
    return [(dt_util.utc_from_timestamp(row["start"]), row["mean"]) for row in rows or ()
            if isinstance(row.get("mean"), (int, float)) and isinstance(row.get("start"), (int, float))]


async def async_review(hass, now=None):
    """The home's review: every loaded room and the whole; kept an hour, the statistics changing only hourly."""
    now = now or dt_util.utcnow()
    cached = hass.data.get(DATA_REVIEW)
    if cached and now - cached[0] < REVIEW_REFRESH:
        return cached[1]
    entries = _rooms(hass)
    # Each room's own sensors: a room sharing another's air does not grade that air a second time.
    wanted = {e.entry_id: {k: e.runtime_data.config.get("sources", {}).get(source) for k, source in MEASURES.items()} for e in entries}
    outdoor = next((e.runtime_data._outdoor_entity() for e in entries if e.runtime_data._outdoor_entity()), None)
    ids = {i for sources in wanted.values() for i in sources.values() if i} | ({outdoor} if outdoor else set())
    start = now - timedelta(days=REVIEW_DAYS)
    stats = await _statistics(hass, ids, start, now) if ids else {}
    zone = dt_util.get_default_time_zone()
    outside = _points(stats.get(outdoor)) if outdoor else []

    def build():
        rooms = []
        for entry in entries:
            series = {k: _points(stats.get(i)) for k, i in wanted[entry.entry_id].items() if i}
            config = entry.runtime_data.config
            graded = review.room(series, outside, zone, config.get("heated", True) is not False)
            # A room with a ventilation of its own is told to run it longer rather than to open.
            ventilation = bool(config.get("sources", {}).get("ventilation"))
            rooms.append({"entry_id": entry.entry_id, "title": entry.title, **graded, "advice": review.advice(graded, ventilation)})
        return rooms

    rooms = await hass.async_add_executor_job(build)
    result = {"version": 1, "computed_at": now.isoformat(), "start": start.isoformat(), "outdoor": bool(outside),
              "home": {**review.home(rooms), "advice": review.home_advice(rooms)}, "rooms": rooms}
    hass.data[DATA_REVIEW] = (now, result)
    return result


async def async_periods(hass, now=None):
    """The home card's last day, week and month (engine/review.period); kept an hour like the review."""
    now = now or dt_util.utcnow()
    cached = hass.data.get(DATA_PERIODS)
    if cached and now - cached[0] < REVIEW_REFRESH:
        return cached[1]
    entries = _rooms(hass)
    wanted = {e.entry_id: {k: e.runtime_data.config.get("sources", {}).get(source) for k, source in MEASURES.items()} for e in entries}
    outdoor = next((e.runtime_data._outdoor_entity() for e in entries if e.runtime_data._outdoor_entity()), None)
    ids = {i for sources in wanted.values() for i in sources.values() if i} | ({outdoor} if outdoor else set())
    stats = await _statistics(hass, ids, now - timedelta(days=PERIODS_DAYS), now) if ids else {}
    zone = dt_util.get_default_time_zone()
    outside = _points(stats.get(outdoor)) if outdoor else []
    rooms = [{"entry_id": e.entry_id, "title": e.title, "heated": e.runtime_data.config.get("heated", True) is not False,
              "series": {k: _points(stats.get(i)) for k, i in wanted[e.entry_id].items() if i}} for e in entries]

    def build():
        return {name: review.period(rooms, outside, now, name, zone) for name in review.PERIODS}

    result = {"version": 1, "computed_at": now.isoformat(), **await hass.async_add_executor_job(build)}
    hass.data[DATA_PERIODS] = (now, result)
    return result
