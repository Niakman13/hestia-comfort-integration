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


def samples(start, end, indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity,
            solar=(), contacts=None, heating=()):
    """Half-hour samples between `start` and `end` from raw (time, value) points.

    `contacts`: {entity: [(time, bool|None)]}; `heating`: [(time, bool)] running or not. A half hour with
    a contact that does not answer is left out: what a window did then is not known."""
    ti, hi, te, he = (_Series(p) for p in (indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity))
    sun, heat = _Series(solar), _Series(heating)
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
            sunny += max(0.0, float(sun.at(t) or 0.0))
            steps, t = steps + 1, t + SUB
        if known and steps:
            rows.append([when.isoformat(), round(values[0], 2), round(values[1], 1), round(values[2], 2), round(values[3], 1),
                         round(sunny / steps / 1000, 3), round(opened / steps, 2), round(heated / steps, 2)])
        when += STEP
    return rows


def merge(stored, fresh, now):
    """Stored samples plus the fresh ones (same time: the fresh one wins), the last thirty days only."""
    by_time = {r[0]: r for r in stored or [] if isinstance(r, list) and len(r) == 8 and isinstance(r[0], str)}
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
    _, ti, _, te, _, sun, opened, heated = r
    return [te - ti, sun, heated, opened * (te - ti), 1.0]


def _water_x(r):
    _, ti, hi, te, he, _, opened, _ = r
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
            "samples": len(pairs), "open_samples": sum(1 for r, _ in pairs if r[6] > 0),
            "sunny_samples": sum(1 for r, _ in pairs if r[5] > 0.1), "heated_samples": sum(1 for r, _ in pairs if r[7] > 0)}


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


def next_hour(twin, current):
    """The room in one hour if the weather and the windows stay as they are now; None until the twin is ready."""
    if not twin or twin.get("status") != "ready" or not current or None in (current.get(k) for k in ("ti", "hi", "te", "he")):
        return None
    ti, hi = current["ti"], current["hi"]
    for _ in range(2):
        ti, hi = step(twin["model"], ti, hi, current["te"], current["he"], current.get("sun", 0.0), current.get("opened", 0.0), current.get("heated", 0.0))
    return {"temperature": round(ti, 1), "humidity": round(hi)}
