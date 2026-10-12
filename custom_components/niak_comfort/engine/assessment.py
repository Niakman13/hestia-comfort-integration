"""Zone-local needs, opportunities and constraints, independently of commands.

Threshold defaults replay historical settings; they are not health standards.
"""
from dataclasses import asdict, dataclass
import math
from typing import Mapping

from .sources import Reading

LEVELS = ("calm", "benefit", "action", "urgent", "neutral")
ACTIONS = ("ok", "ouvrir", "fermer", "attendre", "unknown")


@dataclass(frozen=True)
class Settings:
    minimum: float = 20
    maximum: float = 24
    humidity_high: float = 62
    co2_potential: float = 1000
    co2_action: float = 1200
    co2_urgent: float = 1600
    temperature_hysteresis: float = 0.5
    co2_hysteresis: float = 100
    humidity_hysteresis: float = 3
    cooling_delta: float = 1.5
    drying_delta: float = 1.5
    max_age_seconds: float = 1800

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in asdict(self).values()):
            raise ValueError("finite_settings_required")
        if not (5 <= self.minimum < self.maximum <= 40):
            raise ValueError("invalid_temperature_range")
        if not (0 <= self.co2_potential < self.co2_action < self.co2_urgent <= 100000):
            raise ValueError("invalid_co2_thresholds")
        if not (0 < self.humidity_high <= 100):
            raise ValueError("invalid_humidity_threshold")
        if not (0 <= self.temperature_hysteresis < (self.maximum - self.minimum) / 2):
            raise ValueError("invalid_temperature_hysteresis")
        if not (0 <= self.co2_hysteresis < self.co2_action - self.co2_potential):
            raise ValueError("invalid_co2_hysteresis")
        if not (0 <= self.humidity_hysteresis < self.humidity_high):
            raise ValueError("invalid_humidity_hysteresis")
        if self.cooling_delta <= 0 or self.drying_delta <= 0 or self.max_age_seconds <= 0:
            raise ValueError("positive_settings_required")


@dataclass(frozen=True)
class Assessment:
    action: str
    level: str
    reason: str
    needs: tuple[str, ...]
    constraints: tuple[str, ...]
    opportunities: tuple[str, ...]
    partial: bool
    missing: tuple[str, ...]
    heating_action: str
    indoor_absolute_humidity: float | None
    outdoor_absolute_humidity: float | None
    temperature_delta: float | None
    coordination: str = "not_connected"

    def to_dict(self) -> dict:
        return asdict(self)


def absolute_humidity(t: float | None, rh: float | None) -> float | None:
    if t is None or rh is None:
        return None
    return 6.112 * math.exp(17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)


def assess(readings: Mapping[str, Reading], settings: Settings = Settings(),
           previous: Assessment | None = None) -> Assessment:
    def value(key: str):
        reading = readings.get(key)
        return reading.value if reading and reading.usable else None
    ti, te = value("indoor_temperature"), value("outdoor_temperature")
    hi, he, co2 = value("indoor_humidity"), value("outdoor_humidity"), value("co2")
    contacts = [r for k, r in readings.items() if k.startswith("window:")]
    opened = any(r.usable and r.value is True for r in contacts)
    closed = bool(contacts) and all(r.usable and r.value is False for r in contacts)
    rain, pollution = value("rain"), value("pollution")
    daily_air = readings.get("pollution")
    if daily_air and daily_air.quality == "estimated" and daily_air.value is True:
        pollution = True  # Configured daily precaution can block; it never clears an opening.
    old = previous.needs if previous else ()
    hot = ti is not None and ti > settings.maximum - (settings.temperature_hysteresis if "cool" in old else 0)
    cold = ti is not None and ti < settings.minimum + (settings.temperature_hysteresis if "heat" in old else 0)
    air = co2 is not None and co2 >= settings.co2_action - (settings.co2_hysteresis if "air" in old else 0)
    wet = hi is not None and hi > settings.humidity_high - (settings.humidity_hysteresis if "dry" in old else 0)
    needs = tuple(k for k, active in (("air", air), ("cool", hot), ("heat", cold), ("dry", wet)) if active)
    ai, ae = absolute_humidity(ti, hi), absolute_humidity(te, he)
    delta = te - ti if te is not None and ti is not None else None
    cool = delta is not None and delta <= -settings.cooling_delta
    dry = ai is not None and ae is not None and ai - ae >= settings.drying_delta
    constraints = tuple(k for k, active in (("rain", rain is True), ("pollution", pollution is True)) if active)
    # An unconfigured protection is not proof that opening is safe.
    checked = rain is False and pollution is False
    thermal_known = ti is not None and te is not None
    optional_wet_exchange = ai is not None and ae is not None and ae > ai + 1
    useful = air or (hot and cool and not optional_wet_exchange) or (wet and dry and not cold)
    opportunities = tuple(k for k, active in (("cool", cool and not optional_wet_exchange), ("dry", dry),
        ("air", co2 is not None and co2 >= settings.co2_potential)) if active) if not constraints else ()
    missing = tuple(sorted({k for k, r in readings.items() if r.source and not r.usable}
                           | {k for k in ("indoor_temperature", "outdoor_temperature", "rain", "pollution") if value(k) is None}))
    partial = bool(missing)
    level = "urgent" if (co2 is not None and co2 >= settings.co2_urgent) or (rain is True and opened) else "action" if needs else "neutral" if partial else "calm"
    action, reason = "ok", "within_comfort"
    if rain is True and opened:
        action, reason = "fermer", "rain_open_windows"
    elif constraints:
        action, reason = ("fermer" if opened else "attendre"), "opening_blocked"
        if level in ("calm", "neutral"):
            # A constraint alone, with known closed windows and no need, is not an action need.
            level = "calm" if closed and not partial else "neutral"
    elif useful:
        if not checked or not thermal_known:
            action, reason = "unknown", "verify_exterior"
        else:
            action, reason = ("ok" if opened else "ouvrir"), "air_needed" if air else "cooling_possible" if hot else "drying_possible"
    elif opened and delta is not None and ((ti >= (settings.minimum + settings.maximum) / 2 and delta > 0.5)
                                          or (ti <= settings.minimum + 1 and delta < -0.5)):
        action, reason = "fermer", "exchange_harmful"
        level = "action"
    elif hot:
        action, reason = "attendre", "cooling_unavailable"
    elif cold:
        action, reason = ("fermer" if opened else "ok"), "heat_needed"
    elif wet:
        action, reason = "attendre", "drying_unavailable"
    elif partial:
        action, reason = "unknown", "incomplete_data"
    elif opportunities and not opened and co2 is not None and co2 >= settings.co2_potential:
        level, reason = "benefit", "optional_air_change"
    heating = (value("heating") or "unknown") if "heating" in readings else "not_configured"
    return Assessment(action, level, reason, needs, constraints, opportunities, partial, missing,
                      heating, ai, ae, delta)
