"""The walls (NADIR's two-node model): a short airing cools the air, the walls give it back once shut."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine import twin

START = datetime(2026, 7, 1, tzinfo=timezone.utc)


def heavy_room(days=7, coupling=0.25):
    """Light air over heavy walls, aired twenty minutes every evening under a summer swing."""
    a = twin.HOURS / 40
    ti = tm = 26.0
    hi, points = 55.0, {k: [] for k in ("ti", "hi", "te", "he", "sun", "win")}
    t = START
    step = twin.SUB.total_seconds() / twin.STEP.total_seconds()
    while t < START + timedelta(days=days):
        hour = t.hour + t.minute / 60
        te = 22 + 7 * math.sin((hour - 9) / 24 * 2 * math.pi)
        sun = max(0.0, 600 * math.sin((hour - 6) / 12 * math.pi)) if 6 <= hour <= 18 else 0.0
        opened = 21 <= hour < 21 + 1 / 3
        for key, value in (("ti", ti), ("hi", hi), ("te", te), ("he", 60.0), ("sun", sun), ("win", opened)):
            points[key].append((t, value))
        gap = te - ti
        ti, tm = (ti + step * (a * gap + coupling * (tm - ti) + 0.2 * sun / 1000 + (0.6 * gap if opened else 0) + 0.04),
                  tm + step * (ti - tm) * twin.HOURS / twin.MASS_HOURS)
        t += twin.SUB
    rows = twin.samples(START, t, points["ti"], points["hi"], points["te"], points["he"], points["sun"], {"w": points["win"]})
    return rows, t


class Mass(unittest.TestCase):
    def test_walls_are_found_in_a_heavy_room(self):
        rows, end = heavy_room()
        model = twin.fit(rows)
        # Half-hour samples and the prior pull it low; it is still clearly there, and absent without walls.
        self.assertGreater(model["thermal"]["z"], 0.03)

    def test_walls_make_the_replay_closer(self):
        rows, end = heavy_room()
        model = twin.fit(rows)
        flat = {**model, "thermal": {**model["thermal"], "z": 0.0}}
        self.assertLess(twin.replay(model, rows)["temperature"], twin.replay(flat, rows)["temperature"])

    def test_a_room_without_walls_keeps_none(self):
        rows, end = heavy_room(coupling=0.0)
        self.assertLess(twin.fit(rows)["thermal"]["z"], 0.01)


if __name__ == "__main__":
    unittest.main()
