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


class SunOnFacades(unittest.TestCase):
    def test_the_sun_position_at_home(self):
        # Gardanne, 21 June at solar noon (11 h 38 UTC): high in the south.
        elevation, azimuth = twin.sun_position(datetime(2026, 6, 21, 11, 38, tzinfo=timezone.utc), 43.45, 5.47)
        self.assertAlmostEqual(elevation, 70, delta=1)
        self.assertAlmostEqual(azimuth, 180, delta=3)
        # 20 October, 16 h UTC: low in the south-west.
        elevation, azimuth = twin.sun_position(datetime(2026, 10, 20, 16, tzinfo=timezone.utc), 43.45, 5.47)
        self.assertTrue(5 < elevation < 20 and 225 < azimuth < 260, (elevation, azimuth))

    def test_a_south_window_gets_the_noon_sun_a_north_one_only_light(self):
        south = twin.on_facades(600, 40, 180, [180])
        north = twin.on_facades(600, 40, 180, [0])
        self.assertGreater(south, 500)
        self.assertAlmostEqual(north, 90)  # diffuse light only
        self.assertEqual(twin.on_facades(600, 40, 180, []), 600)  # unknown facades: the station's own measure


class LearnedAdvice(unittest.TestCase):
    def ready(self, days=10, temperature=0.2, humidity=1.5):
        rows, end = known_room()
        summary = twin.summary(rows, end)
        return {**summary, "days": days, "precision": {"hours": 24, "temperature": temperature, "humidity": humidity}}

    def test_a_drying_airing_is_promised_only_when_learning_is_optimal(self):
        advice = {"action": "ouvrir", "reason": "drying_possible", "features": {"drying": {"now": 76, "after": 68, "minutes": 15, "openings": 31}}}
        learned = twin.learned_advice(advice, self.ready())
        self.assertEqual((learned["now"], learned["after"], learned["minutes"], learned["measure"], learned["openings"]), (76, 68, 15, "humidity", 31))
        # A week at least, the last day replayed within ±0.5 °C and ±3 %, five airings learned.
        self.assertIsNone(twin.learned_advice(advice, self.ready(days=5)))
        self.assertIsNone(twin.learned_advice(advice, self.ready(temperature=1.1)))
        self.assertIsNone(twin.learned_advice(advice, self.ready(humidity=4.7)))
        self.assertIsNone(twin.learned_advice(advice, {**self.ready(), "precision": None}))
        few = {**advice, "features": {"drying": {**advice["features"]["drying"], "openings": 3}}}
        self.assertIsNone(twin.learned_advice(few, self.ready()))
        # Air for CO₂ or a closing: nothing learned to promise.
        self.assertIsNone(twin.learned_advice({**advice, "reason": "air_needed"}, self.ready()))
        self.assertIsNone(twin.learned_advice({**advice, "action": "fermer"}, self.ready()))

    def test_a_cooling_airing_gets_its_learned_temperature(self):
        advice = {"action": "ouvrir", "reason": "cooling_possible", "features": {}}
        learned = twin.learned_advice(advice, self.ready(), {"ti": 26, "hi": 50, "te": 18, "he": 60}, openings=12)
        self.assertEqual((learned["measure"], learned["minutes"], learned["now"]), ("temperature", 30, 26))
        self.assertLess(learned["after"], 26)


class AirLearned(unittest.TestCase):
    def test_the_air_of_a_room_is_learned_and_promised(self):
        t, out, co2 = START, [], 1200.0
        while t < START + timedelta(days=6):
            opened = 1.0 if t.hour == 19 and t.minute == 0 else 0.0
            out.append([t.isoformat(), 21.0, 55.0, 12.0, 70.0, 0.0, opened, 0.0, round(co2), None])
            co2 = 420 + (co2 - 420) * (1 - 0.05 - 0.6 * opened) + (60 if 7 <= t.hour < 23 else 0)
            t += twin.STEP
        model = twin.fit(out)
        air = model["air"]["co2"]
        self.assertAlmostEqual(air["a"] + air["b"], 0.65, delta=0.15)
        self.assertIsNone(model["air"]["voc"])
        ready = {"status": "ready", "days": 10, "precision": {"hours": 24, "temperature": 0.2, "humidity": 1.5}, "model": model}
        advice = {"action": "ouvrir", "reason": "air_needed", "features": {"air": {"co2_status": "high"}, "ventilation": {"duration_minutes": {"min": 6, "max": 15}}}}
        learned = twin.learned_advice(advice, ready, {"co2": 1180})
        self.assertEqual((learned["measure"], learned["now"], learned["minutes"]), ("co2", 1180, 15))
        self.assertLess(learned["after"], 1000)


if __name__ == "__main__":
    unittest.main()
