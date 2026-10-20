"""The room's twin: a few numbers, learned from its own measures, that say how it follows the weather.

Every half hour of the past is one sample: the indoor temperature and water content, the outdoor ones,
the sun on the station, how long a window stood open and how long the heating ran. Two small models are
fitted on them, pulled toward an ordinary room while little is known:

- temperature: ΔTi = a·(Te−Ti) + b·sun + c·heating + d·open·(Te−Ti) + e
- water:       ΔW  = n·(We−W) + m·open·(We−W) + g

`a` gives the room's inertia, `b` what the sun brings, `d` what an open window adds, `e` the steady
gains of the household, `n` the air that leaks in with every window shut, `g` the water the room makes.
The twin only observes: nothing here decides an advice.
"""
from bisect import bisect_right
from datetime import datetime, timedelta
import math

STEP = timedelta(minutes=30)
SUB = timedelta(minutes=5)
HOURS = STEP.total_seconds() / 3600
KEEP_DAYS = 30
# Before the twin speaks: three days of samples.
READY_SAMPLES = 144
# An ordinary room, the prior every fit is pulled toward while samples are few.
PRIOR_T = {"a": HOURS / 30, "b": 0.0, "c": 0.0, "d": 0.3, "e": 0.0}
PRIOR_W = {"n": HOURS / 3, "m": 0.3, "g": 0.0}
# Weight of the prior, in samples: one day of half hours.
PRIOR_STRENGTH = 48


def absolute(temperature, relative):
    """Water content of the air in g/m³ (Magnus formula)."""
    return 6.112 * math.exp(17.67 * temperature / (temperature + 243.5)) * relative * 2.1674 / (273.15 + temperature)


class _Series:
    """A sample-and-hold series: the value at a time is the last one reported before it."""
    def __init__(self, points, keep_none=False):
        # A contact that stops answering stays in its series as None: what the window did then is unknown.
        points = sorted(((t, v) for t, v in points if (v is not None or keep_none) and not (isinstance(v, float) and not math.isfinite(v))),
                        key=lambda p: p[0])
        self.times = [t for t, _ in points]
        self.values = [v for _, v in points]

    def at(self, when):
        i = bisect_right(self.times, when)
        return self.values[i - 1] if i else None


def sun_position(when, latitude, longitude):
    """Elevation and azimuth of the sun in degrees (NOAA's simplified formulas, within a degree)."""
    day = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600 - (when.utcoffset().total_seconds() / 3600 if when.utcoffset() else 0)
    gamma = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24)
    equation = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    declination = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma)
                   + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    angle = math.radians((hour * 60 + equation + 4 * longitude) / 4 - 180)
    lat = math.radians(latitude)
    cos_zenith = math.sin(lat) * math.sin(declination) + math.cos(lat) * math.cos(declination) * math.cos(angle)
    zenith = math.acos(max(-1.0, min(1.0, cos_zenith)))
    azimuth = math.degrees(math.atan2(math.sin(angle), math.cos(angle) * math.sin(lat) - math.tan(declination) * math.cos(lat))) + 180
    return 90 - math.degrees(zenith), azimuth % 360


def on_facades(solar, elevation, azimuth, facades):
    """W/m² on the room's windows from the horizontal irradiance of the station: the direct sun each facade faces, or the
    diffuse light; the mean over its windows. Without known facades, the station's own measure."""
    if not facades:
        return solar
    if solar <= 0:
        return 0.0
    out = []
    for facing in facades:
        gap = ((azimuth - facing + 540) % 360) - 180
        share = max(math.cos(math.radians(elevation)) * math.cos(math.radians(gap)), 0.0) if elevation > 0 else 0.0
        direct = min(solar / max(math.sin(math.radians(elevation)), 0.09) * share, 850) if elevation > 5 and solar > 40 else 0.0
        out.append(max(direct, solar * 0.15))
    return sum(out) / len(out)


def samples(start, end, indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity,
            solar=(), contacts=None, heating=(), facades=None, location=None, co2=(), voc=()):
    """Half-hour samples between `start` and `end` from raw (time, value) points.

    `facades`: the bearings of the room's windows and `location` (latitude, longitude): the sun is then counted on the
    windows, half hour by half hour, instead of on the station's horizontal sensor.

    `contacts`: {entity: [(time, bool|None)]}; `heating`: [(time, bool)] running or not. A half hour with
    a contact that does not answer is left out: what a window did then is not known."""
    ti, hi, te, he = (_Series(p) for p in (indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity))
    sun, heat, carbon, organic = _Series(solar), _Series(heating), _Series(co2), _Series(voc)
    windows = [_Series(points, keep_none=True) for points in (contacts or {}).values()]
    rows = []
    when = start.replace(minute=0 if start.minute < 30 else 30, second=0, microsecond=0)
    if when < start:
        when += STEP
    while when + STEP <= end:
        values = [ti.at(when), hi.at(when), te.at(when), he.at(when)]
        if None in values or not (0 < values[1] <= 100 and 0 < values[3] <= 100):
            when += STEP
            continue
        opened = heated = sunny = 0.0
        known, steps, t = True, 0, when
        while t < when + STEP:
            states = [w.at(t) for w in windows]
            if any(s is None for s in states):
                known = False
                break
            opened += any(states)
            heated += bool(heat.at(t))
            light = max(0.0, float(sun.at(t) or 0.0))
            if facades and location:
                elevation, azimuth = sun_position(t, *location)
                light = on_facades(light, elevation, azimuth, facades)
            sunny += light
            steps, t = steps + 1, t + SUB
        if known and steps:
            c, v = carbon.at(when), organic.at(when)
            rows.append([when.isoformat(), round(values[0], 2), round(values[1], 1), round(values[2], 2), round(values[3], 1),
                         round(sunny / steps / 1000, 3), round(opened / steps, 2), round(heated / steps, 2),
                         None if c is None else round(c), None if v is None else round(v)])
        when += STEP
    return rows


def merge(stored, fresh, now):
    """Stored samples plus the fresh ones (same time: the fresh one wins), the last thirty days only."""
    # Samples from before the air was learned carry no CO₂ nor VOC: unknown, not zero.
    by_time = {r[0]: (r + [None, None])[:10] for r in stored or [] if isinstance(r, list) and len(r) in (8, 10) and isinstance(r[0], str)}
    by_time.update({r[0]: r for r in fresh})
    limit = now - timedelta(days=KEEP_DAYS)
    return [by_time[k] for k in sorted(by_time, key=datetime.fromisoformat) if datetime.fromisoformat(k) >= limit]


def _solve(rows, prior, strength):
    """Least squares pulled toward `prior`: (XᵀX + λI)β = Xᵀy + λ·prior, by Gaussian elimination."""
    keys = list(prior)
    size = len(keys)
    a = [[strength if i == j else 0.0 for j in range(size)] for i in range(size)]
    b = [strength * prior[k] for k in keys]
    for x, y in rows:
        for i in range(size):
            b[i] += x[i] * y
            for j in range(size):
                a[i][j] += x[i] * x[j]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return dict(prior)
        a[col], a[pivot], b[col], b[pivot] = a[pivot], a[col], b[pivot], b[col]
        for r in range(size):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [v - f * w for v, w in zip(a[r], a[col])]
                b[r] -= f * b[col]
    return {k: b[i] / a[i][i] for i, k in enumerate(keys)}


def _pairs(rows):
    """Consecutive samples, half an hour apart."""
    for first, second in zip(rows, rows[1:]):
        if datetime.fromisoformat(second[0]) - datetime.fromisoformat(first[0]) == STEP:
            yield first, second


def _thermal_x(r):
    _, ti, _, te, _, sun, opened, heated = r[:8]
    return [te - ti, sun, heated, opened * (te - ti), 1.0]


def _water_x(r):
    _, ti, hi, te, he, _, opened, _ = r[:8]
    gap = absolute(te, he) - absolute(ti, hi)
    return [gap, opened * gap, 1.0]


def fit(rows):
    """The twin's coefficients, with the number of samples they rest on."""
    pairs = list(_pairs(rows or []))
    thermal = _solve([(_thermal_x(r), s[1] - r[1]) for r, s in pairs], PRIOR_T, PRIOR_STRENGTH)
    water = _solve([(_water_x(r), absolute(s[1], s[2]) - absolute(r[1], r[2])) for r, s in pairs], PRIOR_W, PRIOR_STRENGTH)
    # Keep the coefficients physical: a room follows the outside, never runs away from it.
    thermal["a"] = min(1.0, max(HOURS / 500, thermal["a"]))
    water["n"] = min(1.0, max(HOURS / 100, water["n"]))
    # The sun, the heating and an open window never cool a room nor dry it less: a negative value is noise.
    for coefficients, keys in ((thermal, ("b", "c", "d")), (water, ("m",))):
        for key in keys:
            coefficients[key] = max(0.0, coefficients[key])
    return {"thermal": {k: round(v, 5) for k, v in thermal.items()}, "water": {k: round(v, 5) for k, v in water.items()},
            "air": {name: fit_air(pairs, index, base) for name, index, base in AIR},
            "samples": len(pairs), "open_samples": sum(1 for r, _ in pairs if r[6] > 0),
            "sunny_samples": sum(1 for r, _ in pairs if r[5] > 0.1), "heated_samples": sum(1 for r, _ in pairs if r[7] > 0)}


# The air: CO₂ falls toward the outdoor level (about 420 ppm), a VOC index toward its usual level (100).
AIR = (("co2", 8, 420.0), ("voc", 9, 100.0))
PRIOR_AIR = {"a": 0.1, "b": 0.5, "g": 0.0}


def fit_air(pairs, index, base):
    """How the room's CO₂ or VOC goes back to its base, windows shut (`a`) and open (`a + b`), half an hour at a time.
    None without measures; `open_samples` says how many open half hours it rests on."""
    data = [(r, s) for r, s in pairs if len(r) > index and r[index] is not None and s[index] is not None]
    if not data:
        return None
    coefficients = _solve([([base - r[index], r[6] * (base - r[index]), 1.0], s[index] - r[index]) for r, s in data], PRIOR_AIR, PRIOR_STRENGTH)
    coefficients["a"] = min(0.9, max(0.0, coefficients["a"]))
    coefficients["b"] = min(0.9 - coefficients["a"], max(0.0, coefficients["b"]))
    return {**{k: round(v, 5) for k, v in coefficients.items()}, "base": base, "samples": len(data),
            "open_samples": sum(1 for r, _ in data if r[6] > 0)}


def air_after(air, value, minutes, opened=1.0):
    """The CO₂ or VOC after `minutes` with the windows open (or shut), as the room has learned it."""
    share = air["a"] + air["b"] * opened
    steps = minutes / (HOURS * 60)
    return air["base"] + (value - air["base"]) * (1 - share) ** steps + air["g"] * steps


def step(model, ti, hi, te, he, sun=0.0, opened=0.0, heated=0.0):
    """The room half an hour later, from now and the coming inputs."""
    t, w = model["thermal"], model["water"]
    gap = te - ti
    nti = ti + t["a"] * gap + t["b"] * sun + t["c"] * heated + t["d"] * opened * gap + t["e"]
    water, outside = absolute(ti, hi), absolute(te, he)
    nw = max(0.1, water + w["n"] * (outside - water) + w["m"] * opened * (outside - water) + w["g"])
    return nti, min(100.0, nw / absolute(nti, 100) * 100)


def replay(model, rows, hours=24):
    """The last `hours` simulated from their first measure with the real weather and windows, against what was measured."""
    count = int(hours / HOURS)
    recent = rows[-(count + 1):] if len(rows) > count else []
    if len(recent) < count + 1 or any(datetime.fromisoformat(b[0]) - datetime.fromisoformat(a[0]) != STEP
                                      for a, b in zip(recent, recent[1:])):
        return None
    ti, hi = recent[0][1], recent[0][2]
    curve, errors_t, errors_h = [], [], []
    for row, nxt in zip(recent, recent[1:]):
        ti, hi = step(model, ti, hi, row[3], row[4], row[5], row[6], row[7])
        curve.append({"time": nxt[0], "temperature": round(ti, 1), "measured_temperature": nxt[1],
                      "humidity": round(hi), "measured_humidity": round(nxt[2])})
        errors_t.append(abs(ti - nxt[1]))
        errors_h.append(abs(hi - nxt[2]))
    return {"hours": hours, "temperature": round(sum(errors_t) / len(errors_t), 2),
            "humidity": round(sum(errors_h) / len(errors_h), 1), "curve": curve}


def describe(model):
    """What the twin says of the room, in physical units; None for what it cannot tell yet."""
    t, w = model["thermal"], model["water"]
    a = t["a"]
    window = a + t["d"]
    return {"inertia_hours": round(HOURS / a, 1),
            # Degrees above the outside at equilibrium for a strong sun (500 W/m² on the station).
            "sun_degrees": round(t["b"] * 0.5 / a, 1) if model["sunny_samples"] >= 12 else None,
            "heating_degrees": round(t["c"] / a, 1) if model["heated_samples"] >= 12 else None,
            "household_degrees": round(t["e"] / a, 1),
            # Minutes for an open window to halve the gap with the outside.
            "window_half_minutes": round(math.log(2) * HOURS * 60 / window) if model["open_samples"] >= 6 and window > 0 else None,
            "air_changes_per_hour": round(w["n"] / HOURS, 2),
            "window_air_changes_per_hour": round((w["n"] + w["m"]) / HOURS, 2) if model["open_samples"] >= 6 else None,
            "water_per_hour": round(w["g"] / HOURS, 2)}


def summary(rows, now, current=None):
    """Everything the panel, the sensors and other bricks read of the twin: fit, words, precision, next hour."""
    model = fit(rows)
    days = 0.0
    if rows:
        days = round((datetime.fromisoformat(rows[-1][0]) - datetime.fromisoformat(rows[0][0])).total_seconds() / 86400, 1)
    ready = model["samples"] >= READY_SAMPLES
    result = {"version": 1, "status": "ready" if ready else "learning", "samples": model["samples"], "days": days,
              "open_samples": model["open_samples"], "model": model, "room": describe(model) if ready else None,
              "precision": replay(model, rows) if ready else None, "next_hour": None, "computed_at": now.isoformat()}
    result["next_hour"] = next_hour(result, current)
    return result


# Learning is optimal after a week of measures, when the twin replays the last day this closely.
OPTIMAL_DAYS = 7
OPTIMAL_TEMPERATURE, OPTIMAL_HUMIDITY = 0.5, 3.0
# Airings learned at least, before a drying result is promised.
MIN_OPENINGS = 5


def optimal(twin):
    """Has this room's twin proved itself: a week of measures and the last day replayed closely?"""
    precision = (twin or {}).get("precision")
    return bool(twin and twin.get("status") == "ready" and twin.get("days", 0) >= OPTIMAL_DAYS and precision
                and precision.get("temperature") is not None and precision["temperature"] <= OPTIMAL_TEMPERATURE
                and precision.get("humidity") is not None and precision["humidity"] <= OPTIMAL_HUMIDITY)


def learned_advice(assessment, twin, current=None, openings=0, feedback=None):
    """The result an advised airing will bring, corrected by how the last ones turned out; see `_learned`."""
    learned = _learned(assessment, twin, current, openings)
    if learned is None or (feedback and feedback.get("trusted") is False):
        # Predictions that stopped holding take the room back to estimated advice.
        return None
    gap = ((feedback or {}).get("bias") or {}).get(learned["measure"])
    if gap:
        limit = {"humidity": 5, "temperature": 1, "co2": 150, "voc": 40}[learned["measure"]]
        learned["after"] = round(learned["after"] + max(-limit, min(limit, gap)), 1 if learned["measure"] == "temperature" else 0)
        learned["corrected"] = True
    return learned


def _learned(assessment, twin, current=None, openings=0):
    """The result an advised airing will bring, as this room has learned it; None unless its learning is optimal.

    Drying comes from the room's own past airings (engine/learning.py), cooling from its twin, half an hour open."""
    if not optimal(twin) or assessment.get("action") not in ("ouvrir", "ok"):
        return None
    basis = {"days": twin["days"], "precision": {k: twin["precision"][k] for k in ("temperature", "humidity")}}
    reason, features = assessment.get("reason"), assessment.get("features") or {}
    drying = features.get("drying") or {}
    if reason == "drying_possible" and drying.get("openings", 0) >= MIN_OPENINGS and drying.get("after") is not None:
        return {"now": drying["now"], "after": drying["after"], "minutes": drying["minutes"], "measure": "humidity",
                "openings": drying["openings"], **basis}
    model = twin.get("model")
    if reason in ("air_needed", "short_air_change") and model and current:
        air = (features.get("air") or {})
        name = "co2" if air.get("co2_status") == "high" else "voc" if air.get("voc_status") == "high" else None
        learned_air = (model.get("air") or {}).get(name) if name else None
        value = current.get(name) if name else None
        span = (features.get("ventilation") or {}).get("duration_minutes") or {}
        minutes = int(span.get("max") or (5 if reason == "short_air_change" else 10))
        if learned_air and learned_air["open_samples"] >= 6 and learned_air["b"] > 0 and isinstance(value, (int, float)):
            after = air_after(learned_air, value, minutes)
            if after < value - (50 if name == "co2" else 10):
                return {"now": round(value), "after": round(after), "minutes": minutes, "measure": name, "openings": openings, **basis}
        return None
    if (reason == "cooling_possible" and model and model.get("open_samples", 0) >= 6 and current
            and None not in (current.get(k) for k in ("ti", "hi", "te", "he"))):
        after, _ = step(model, current["ti"], current["hi"], current["te"], current["he"], current.get("sun", 0.0), 1.0, 0.0)
        if after < current["ti"] - 0.2:
            return {"now": round(current["ti"], 1), "after": round(after, 1), "minutes": int(HOURS * 60), "measure": "temperature",
                    "openings": openings, **basis}
    return None


def next_hour(twin, current):
    """The room in one hour if the weather and the windows stay as they are now; None until the twin is ready."""
    if not twin or twin.get("status") != "ready" or not current or None in (current.get(k) for k in ("ti", "hi", "te", "he")):
        return None
    ti, hi = current["ti"], current["hi"]
    for _ in range(2):
        ti, hi = step(twin["model"], ti, hi, current["te"], current["he"], current.get("sun", 0.0), current.get("opened", 0.0), current.get("heated", 0.0))
    return {"temperature": round(ti, 1), "humidity": round(hi)}
