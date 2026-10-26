"""« Rallumez le chauffage » only for a room clearly and lastingly cold, not warming by itself."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Settings, assess
from engine.sources import Reading

NOW = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
SETTINGS = Settings(minimum=20, maximum=24)


def run(ti, previous=None, now=NOW, settings=SETTINGS, heating="off", occupied=True, **context):
    values = {"indoor_temperature": ti, "outdoor_temperature": 12, "indoor_humidity": 55, "outdoor_humidity": 80,
              "heating": heating}
    readings = {k: Reading(v, "valid", "sensor.x") for k, v in values.items()}
    return assess(readings, settings, previous, {}, None, {}, now, context={"heated": True, "occupied": occupied, **context})


class HeatingAdvice(unittest.TestCase):
    def test_within_tolerance_is_only_said(self):
        a = run(19.2)
        self.assertEqual(a.reason, "heat_needed")
        self.assertIn(a.level, ("calm", "neutral"))
        self.assertIsNone(a.features["warmth"]["chilly_since"])

    def test_clearly_cold_waits_half_an_hour(self):
        first = run(18.5)
        self.assertIn(first.level, ("calm", "neutral"))
        self.assertEqual(first.features["warmth"]["chilly_since"], NOW.isoformat())
        later = run(18.5, first, NOW + timedelta(minutes=31))
        self.assertEqual(later.level, "action")
        self.assertEqual(later.features["warmth"]["chilly_since"], NOW.isoformat())

    def test_hysteresis_keeps_the_advice_until_the_room_recovers(self):
        first = run(18.5)
        on = run(18.5, first, NOW + timedelta(minutes=31))
        # 19.2: back within the tolerance, but not by more than the hysteresis: the advice holds.
        self.assertEqual(run(19.2, on, NOW + timedelta(minutes=40)).level, "action")
        self.assertIn(run(19.6, on, NOW + timedelta(minutes=40)).level, ("calm", "neutral"))

    def test_a_room_warming_by_itself_is_not_told_to_heat(self):
        first = run(18.5)
        a = run(18.5, first, NOW + timedelta(minutes=31), next_hour_temperature=19.0)
        self.assertIn(a.level, ("calm", "neutral"))
        self.assertTrue(a.features["warmth"]["warming"])

    def test_zero_tolerance_restores_the_strict_rule(self):
        strict = Settings(minimum=20, maximum=24, heating_tolerance=0)
        first = run(19.8, settings=strict)
        self.assertEqual(run(19.8, first, NOW + timedelta(minutes=31), settings=strict).level, "action")

    def test_empty_home_or_heating_on_stays_quiet(self):
        first = run(17, occupied=False)
        self.assertIn(run(17, first, NOW + timedelta(hours=1), occupied=False).level, ("calm", "neutral"))
        first = run(17, heating="heating")
        self.assertIn(run(17, first, NOW + timedelta(hours=1), heating="heating").level, ("calm", "neutral"))

    def test_tolerance_is_bounded(self):
        with self.assertRaises(ValueError):
            Settings(heating_tolerance=-1)
        with self.assertRaises(ValueError):
            Settings(heating_tolerance=6)


if __name__ == "__main__":
    unittest.main()
