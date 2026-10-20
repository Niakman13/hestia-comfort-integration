"""The room's twin: it finds back a known room, replays its day, and stays quiet while it learns."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine import twin

START = datetime(2026, 10, 1, tzinfo=timezone.utc)


def known_room(days=6, tau=40.0, window=0.25, gains=0.08):
    """A room with a 40-hour inertia, opened every evening, under a daily outdoor swing and sun."""
    a = twin.HOURS / tau
    ti, hi, points = 20.0, 60.0, {k: [] for k in ("ti", "hi", "te", "he", "sun", "win")}
    t = START
    while t < START + timedelta(days=days):
        hour = t.hour + t.minute / 60
        te = 14 + 5 * math.sin((hour - 9) / 24 * 2 * math.pi)
        he, sun = 80.0, max(0.0, 600 * math.sin((hour - 6) / 12 * math.pi)) if 6 <= hour <= 18 else 0.0
        opened = 19 <= hour < 20
        for key, value in (("ti", ti), ("hi", hi), ("te", te), ("he", he), ("sun", sun), ("win", opened)):
            points[key].append((t, value))
        step = twin.SUB.total_seconds() / twin.STEP.total_seconds()
        gap = te - ti
        ti += step * (a * gap + 0.3 * sun / 1000 + (window * gap if opened else 0) + gains)
        water, outside = twin.absolute(ti, hi), twin.absolute(te, he)
        water += step * ((0.15 + (0.4 if opened else 0)) * (outside - water) + 0.05)
        hi = min(100.0, water / twin.absolute(ti, 100) * 100)
        t += twin.SUB
    rows = twin.samples(START, t, points["ti"], points["hi"], points["te"], points["he"], points["sun"], {"w": points["win"]})
    return rows, t


class Twin(unittest.TestCase):
    def test_it_finds_back_a_known_room(self):
        rows, end = known_room()
        result = twin.summary(rows, end, {"ti": 20, "hi": 60, "te": 0, "he": 80})
        self.assertEqual(result["status"], "ready")
        room = result["room"]
        self.assertAlmostEqual(room["inertia_hours"], 40, delta=12)
        self.assertGreater(room["sun_degrees"], 0)
        self.assertIsNotNone(room["window_half_minutes"])
        self.assertLess(result["precision"]["temperature"], 0.6)
        self.assertLess(result["precision"]["humidity"], 3)
        self.assertEqual(len(result["precision"]["curve"]), 48)
        self.assertLess(result["next_hour"]["temperature"], 20)  # 0 °C outside: the room cools

    def test_it_stays_quiet_while_learning(self):
        rows, end = known_room(days=1)
        result = twin.summary(rows, end, {"ti": 20, "hi": 60, "te": 10, "he": 80})
        self.assertEqual((result["status"], result["room"], result["precision"], result["next_hour"]), ("learning", None, None, None))

    def test_a_silent_contact_leaves_its_half_hours_out_and_old_samples_go(self):
        rows, end = known_room(days=2)
        ti = [(START, 20.0)]
        silent = twin.samples(START, START + timedelta(hours=3), ti, [(START, 60.0)], [(START, 10.0)], [(START, 80.0)],
                              contacts={"w": [(START, False), (START + timedelta(hours=1), None), (START + timedelta(hours=2), False)]})
        self.assertEqual([r[0][11:16] for r in silent], ["00:00", "00:30", "02:00", "02:30"])
        merged = twin.merge(rows, [], START + timedelta(days=31))
        self.assertTrue(all(datetime.fromisoformat(r[0]) >= START + timedelta(days=1) for r in merged))

    def test_the_sun_never_cools_a_room(self):
        rows, end = known_room()
        flipped = [[r[0], r[1], r[2], r[3], r[4], 0.0 if r[5] else 0.5, r[6], r[7]] for r in rows]
        self.assertGreaterEqual(twin.fit(flipped)["thermal"]["b"], 0)


if __name__ == "__main__":
    unittest.main()
