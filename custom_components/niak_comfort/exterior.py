"""Normalize supported exterior sources without equating daily outlooks to observations."""
from dataclasses import replace
import math
from homeassistant.util import dt as dt_util
from .const import SOURCES
from .engine.sources import normalize, Reading


def exterior_reading(state, key, spec, *, now, max_age):
    entity_id = spec["entity_id"]
    if not state:
        return Reading(None, "unknown", source=entity_id, detail="unavailable")
    adapter = spec.get("adapter", "direct")
    if adapter == "direct" or adapter == "binary":
        kind = SOURCES.get(key, key)
        return normalize(kind, state.state, state.attributes.get("unit_of_measurement"), source=entity_id,
                         reported_at=state.last_reported, now=now, max_age=max_age)
    if adapter == "rain_rate":
        unit = state.attributes.get("unit_of_measurement")
        try:
            rate = float(state.state)
            if not math.isfinite(rate) or rate < 0 or unit not in ("mm/h", "in/h"):
                raise ValueError
        except (TypeError, ValueError):
            return Reading(None, "unknown", source=entity_id, detail="invalid_rain_rate")
        reading = normalize("rain", rate > 0, source=entity_id, reported_at=state.last_reported, now=now, max_age=max_age)
        return replace(reading, detail="rain_rate_observed")
    if adapter == "atmo_daily":
        label = state.attributes.get("Libellé")
        labels = ("Bon", "Moyen", "Dégradé", "Mauvais", "Très mauvais", "Extrêmement mauvais")
        stamp = state.attributes.get("Date de mise à jour")
        reported = dt_util.parse_datetime(stamp) if isinstance(stamp, str) else None
        if not reported or not reported.tzinfo or label not in labels:
            return Reading(None, "unknown", source=entity_id, detail="invalid_atmo_index")
        if reported > now or dt_util.as_local(reported).date() != dt_util.as_local(now).date():
            return Reading(None, "stale", source=entity_id, received_at=reported.isoformat(), detail="expired")
        # A daily regional forecast can flag a configured precaution, but never prove
        # that the air at these windows is currently suitable for ventilation.
        return Reading(labels.index(label)+1 >= spec.get("block_from", 4), "estimated",
                       source=entity_id, received_at=reported.isoformat(), detail="atmo_daily_forecast")
    if adapter == "niak_index":
        try:
            index = float(state.state)
        except (TypeError, ValueError):
            return Reading(None, "unknown", source=entity_id, detail="invalid_air_index")
        if not 1 <= index <= 6:
            return Reading(None, "unknown", source=entity_id, detail="invalid_air_index")
        # Like ATMO: a regional daily index can flag the precaution, never prove the air is good now.
        return Reading(index >= spec.get("block_from", 4), "estimated", source=entity_id,
                       received_at=state.last_reported.isoformat(), detail="atmo_daily_forecast")
    return Reading(None, "unknown", source=entity_id, detail="unsupported_adapter")
