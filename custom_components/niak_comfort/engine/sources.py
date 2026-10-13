"""Normalize explicitly selected observations without numeric fallbacks."""
from dataclasses import dataclass
from datetime import datetime
import math

WIND_TO_KMH = {"km/h": 1.0, "m/s": 3.6, "mph": 1.609344, "kn": 1.852, "ft/s": 1.09728}


@dataclass(frozen=True)
class Reading:
    value: float | bool | str | None
    quality: str
    source: str | None = None
    received_at: str | None = None
    detail: str | None = None
    unit: str | None = None

    @property
    def usable(self) -> bool:
        return self.quality == "valid" and self.value is not None


def normalize(kind: str, value: object, unit: str | None = None, *,
              source: str | None = None, reported_at: datetime | None = None,
              now: datetime, max_age: float = 1800) -> Reading:
    stamp = reported_at.isoformat() if reported_at else None
    def invalid(detail: str, quality: str = "unknown") -> Reading:
        return Reading(None, quality, source, stamp, detail)
    if not source:
        return invalid("not_configured")
    if value is None or str(value).lower() in ("unknown", "unavailable", "none", ""):
        return invalid("unavailable")
    if reported_at is None or reported_at.tzinfo is None or now.tzinfo is None:
        return invalid("missing_timestamp")
    age = (now - reported_at).total_seconds()
    if age < -60:
        return invalid("future_timestamp")
    if age > max_age:
        return invalid("expired", "stale")
    if kind in ("window", "rain", "pollution"):
        if isinstance(value, bool):
            result = value
        elif str(value).lower() in ("on", "off"):
            result = str(value).lower() == "on"
        else:
            return invalid("invalid_boolean")
    elif kind == "heating":
        if value not in ("heating", "idle", "off", "cooling"):
            return invalid("unknown_action")
        result = str(value)
    else:
        if isinstance(value, bool):
            return invalid("invalid_number")
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            return invalid("invalid_number")
        if not math.isfinite(result):
            return invalid("non_finite")
        if kind == "temperature":
            if unit == "°F":
                result = (result - 32) * 5 / 9
            elif unit == "K":
                result -= 273.15
            elif unit != "°C":
                return invalid("incompatible_unit")
            bounds = (-80, 80)
        elif kind == "humidity" and unit == "%":
            bounds = (0, 100)
        elif kind == "co2" and unit == "ppm":
            bounds = (0, 100000)
        elif kind == "wind" and unit in WIND_TO_KMH:
            result *= WIND_TO_KMH[unit]
            bounds = (0, 500)
        elif kind == "irradiance" and unit == "W/m²":
            bounds = (0, 2000)
        elif kind == "bearing" and unit == "°":
            bounds = (0, 360)
        else:
            return invalid("incompatible_unit")
        if not bounds[0] <= result <= bounds[1]:
            return invalid("out_of_range")
    canonical_unit = {"temperature": "°C", "humidity": "%", "co2": "ppm", "wind": "km/h", "irradiance": "W/m²", "bearing": "°"}.get(kind)
    return Reading(result, "valid", source, stamp, unit=canonical_unit)
