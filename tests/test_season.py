"""Seasonal comfort range and unheated rooms, on synthetic readings only."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "niak_comfort"))
from engine.assessment import Settings, assess, seasonal
from engine.sources import Reading


def readings(ti, te=15.0):
    values = {"indoor_temperature": ti, "outdoor_temperature": te, "indoor_humidity": 50.0,
              "outdoor_humidity": 50.0, "window:fen": False}
    return {k: Reading(v, "valid", "fictitious") for k, v in values.items()}


class SeasonalRangeTests(unittest.TestCase):
    def test_unknown_mean_keeps_saved_range(self):
        settings, info = seasonal(Settings(), None)
        self.assertEqual(settings.maximum, 24)
        self.assertFalse(info["known"])

    def test_winter_keeps_winter_limit_and_summer_reaches_summer_limit(self):
        self.assertEqual(seasonal(Settings(), 8)[0].maximum, 24)
        self.assertEqual(seasonal(Settings(), 12)[0].maximum, 24)
        self.assertEqual(seasonal(Settings(), 20)[0].maximum, 26)
        self.assertEqual(seasonal(Settings(), 31)[0].maximum, 26)

    def test_between_seasons_moves_smoothly(self):
        self.assertEqual(seasonal(Settings(), 16)[0].maximum, 25.0)
        self.assertEqual(seasonal(Settings(), 16)[1]["weight"], 0.5)

    def test_summer_limit_never_lowers_the_saved_maximum(self):
        settings, _ = seasonal(Settings(maximum=27, summer_maximum=26), 25)
        self.assertEqual(settings.maximum, 27)

    def test_summer_limit_must_be_above_the_minimum(self):
        with self.assertRaises(ValueError):
            Settings(minimum=20, summer_maximum=20)

    def test_a_warm_room_needs_cooling_in_winter_but_not_in_summer(self):
        winter = assess(readings(25.0), context={"outdoor_mean_7d": 8})
        summer = assess(readings(25.0), context={"outdoor_mean_7d": 24})
        self.assertIn("cool", winter.needs)
        self.assertNotIn("cool", summer.needs)

    def test_the_effective_range_is_published(self):
        result = assess(readings(22.0), context={"outdoor_mean_7d": 16})
        self.assertEqual(result.features["season"]["maximum"], 25.0)
        self.assertEqual(result.features["season"]["minimum"], 20)


class UnheatedRoomTests(unittest.TestCase):
    def test_a_cold_heated_room_asks_for_warmth(self):
        self.assertIn("heat", assess(readings(17.0, 10.0)).needs)

    def test_an_unheated_room_never_asks_for_warmth(self):
        result = assess(readings(17.0, 10.0), context={"heated": False})
        self.assertNotIn("heat", result.needs)
        self.assertEqual(result.level, "calm")
        self.assertFalse(result.features["season"]["heated"])

    def test_an_unheated_room_still_follows_heat_and_humidity(self):
        result = assess(readings(27.0, 15.0), context={"heated": False, "outdoor_mean_7d": 8})
        self.assertIn("cool", result.needs)


class DayRangeTests(unittest.TestCase):
    def test_the_range_includes_the_current_reading(self):
        result = assess(readings(25.4), context={"indoor_day_range": {"min": 21.0, "max": 24.8}})
        self.assertEqual(result.features["day_range"], {"min": 21.0, "max": 25.4})

    def test_an_unknown_or_invalid_range_is_not_drawn(self):
        self.assertIsNone(assess(readings(22.0)).features["day_range"])
        self.assertIsNone(assess(readings(22.0), context={"indoor_day_range": {"min": 25, "max": 20}}).features["day_range"])


if __name__ == "__main__":
    unittest.main()
