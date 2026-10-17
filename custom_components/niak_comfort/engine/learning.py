"""What airing really does in each room, learned from its past openings.

The theoretical promise (« the outdoor air, warmed inside, would bring the room to 52 % ») assumes the
whole air is replaced. Real rooms never get there: a tilted window renews little air, walls and fabrics
give their water back, a bathroom next door keeps feeding moisture. So each room learns, from its own
history, three numbers:

- `tau`: minutes for the indoor water content to cover about two thirds of its way toward its floor;
- `residual`: g/m³ the room keeps above the outdoor air even after a long airing (its moisture sources);
- `rebound`: share of the water removed that comes back within 45 minutes once the window is closed.

Each opening is summarised by a few sums (a least-squares fit of the 5-minute change of the indoor water
content against its gap to the outdoor air), so episodes can be stored, merged and refitted cheaply.
"""
from bisect import bisect_right
from datetime import datetime, timedelta
import math

STEP = timedelta(minutes=5)
REBOUND_AFTER = timedelta(minutes=45)
MIN_OPENING = timedelta(minutes=10)
BLIP = timedelta(minutes=10)
# Before any opening is learned: a modest, ordinary room rather than a full air replacement.
DEFAULT = {"tau": 45.0, "residual": 1.0, "rebound": 0.4}
# Open-window time weighing as much as the default: two hours of 5-minute steps move the model halfway.
PRIOR_STEPS = 24
# Closings weighing as much as the default rebound.
PRIOR_CLOSINGS = 2
# A lasting gain under this (humidity points) is not worth asking to open.
MIN_GAIN = 5.0
# g/m³ between the station and the forecast beyond which the forecast is not trusted for timing.
MAX_FORECAST_BIAS = 2.5
KEEP_DAYS = 90
KEEP_EPISODES = 60


def absolute(temperature: float, relative: float) -> float:
    """Water content of the air in g/m³ (Magnus formula)."""
    return 6.112 * math.exp(17.67 * temperature / (temperature + 243.5)) * relative * 2.1674 / (273.15 + temperature)


class _Series:
    """A sample-and-hold series: the value at a time is the last one reported before it."""
    def __init__(self, points):
        points = sorted(p for p in points if p[1] is not None and math.isfinite(p[1]))
        self.times = [t for t, _ in points]
        self.values = [v for _, v in points]

    def at(self, when):
        i = bisect_right(self.times, when)
        return self.values[i - 1] if i else None


def _intervals(contacts):
    """Periods when at least one opening of the room was open. `contacts`: {entity: [(time, bool|None)]}.

    Each period says whether it ended on a real closing (False when a contact stopped answering).
    """
    changes = []
    for entity, points in contacts.items():
        points = sorted(points)
        for i, (when, value) in enumerate(points):
            # Radio contacts drop out for a minute and come back: a short silence is not a closing.
            if value is None and i + 1 < len(points) and points[i + 1][0] - when < BLIP:
                continue
            changes.append((when, entity, value))
    changes.sort()
    state, intervals, start = {}, [], None
    for when, entity, value in changes:
        state[entity] = value
        if value is None:
            if start is not None:
                intervals.append((start, when, False))
                start = None
            continue
        if any(v is None for v in state.values()):
            continue
        opened = any(state.values())
        if opened and start is None:
            start = when
        elif not opened and start is not None:
            intervals.append((start, when, True))
            start = None
    return intervals


def episodes(contacts, indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity):
    """One summary per opening of at least ten minutes, from raw (time, value) points.

    Water contents come from both temperature and humidity, so the cooling of an aired room is not
    taken for drying.
    """
    ti, hi, te, he = (_Series(p) for p in (indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity))

    def water(when):
        a, b, c, d = ti.at(when), hi.at(when), te.at(when), he.at(when)
        if None in (a, b, c, d) or not (0 < b <= 100 and 0 < d <= 100):
            return None
        return absolute(a, b), absolute(c, d)

    spans = _intervals(contacts)
    result = []
    for index, (start, end, closed) in enumerate(spans):
        if end - start < MIN_OPENING:
            continue
        n = sx = sy = sxx = sxy = 0.0
        when, before = start, water(start)
        while when + STEP <= end:
            after = water(when + STEP)
            if before and after:
                gap, change = before[0] - before[1], after[0] - before[0]
                n, sx, sy, sxx, sxy = n + 1, sx + gap, sy + change, sxx + gap * gap, sxy + gap * change
            when, before = when + STEP, after
        if n < 2:
            continue
        rebound = None
        first, last, later = water(start), water(end), water(end + REBOUND_AFTER)
        reopened = index + 1 < len(spans) and spans[index + 1][0] < end + REBOUND_AFTER
        if closed and not reopened and first and last and later and first[0] - last[0] >= 0.5:
            rebound = min(1.0, max(0.0, (later[0] - last[0]) / (first[0] - last[0])))
        result.append({"start": start.isoformat(), "minutes": round((end - start).total_seconds() / 60),
                       "n": int(n), "sx": round(sx, 4), "sy": round(sy, 4), "sxx": round(sxx, 4), "sxy": round(sxy, 4),
                       "rebound": None if rebound is None else round(rebound, 3)})
    return result


def merge(stored, fresh, now):
    """Stored episodes plus the fresh ones (same start: the fresh summary wins), recent ones only."""
    by_start = {e["start"]: e for e in stored or [] if isinstance(e, dict) and isinstance(e.get("start"), str)}
    by_start.update({e["start"]: e for e in fresh})
    limit = now - timedelta(days=KEEP_DAYS)
    kept = []
    for start, episode in by_start.items():
        try:
            if datetime.fromisoformat(start) >= limit:
                kept.append(episode)
        except ValueError:
            continue
    return sorted(kept, key=lambda e: e["start"])[-KEEP_EPISODES:]


def fit(records):
    """The room's model: the learned numbers, pulled toward the default while few openings are known."""
    records = [e for e in records or [] if all(isinstance(e.get(k), (int, float)) for k in ("n", "sx", "sy", "sxx", "sxy"))]
    count, n = len(records), sum(e["n"] for e in records)
    tau, residual = DEFAULT["tau"], DEFAULT["residual"]
    if count and n >= 6:
        sx, sy, sxx, sxy = (sum(e[k] for e in records) for k in ("sx", "sy", "sxx", "sxy"))
        spread = sxx - sx * sx / n
        if spread > 0.02 * n:
            # Water lost per 5 minutes for each g/m³ of gap; none at all means the window barely renews the air.
            k = min(1.0, max(5 / 600, -(sxy - sx * sy / n) / spread))
            tau = 5 / k
            residual = min(5.0, max(-1.0, (sy + k * sx) / n / k))
    weight = n / (n + PRIOR_STEPS)
    rebounds = sorted(e["rebound"] for e in records if isinstance(e.get("rebound"), (int, float)))
    rebound = rebounds[len(rebounds) // 2] if rebounds else DEFAULT["rebound"]
    rebound_weight = len(rebounds) / (len(rebounds) + PRIOR_CLOSINGS)
    return {"tau": round(math.exp(weight * math.log(tau) + (1 - weight) * math.log(DEFAULT["tau"])), 1),
            "residual": round(weight * residual + (1 - weight) * DEFAULT["residual"], 2),
            "rebound": round(min(0.8, rebound_weight * rebound + (1 - rebound_weight) * DEFAULT["rebound"]), 2),
            "openings": count}


def minutes(model):
    """How long to air: about one time constant, between 10 minutes and one hour, by steps of five."""
    return int(min(60, max(10, 5 * round(model["tau"] / 5))))


def outcome(model, indoor_temperature, indoor_water, outdoor_water, duration=None):
    """Humidity after airing for `duration` minutes, once the room has given part of its water back."""
    duration = duration or minutes(model)
    floor = outdoor_water + model["residual"]
    saturated = absolute(indoor_temperature, 100)
    now = indoor_water / saturated * 100
    removed = max(0.0, indoor_water - floor) * (1 - math.exp(-duration / model["tau"]))
    gain = removed * (1 - model["rebound"]) / saturated * 100
    return {"minutes": duration, "now": round(now, 1), "after": round(now - gain, 1), "gain": round(gain, 1)}


def best_moment(model, indoor_temperature, indoor_water, outdoor_water, hours, now, horizon=12):
    """A later hour that would dry clearly better than now, from the Niak Weather forecast.

    The forecast is set on the local station: its error at the current hour is carried over.
    """
    forecast = []
    for hour in hours or []:
        try:
            when = datetime.fromisoformat(hour["time"])
            water = absolute(float(hour["temperature"]), float(hour["humidity"]))
        except (KeyError, TypeError, ValueError):
            continue
        if when.tzinfo is None:
            continue
        rainy = isinstance(hour.get("precipitation"), (int, float)) and hour["precipitation"] >= 0.2
        forecast.append((when, None if rainy else water))
    if not forecast:
        return None
    current = min(forecast, key=lambda f: abs((f[0] - now).total_seconds()))
    if current[1] is None or abs((current[0] - now).total_seconds()) > 5400:
        return None
    bias = outdoor_water - current[1]
    if abs(bias) > MAX_FORECAST_BIAS:
        # The forecast does not describe this place well enough right now to promise a better hour.
        return None
    present = outcome(model, indoor_temperature, indoor_water, outdoor_water)["gain"]
    best = None
    for when, water in forecast:
        if water is None or not now + timedelta(hours=1) <= when <= now + timedelta(hours=horizon):
            continue
        later = outcome(model, indoor_temperature, indoor_water, max(0.5, water + bias))
        if later["gain"] >= MIN_GAIN and later["gain"] >= present + 4 and (best is None or later["gain"] > best["gain"]):
            best = {**later, "time": when.isoformat()}
    return best
