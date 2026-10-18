"""Learning what airing really does in a room, from its past openings."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.niak_comfort.engine import learning
from custom_components.niak_comfort.engine.assessment import assess
from custom_components.niak_comfort.engine.sources import Reading

T0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
SATURATED_20 = learning.absolute(20, 100)


def room(tau, residual, openings, minutes=180, outdoor=(12.0, 80.0), start_water=14.5, blip=False):
    """Indoor water relaxing toward outdoor + residual while open, constant while closed; 20 °C inside."""
    outdoor_water = learning.absolute(*outdoor)
    contacts, humidity = [], []
    for i in range(openings):
        start = T0 + timedelta(days=i)
        water = start_water
        contacts += [(start - timedelta(hours=1), False), (start, True), (start + timedelta(minutes=minutes), False)]
        if blip:
            contacts += [(start + timedelta(minutes=40), None), (start + timedelta(minutes=41), True)]
        for step in range(-12, minutes // 5 + 12):
            when = start + timedelta(minutes=5 * step)
            if 0 < step <= minutes // 5:
                water = outdoor_water + residual + (water - outdoor_water - residual) * math.exp(-5 / tau)
            humidity.append((when, water / SATURATED_20 * 100))
    first = T0 - timedelta(days=1)
    return {"binary_sensor.window": contacts}, [(first, 20.0)], humidity, [(first, outdoor[0])], [(first, outdoor[1])]


class LearningTests(unittest.TestCase):
    def test_a_room_recovers_its_own_drying_speed_and_floor(self):
        model = learning.fit(learning.episodes(*room(tau=60, residual=1.5, openings=5)))
        self.assertEqual(model["openings"], 5)
        self.assertAlmostEqual(model["tau"], 60, delta=9)
        self.assertAlmostEqual(model["residual"], 1.5, delta=0.3)

    def test_a_one_minute_radio_dropout_does_not_split_the_opening(self):
        self.assertEqual(len(learning.episodes(*room(tau=60, residual=1.5, openings=1, blip=True))), 1)

    def test_the_water_coming_back_after_closing_is_measured(self):
        contacts, ti, hi, te, he = room(tau=30, residual=0.5, openings=1, minutes=60)
        close = T0 + timedelta(minutes=60)
        before = [v for t, v in hi if t <= close]
        # Half of what was removed comes back within the next 45 minutes.
        back = before[-1] + (before[0] - before[-1]) / 2
        hi = [(t, v) for t, v in hi if t <= close] + [(close + timedelta(minutes=30), back)]
        self.assertAlmostEqual(learning.episodes(contacts, ti, hi, te, he)[0]["rebound"], 0.5, delta=0.02)

    def test_without_openings_the_default_room_is_used(self):
        self.assertEqual(learning.fit([]), {**learning.DEFAULT, "openings": 0})

    def test_stored_openings_merge_and_age_out(self):
        old = {"start": (T0 - timedelta(days=120)).isoformat(), "n": 3, "sx": 1, "sy": 1, "sxx": 1, "sxy": 1}
        kept = {"start": T0.isoformat(), "n": 3, "sx": 1, "sy": 1, "sxx": 1, "sxy": 1}
        fresh = {**kept, "n": 9}
        self.assertEqual(learning.merge([old, kept], [fresh], T0), [fresh])

    def test_the_promise_is_far_below_a_full_air_replacement(self):
        # Chambre P on 17 October: 20.2 °C, 76 %; outdoor 13.1 °C, 81 %.
        ai, ae = learning.absolute(20.2, 76), learning.absolute(13.1, 81)
        theoretical = ae / learning.absolute(20.2, 100) * 100
        slow = learning.outcome({"tau": 165, "residual": 2.0, "rebound": 0.37}, 20.2, ai, ae)
        self.assertLess(theoretical, 55)
        self.assertGreater(slow["after"], 72)
        self.assertEqual(slow["minutes"], 60)


def wet_room(model=None, opened=False, hours=None, now=None):
    values = {"indoor_temperature": 20.0, "outdoor_temperature": 12.0, "indoor_humidity": 78.0,
              "outdoor_humidity": 80.0, "window:fen": opened}
    readings = {k: Reading(v, "valid", "fictitious") for k, v in values.items()}
    return assess(readings, context={"drying_model": model} if model else None,
                  outlook={"hours": hours} if hours else None, now=now)


SLOW = {"tau": 250.0, "residual": 2.5, "rebound": 0.5, "openings": 6}


class DryingAdviceTests(unittest.TestCase):
    def test_an_ordinary_room_is_told_how_long_to_air(self):
        result = wet_room()
        self.assertEqual((result.action, result.reason), ("ouvrir", "drying_possible"))
        self.assertGreaterEqual(result.features["drying"]["gain"], learning.MIN_GAIN)
        self.assertEqual(result.features["ventilation"]["duration_minutes"], {"min": 35, "max": 45})

    def test_a_room_that_barely_dries_is_not_told_to_open(self):
        result = wet_room(SLOW)
        self.assertEqual((result.action, result.reason), ("attendre", "drying_slow"))
        self.assertLess(result.features["drying"]["gain"], learning.MIN_GAIN)

    def test_an_open_window_keeps_its_airing_to_the_end(self):
        result = wet_room(SLOW, opened=True)
        self.assertEqual((result.action, result.reason), ("ok", "drying_possible"))

    def test_a_much_drier_evening_is_announced(self):
        now = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
        hours = [{"time": (now + timedelta(hours=h)).isoformat(), "temperature": 12.0 if h < 5 else 4.0,
                  "humidity": 80.0, "precipitation": 0} for h in range(0, 12)]
        # Little to gain now (the room keeps 4 g/m³ above the outdoor air), much more once it is colder.
        model = {"tau": 60.0, "residual": 4.0, "rebound": 0.4, "openings": 6}
        result = wet_room(model, hours=hours, now=now)
        self.assertEqual((result.action, result.reason), ("attendre", "drying_later"))
        self.assertEqual(datetime.fromisoformat(result.features["drying"]["later"]["time"]), now + timedelta(hours=5))

    def test_a_forecast_far_from_the_station_announces_no_better_hour(self):
        now = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
        # The forecast says 20 °C now while the station measures 12 °C.
        hours = [{"time": (now + timedelta(hours=h)).isoformat(), "temperature": 20.0 if h < 5 else 4.0,
                  "humidity": 80.0, "precipitation": 0} for h in range(0, 12)]
        model = {"tau": 60.0, "residual": 4.0, "rebound": 0.4, "openings": 6}
        self.assertIsNone(wet_room(model, hours=hours, now=now).features["drying"]["later"])

    def test_a_worthwhile_airing_now_is_not_postponed(self):
        now = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
        hours = [{"time": (now + timedelta(hours=h)).isoformat(), "temperature": 12.0 if h < 5 else 4.0,
                  "humidity": 80.0, "precipitation": 0} for h in range(0, 12)]
        result = wet_room(hours=hours, now=now)
        self.assertEqual((result.action, result.reason), ("ouvrir", "drying_possible"))
        self.assertIsNotNone(result.features["drying"]["later"])



class UsefulAdviceTests(unittest.TestCase):
    """A banner speaks only when it brings something."""
    def room(self, humidity=64.0, outdoor=(13.0, 92.0), context=None, **extra):
        values = {"indoor_temperature": 21.0, "outdoor_temperature": outdoor[0], "indoor_humidity": humidity,
                  "outdoor_humidity": outdoor[1], "window:fen": False, **extra}
        return assess({k: Reading(v, "valid", "fictitious") for k, v in values.items()}, context=context)

    def test_a_little_above_the_threshold_for_a_moment_is_not_a_need(self):
        # Default threshold 62 %: 64 % for a moment is fine, three hours above it or 68 % is not.
        self.assertNotIn("dry", self.room(64.0).needs)
        self.assertIn("dry", self.room(64.0, context={"humidity_floor_3h": 63.0}).needs)
        self.assertIn("dry", self.room(68.0).needs)

    def test_outdoor_air_as_wet_as_inside_leaves_the_banner_calm(self):
        # Like the Salon on 18 October: 21 °C inside, 13 °C and 92 % outside, everything closed.
        result = self.room(68.0)
        self.assertIn(result.reason, ("drying_unavailable", "drying_slow"))
        self.assertEqual((result.action, result.level), ("attendre", "calm"))

    def test_the_ventilation_is_offered_where_the_window_dries_little(self):
        slow = {"drying_model": {"tau": 250.0, "residual": 2.5, "rebound": 0.5, "openings": 6}}
        result = self.room(78.0, outdoor=(12.0, 80.0), context=slow, ventilation=False)
        self.assertEqual((result.reason, result.level), ("ventilation_possible", "action"))
        quiet = self.room(78.0, outdoor=(12.0, 80.0), context=slow)
        self.assertEqual((quiet.reason, quiet.level), ("drying_slow", "calm"))


if __name__ == "__main__":
    unittest.main()
