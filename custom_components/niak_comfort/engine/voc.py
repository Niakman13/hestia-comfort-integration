"""VOC that call for air: steady enough to be worth an airing, not every passing peak.

A Sensirion VOC index (IKEA VINDSTYRKA and others) is relative: 100 is the home's own mean of the last 24 hours,
500 its ceiling. It moves a lot: cooking, a cleaning product, a candle, someone coming in. Compared moment by moment
with a threshold, it crosses it again and again and the advice comes and goes. So:

- the index is judged on its mean over the last MEAN_MINUTES, not on one reading;
- a margin: it calls for air above the threshold, and stops below the threshold minus MARGIN of it (like the CO₂);
- a delay: only once above for `delay` minutes (10 by default), except a strong peak (twice the threshold) at once;
- a pause after an airing: for `pause` minutes (45 by default) no new call, unless the index climbs well above what the
  airing left (by RISE of the threshold): while the pan is still on the stove, opening ten times does not help.
"""
from datetime import datetime, timedelta

MEAN_MINUTES = 10
MARGIN = 0.2
STRONG = 2.0
RISE = 1 / 3
DELAY_MINUTES = 10
PAUSE_MINUTES = 45


def _since(value):
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def judge(value, threshold, now, *, mean=None, was_high=False, above_since=None, delay=DELAY_MINUTES,
          pause=PAUSE_MINUTES, aired_at=None, aired_after=None):
    """{"high", "above_since", "minutes", "mean", "paused"} for one reading of the index; `mean` is the recent mean."""
    level = mean if isinstance(mean, (int, float)) else value
    limit = threshold * (1 - MARGIN) if was_high else threshold
    above = level >= limit
    since = (_since(above_since) or now) if above and now else None
    minutes = (now - since).total_seconds() / 60 if since and now else 0.0
    strong = value >= threshold * STRONG
    # Without a clock (a single reading judged alone), no delay can be counted: judged at once.
    high = above and (now is None or was_high or strong or minutes >= delay)
    # Right after an airing, the source is often still there: no new call unless the index climbs well above.
    aired = _since(aired_at)
    paused = (high and not was_high and not strong and aired is not None and now is not None
              and now - aired < timedelta(minutes=pause) and isinstance(aired_after, (int, float))
              and level < aired_after + threshold * RISE)
    return {"high": high and not paused, "above_since": since.isoformat() if since else None, "minutes": round(minutes),
            "mean": round(level), "paused": paused}


def mean(points, now, minutes=MEAN_MINUTES):
    """The index's mean over the last `minutes`, each reading weighed by how long it stood; None without one.

    `points`: [(datetime, value)] in time order. A reading taken before the window counts from its start."""
    start = now - timedelta(minutes=minutes)
    total = weight = 0.0
    for i, (when, value) in enumerate(points):
        until = points[i + 1][0] if i + 1 < len(points) else now
        span = (min(until, now) - max(when, start)).total_seconds()
        if span > 0:
            total += value * span
            weight += span
    return total / weight if weight else (points[-1][1] if points else None)
