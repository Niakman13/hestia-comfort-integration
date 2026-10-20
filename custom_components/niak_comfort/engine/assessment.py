"""Zone-local needs, opportunities and constraints, independently of commands.

Threshold defaults replay historical settings; they are not health standards.
"""
from dataclasses import asdict, dataclass, field, replace
import math
from datetime import datetime
from typing import Mapping

from .sources import Reading
from .wind import DRIVEN_RAIN_GUST, crossing as wind_crossing, open_first, side as wind_side
from .outlook import IMMINENT, rain_timing, slot as next_slot
from . import learning

# Points above the humidity threshold that call for a gesture at once; below, only a lasting excess does.
HUMIDITY_GRACE = 5
# Water (g/m³) the room must hold above the outdoor air for its humidity to come from inside: below it,
# the humidity is the weather's, and no airing can lower it.
INDOOR_SOURCE = 0.5
# The coldest spot of an outer wall (a corner, a thermal bridge) sits at 70 % of the way from outdoors to
# indoors (EN ISO 13788's fRsi criterion); mould grows where the air touching it stays above 80 %.
WALL_FACTOR = 0.7
MOULD_RH, MOULD_FAST, MOULD_HYSTERESIS = 80.0, 85.0, 3.0
# Reasons that only say « do not open »: with nothing open, they bring nothing and stay off the banner.
QUIET_REASONS = ("humid_outdoor", "drying_unavailable", "drying_slow", "opening_blocked", "heat_needed", "cooling_unavailable", "precool_later")
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
    # Many sensors only send a value when it changes: three hours of silence is still a valid reading.
    max_age_seconds: float = 10800
    gust_max: float = 45
    frost: float = 1.0
    sun_facade: float = 250
    pm25_action: float = 25
    illuminance_low: float = 100
    # Upper comfort limit once summer has settled in; `maximum` stays the winter limit.
    summer_maximum: float = 26

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
        if min(self.cooling_delta, self.drying_delta, self.max_age_seconds, self.gust_max, self.sun_facade, self.pm25_action, self.illuminance_low) <= 0:
            raise ValueError("positive_settings_required")
        if not -30 <= self.frost <= 15:
            raise ValueError("invalid_frost_threshold")
        if not self.minimum < self.summer_maximum <= 40:
            raise ValueError("invalid_summer_maximum")


# Seven-day mean outdoor temperature between which the comfort limit moves from winter to summer.
SEASON_FROM, SEASON_TO = 12.0, 20.0


def seasonal(settings: "Settings", outdoor_mean: float | None) -> tuple["Settings", dict]:
    """Comfort range for the season: the upper limit follows the recent outdoor mean, smoothly.

    Without a known mean the saved range is kept untouched; nothing is guessed from the calendar.
    """
    summer = max(settings.summer_maximum, settings.maximum)
    if outdoor_mean is None or not math.isfinite(outdoor_mean):
        return settings, {"known": False, "weight": None, "outdoor_mean": None,
                          "minimum": settings.minimum, "maximum": settings.maximum}
    weight = min(1.0, max(0.0, (outdoor_mean - SEASON_FROM) / (SEASON_TO - SEASON_FROM)))
    maximum = round(settings.maximum + weight * (summer - settings.maximum), 1)
    return replace(settings, maximum=maximum), {"known": True, "weight": round(weight, 2),
                                                "outdoor_mean": round(outdoor_mean, 1),
                                                "minimum": settings.minimum, "maximum": maximum}


@dataclass(frozen=True)
class Opening:
    """What the user declared about one opening; nothing is guessed from its name."""
    exposure: str | None = None
    kind: str = "window"
    sheltered: bool = False
    shutter: str = "none"
    cover_entity: str | None = None
    auto_entity: str | None = None
    override_entity: str | None = None
    # The integration that drives the cover with the sun (« adaptive_cover_pro »), when one is recognised.
    driver: str | None = None
    # The window's exact bearing in degrees, when the cover's driver knows it (Adaptive Cover Pro).
    azimuth: float | None = None
    width: float | None = None
    height: float | None = None
    overhang_depth: float | None = None
    overhang_gap: float | None = None


@dataclass(frozen=True)
class Sun:
    elevation: float
    azimuth: float


EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
KINDS = ("window", "french", "skylight", "door")
SHELTER_ATTENUATION = 3.0  # Template casquette_att: a roof overhang divides direct sun.


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
    openings: tuple[dict, ...] = ()
    sun: dict | None = None
    unverified: tuple[str, ...] = ()
    wind_bearing: float | None = None
    crossing: str | None = None
    open_first: tuple[str, ...] = ()
    slot: dict | None = None
    rain_soon_minutes: int | None = None
    features: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def absolute_humidity(t: float | None, rh: float | None) -> float | None:
    if t is None or rh is None:
        return None
    return 6.112 * math.exp(17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)


def facade_share(exposure: str | None, sun: Sun | None, azimuth: float | None = None) -> float:
    """Share of the sun facing a facade, as in the template: cos(elevation)·cos(azimuth gap).
    An exact bearing, when known, replaces the eight-point exposure."""
    facing = azimuth if azimuth is not None else EXPOSURES.get(exposure)
    if facing is None or sun is None or sun.elevation <= 0:
        return 0.0
    gap = ((sun.azimuth - facing + 540) % 360) - 180
    return max(math.cos(math.radians(sun.elevation)) * math.cos(math.radians(gap)), 0.0)


def facade_irradiance(share: float, sun: Sun | None, solar: float | None) -> float | None:
    """W/m² on a vertical facade from the measured horizontal irradiance; never invented."""
    if solar is None or sun is None:
        return None
    diffuse = solar * 0.15
    direct = 0.0
    if sun.elevation > 5 and solar > 40:
        direct = min(solar / max(math.sin(math.radians(sun.elevation)), 0.09) * share, 850)
    return round(max(direct, diffuse))


def assess(readings: Mapping[str, Reading], settings: Settings = Settings(),
           previous: Assessment | None = None, openings: Mapping[str, Opening] | None = None,
           sun: Sun | None = None, outlook: Mapping | None = None, now: datetime | None = None,
           context: Mapping | None = None) -> Assessment:
    def value(key: str):
        reading = readings.get(key)
        return reading.value if reading and reading.usable else None
    openings = openings or {}
    outlook = outlook or {}
    context = context or {}
    # The upper comfort limit follows the season; a room declared unheated never calls for warmth.
    settings, season = seasonal(settings, context.get("outdoor_mean_7d"))
    heated = context.get("heated", True) is not False
    ti, te = value("indoor_temperature"), value("outdoor_temperature")
    hi, he, co2 = value("indoor_humidity"), value("outdoor_humidity"), value("co2")
    gust, solar, bearing = value("wind_gust"), value("solar"), value("wind_bearing")
    contacts = {k[7:]: r for k, r in readings.items() if k.startswith("window:")}
    opened = any(r.usable and r.value is True for r in contacts.values())
    closed = bool(contacts) and all(r.usable and r.value is False for r in contacts.values())
    # Rain only concerns openings that are not sheltered, or sheltered but hit by a wind that pushes it in.
    def rained_on(e):
        meta = openings.get(e, Opening())
        driven = wind_side(meta.exposure, bearing) == "windward" and gust is not None and gust >= DRIVEN_RAIN_GUST
        return not meta.sheltered or driven
    exposed = [e for e in contacts if rained_on(e)]
    all_sheltered = bool(contacts) and not exposed
    rain = False if all_sheltered else value("rain")
    pollution = value("pollution")
    daily_air = readings.get("pollution")
    if daily_air and daily_air.quality == "estimated" and daily_air.value is not None:
        # The daily index the person chose as precaution: above their threshold it blocks,
        # below it the precaution is checked, like an unconfigured one would not block.
        pollution = daily_air.value
    from .evolution import air_features, features, _shade
    air_detail = air_features(readings, settings, context)
    old = previous.needs if previous else ()
    hot = ti is not None and ti > settings.maximum - (settings.temperature_hysteresis if "cool" in old else 0)
    cold = heated and ti is not None and ti < settings.minimum + (settings.temperature_hysteresis if "heat" in old else 0)
    previous_co2 = previous.features.get("air", {}).get("co2_status") if previous else None
    co2_was_high = previous_co2 == "high" if previous_co2 is not None else "air" in old
    co2_air = co2 is not None and co2 >= settings.co2_action - (settings.co2_hysteresis if co2_was_high else 0)
    air_detail["co2_status"] = ("not_configured" if "co2" not in readings else "unknown" if co2 is None
                               else "high" if co2_air else "ok")
    air = co2_air or (air_detail["pm25_status"] == "high" and not air_detail["pm25_treated"]) or air_detail["voc_status"] == "high"
    # A little above the threshold for an afternoon bothers nobody: humidity calls for a gesture when it is
    # clearly high, or when it has stayed above the threshold for the last three hours.
    lasting = context.get("humidity_floor_3h")
    lasting = isinstance(lasting, (int, float)) and not isinstance(lasting, bool) and lasting > settings.humidity_high
    humid = hi is not None and (hi > settings.humidity_high - settings.humidity_hysteresis if "dry" in old
                                else hi > settings.humidity_high + HUMIDITY_GRACE or (hi > settings.humidity_high and lasting))
    ai, ae = absolute_humidity(ti, hi), absolute_humidity(te, he)
    # Mould: the relative humidity of the air against the coldest spot of the outer walls, not of the room.
    surface = None
    if ai is not None and te is not None and te < ti:
        surface = min(100.0, ai / absolute_humidity(te + WALL_FACTOR * (ti - te), 100) * 100)
    was_mould = bool(previous and (previous.features.get("humidity") or {}).get("mould"))
    mould = surface is not None and surface >= MOULD_RH - (MOULD_HYSTERESIS if was_mould else 0) and (lasting or surface >= MOULD_FAST)
    # Judged on what airing can gain: humidity that comes from inside (shower, cooking, sleep) calls for a gesture;
    # the weather's own humidity does not, however high. Without the outdoor humidity, as before.
    excess = ai - ae if ai is not None and ae is not None else None
    from_inside = excess is None or excess >= INDOOR_SOURCE - (0.3 if "dry" in old else 0)
    wet = (humid or mould) and from_inside
    humid_outdoor = (humid or mould) and not from_inside
    # Pre-cooling (template « prérefroidir »): at night, when tomorrow is announced well above the comfort range.
    tomorrow_max = outlook.get("tomorrow_max")
    night = sun is not None and sun.elevation < 0
    precool = (not hot and not cold and not wet and night and ti is not None and isinstance(tomorrow_max, (int, float))
               and tomorrow_max >= settings.maximum + 3 and ti > settings.minimum + 2)
    needs = tuple(k for k, active in (("air", air), ("cool", hot), ("heat", cold), ("dry", wet), ("precool", precool)) if active)
    delta = te - ti if te is not None and ti is not None else None
    cool = delta is not None and delta <= -settings.cooling_delta
    dry = ai is not None and ae is not None and ai - ae >= settings.drying_delta
    # What airing would really bring here, learned from the room's past openings (an ordinary room before
    # that), instead of a full replacement of its air by the outdoor one.
    drying = None
    if wet and dry and ti is not None:
        model = context.get("drying_model")
        model = model if isinstance(model, Mapping) and all(isinstance(model.get(k), (int, float)) for k in ("tau", "residual", "rebound")) else {**learning.DEFAULT, "openings": 0}
        drying = {**learning.outcome(model, ti, ai, ae), "tau": model["tau"], "openings": model.get("openings", 0),
                  "later": learning.best_moment(model, ti, ai, ae, outlook.get("hours"), now) if now and not opened else None}
    # Once open, the airing runs its course; before, it must be worth it.
    worth = drying is not None and (opened or drying["gain"] >= learning.MIN_GAIN)
    windy = gust is not None and gust > settings.gust_max
    frost = te is not None and te <= settings.frost
    heating_running = value("heating") == "heating"

    details = []
    for entity_id, reading in contacts.items():
        meta = openings.get(entity_id, Opening())
        is_open = reading.usable and reading.value is True
        share = facade_share(meta.exposure, sun, meta.azimuth)
        watts = facade_irradiance(share, sun, solar)
        shade, shade_model = _shade(meta, sun)
        if watts is not None and shade_model == "geometry":
            watts = round(watts * (1 - shade))
        elif watts is not None and meta.sheltered:
            watts = round(watts / SHELTER_ATTENUATION)
        flags = []
        facing = wind_side(meta.exposure, bearing)
        if is_open and rain is True and rained_on(entity_id):
            flags.append("rain_exposed")
        if is_open and windy:
            flags.append("gust")
        if is_open and hot and watts is not None and watts >= settings.sun_facade:
            flags.append("sun_entering")
        details.append({"entity_id": entity_id, "open": is_open if reading.usable else None,
                        "exposure": meta.exposure, "kind": meta.kind, "sheltered": meta.sheltered,
                        "sun_share": round(share, 2), "sun_wm2": watts, "wind_side": facing, "flags": flags})
    exposed_open = any("rain_exposed" in d["flags"] for d in details)
    sunny_open = any("sun_entering" in d["flags"] for d in details)

    # Template veto order: rain, gusts, outdoor air, frost, heating. Frost and a running
    # heating only soften the advice: a confirmed air need still gets a short airing.
    storm = outlook.get("storm") is True
    vigilance = (outlook.get("vigilance") or 0) >= 2  # orange or red, from Niak Weather
    # One rain for the whole home, the same for « open » and for « close »: the station says whether it rains,
    # the radar when it starts. Only a rain due shortly shuts the exposed openings and keeps them shut: within
    # twenty minutes when known to the minute, within the hour when only the hourly forecast says it and nothing
    # measures the rain here. A later rain only bounds the airing.
    soon, precise = rain_timing(outlook.get("rain"), outlook.get("rain_in_hours")) if rain is not True else (None, False)
    rain_measured = "rain" in readings and readings["rain"].usable
    imminent = (soon is not None and not all_sheltered
                and (soon <= IMMINENT if precise else not rain_measured and soon <= 60))
    # The storm and the orange vigilance are forecasts. When Niak Weather's own station measures the rain
    # and the gusts here, it has the last word: dry, calm and no rain within the hour, they only shorten
    # the airing. Without such a station, or with a red vigilance, the forecast still keeps everything shut.
    station = outlook.get("station") or ()
    measured = ("rain_rate" in station and "wind_gust" in station and value("rain") is False
                and gust is not None and not windy and not imminent)
    forecast_only = measured and (outlook.get("vigilance") or 0) < 3
    constraints = tuple(k for k, active in (("rain", rain is True), ("rain_soon", imminent), ("storm", storm), ("vigilance", vigilance), ("gust", windy),
                                            ("pollution", pollution is True), ("frost", frost), ("heating_running", heating_running)) if active)
    hard = [c for c in constraints if c in ("rain", "rain_soon", "gust", "pollution") or (c in ("storm", "vigilance") and not forecast_only)]
    rain_coming = imminent and any(d["open"] and rained_on(d["entity_id"]) for d in details)
    soft = [c for c in constraints if c in ("frost", "heating_running") or (c in ("storm", "vigilance") and forecast_only)]
    # A configured protection that does not answer blocks the advice; one never configured does not.
    # Rain still guards an opening when its sensor stops answering. A daily outdoor-air index that is
    # down (Atmo France outage) behaves like one never configured: the advice stands, the gap is reported.
    checked = (rain is False or ("rain" not in readings and rain is None)) and pollution is not True
    thermal_known = ti is not None and te is not None
    optional_wet_exchange = ai is not None and ae is not None and ae > ai + 1
    useful = air or ((hot or precool) and cool and not optional_wet_exchange) or (wet and worth and not cold)
    opportunities = tuple(k for k, active in (("cool", cool and not optional_wet_exchange), ("dry", dry),
        ("air", co2 is not None and co2 >= settings.co2_potential)) if active) if not hard and not soft else ()
    missing = tuple(sorted(k for k in ({k for k, r in readings.items() if r.source and not r.usable
                                        and not (k == "pollution" and r.quality == "estimated" and r.value is not None)}
                                       | {k for k in ("indoor_temperature", "outdoor_temperature") if value(k) is None})
                           if not (k == "rain" and all_sheltered)))
    partial = bool(set(missing) - {"pollution"})
    urgent = (co2 is not None and co2 >= settings.co2_urgent) or exposed_open or (windy and opened)
    # Pre-cooling is an opportunity for tomorrow, not a problem now.
    level = "urgent" if urgent else "action" if set(needs) - {"precool"} else "benefit" if needs else "neutral" if partial else "calm"
    action, reason = "ok", "within_comfort"
    if exposed_open:
        action, reason = "fermer", "rain_open_windows"
    elif windy and opened:
        action, reason = "fermer", "gust_open_windows"
    elif opened and ("storm" in hard or "vigilance" in hard):
        action, reason, level = "fermer", "opening_blocked", "urgent" if storm else "action"
    elif rain_coming:
        action, reason, level = "fermer", "rain_soon", "action"
    elif hard:
        # Only outdoor air reaches every opening; rain spares sheltered ones, gusts are handled above.
        action, reason = ("fermer" if opened and pollution is True else "attendre"), "opening_blocked"
        if level in ("calm", "neutral"):
            # A constraint alone, with known closed windows and no need, is not an action need.
            level = "calm" if closed and not partial else "neutral"
    elif soft and air:
        action, reason = ("ok" if opened else "ouvrir"), "short_air_change"
    elif soft and opened:
        action, reason, level = "fermer", "opening_blocked", "action"
    elif soft and (hot or wet or precool):
        action, reason = "attendre", "opening_blocked"
    elif useful:
        if not checked or not thermal_known:
            action, reason = "unknown", "verify_exterior"
        else:
            action, reason = ("ok" if opened else "ouvrir"), ("air_needed" if air else "cooling_possible" if hot
                                                             else "precool_possible" if precool else "drying_possible")
    elif opened and delta is not None and ((ti >= (settings.minimum + settings.maximum) / 2 and delta > 0.5)
                                          or (heated and ti <= settings.minimum + 1 and delta < -0.5)):
        action, reason = "fermer", "exchange_harmful"
        level = "action"
    elif hot and sunny_open:
        action, reason, level = "fermer", "sun_entering", "action"
    elif hot:
        action, reason = "attendre", "cooling_unavailable"
    elif cold:
        action, reason = ("fermer" if opened else "ok"), "heat_needed"
    elif wet and drying and drying["later"]:
        action, reason = "attendre", "drying_later"
    elif wet and drying:
        action, reason = "attendre", "drying_slow"
    elif wet:
        action, reason = "attendre", "drying_unavailable"
    elif humid_outdoor:
        action, reason = "ok", "humid_outdoor"
    elif precool:
        action, reason = "attendre", "precool_later"
    elif partial:
        action, reason = "unknown", "incomplete_data"
    elif opportunities and not opened and co2 is not None and co2 >= settings.co2_potential:
        level, reason = "benefit", "optional_air_change"
    if (opened and optional_wet_exchange and not air and not hard and not soft
            and action != "fermer" and not rain_coming):
        action, reason, level = "fermer", "rehumidification_risk", "action"
    heating = (value("heating") or "unknown") if "heating" in readings else "not_configured"
    first = tuple(open_first(details)) if action == "ouvrir" else ()
    coming = next_slot(outlook.get("hours") or [], now, ti, hot=hot or precool, cool_now=cool, margin=settings.cooling_delta) if now else None
    # A banner speaks only when it brings something: a gesture now, a gesture to undo, a likely wrong reflex
    # (opening when it is hotter outside), a precise later time, or another remedy such as the ventilation.
    # The ventilation brings outdoor air too: it helps where the outdoor air is drier but the window renews little.
    if reason == "drying_slow" and (air_detail.get("ventilation") or {}).get("on") is False:
        reason = "ventilation_possible"
    elif reason == "drying_later" or (reason in ("cooling_unavailable", "precool_later") and coming and coming["kind"] == "open"):
        level = "benefit"
    elif (reason in QUIET_REASONS and action != "fermer" and level != "urgent"
          and not (reason == "cooling_unavailable" and delta is not None and delta > 0)
          # Stale air or a hot room make people open by reflex: warning them off is still useful.
          and not (reason == "opening_blocked" and ("air" in needs or ("cool" in needs and cool)))):
        level = "neutral" if partial or level == "neutral" else "calm"
    # Protections never configured: the advice stands, the card says what Niak does not watch.
    unverified = tuple(k for k in ("pollution", "rain") if k not in readings and not (k == "rain" and all_sheltered))
    extended = features(readings, settings, context, openings, sun, details,
                        needs, action, reason, now, ai, ae, air_detail)
    extended["season"] = {**season, "heated": heated}
    extended["drying"] = drying
    if isinstance(extended.get("humidity"), dict):
        saturated = absolute_humidity(ti, 100) if ti is not None else None
        extended["humidity"].update(
            surface=None if surface is None else round(surface), mould=mould,
            excess=None if excess is None else round(excess, 1), source="inside" if wet else "outside" if humid_outdoor else None,
            # Where a full airing would bring the room at best: the outdoor water, warmed to the room's temperature.
            reachable=None if ae is None or not saturated else round(min(100.0, ae / saturated * 100)))
    if reason == "drying_possible" and drying:
        extended["ventilation"]["duration_minutes"] = {"min": max(5, 5 * round(drying["minutes"] * .75 / 5)), "max": drying["minutes"]}
    # A later rain bounds the airing: the window is shut five minutes before it.
    extended["rain_ahead"] = {"minutes": soon, "precise": precise} if soon is not None else None
    if soon is not None and action == "ouvrir" and soon > IMMINENT:
        span = extended["ventilation"].get("duration_minutes")
        if isinstance(span, dict) and span.get("max", 0) > soon - 5:
            extended["ventilation"]["duration_minutes"] = {"min": min(span["min"], soon - 5), "max": soon - 5}
    # The last 24 hours of the room, widened by the current reading (statistics stop at the last full hour).
    day = context.get("indoor_day_range")
    if (isinstance(day, Mapping) and all(isinstance(day.get(k), (int, float)) and not isinstance(day.get(k), bool) and math.isfinite(day[k]) for k in ("min", "max"))
            and day["min"] <= day["max"]):
        low, high = (min(day["min"], ti), max(day["max"], ti)) if ti is not None else (day["min"], day["max"])
        extended["day_range"] = {"min": round(low, 1), "max": round(high, 1)}
    else:
        extended["day_range"] = None
    # A solar protection opportunity does not change the contact action. Existing
    # room needs and safety reasons retain their original priority.
    if (not constraints and reason == "within_comfort" and level == "calm"
            and any(s["advice"] for s in extended["shutters"])):
        level, reason = "benefit", "shutter_protection"
    return Assessment(action, level, reason, needs, constraints, opportunities, partial, missing,
                      heating, ai, ae, delta, openings=tuple(details), unverified=unverified, wind_bearing=bearing,
                      crossing=wind_crossing(details), open_first=first, slot=coming, rain_soon_minutes=soon,
                      sun={"elevation": round(sun.elevation, 1), "azimuth": round(sun.azimuth, 1)} if sun else None,
                      features=extended)
