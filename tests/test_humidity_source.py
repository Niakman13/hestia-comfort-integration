"""Humidity judged on what airing can gain, and mould judged on the cold walls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Settings, assess
from test_engine import zone

# 20 Oct., 13 h 50: 16.9 °C and 90 % outdoors, 12.9 g/m³ of water; no room can be aired below about 71 %.
OUT = dict(outdoor_temperature=16.9, outdoor_humidity=90)


class HumiditySource(unittest.TestCase):
    def test_current_measure_graduates_both_sides_of_the_configured_range(self):
        settings = Settings(humidity_low=40, humidity_high=60)
        for value, status, degree in [(40, "normal", 0), (60, "normal", 0), (60.6, "high", 1),
                                      (63, "high", 1), (63.1, "high", 2), (70, "high", 2),
                                      (70.1, "high", 3), (39.4, "low", 1), (37, "low", 1),
                                      (36.9, "low", 2), (30, "low", 2), (29.9, "low", 3)]:
            with self.subTest(value=value):
                result = assess(zone(indoor_humidity=value), settings=settings)
                self.assertEqual((result.features["humidity"]["status"], result.features["humidity"]["degree"]), (status, degree))

    def test_small_recovering_excess_does_not_keep_asking_for_drying(self):
        settings = Settings(humidity_high=60)
        previous = assess(zone(indoor_humidity=75), settings=settings)
        current = assess(zone(indoor_humidity=60.6), settings=settings, previous=previous)
        self.assertNotIn("dry", current.needs)
        self.assertEqual(current.features["humidity"]["degree"], 1)
        self.assertEqual(current.features["humidity"]["trend"], "improving")
        normal = assess(zone(indoor_humidity=59), settings=settings, previous=current)
        self.assertEqual(normal.features["humidity"]["status"], "normal")

    def test_unknown_humidity_stays_unknown_and_ranges_must_be_ordered(self):
        self.assertEqual(assess(zone(indoor_humidity=None)).features["humidity"]["status"], "unknown")
        for low, high in [(60, 60), (61, 60), (-1, 60), (40, 101)]:
            with self.assertRaises(ValueError):
                Settings(humidity_low=low, humidity_high=high)

    def test_a_lasting_small_excess_stays_discreet_without_a_wall_risk(self):
        result = assess(zone(indoor_humidity=60.6), settings=Settings(humidity_high=60), context={"humidity_floor_3h": 60.2})
        self.assertNotIn("dry", result.needs)
        self.assertTrue(result.features["humidity"]["lasting"])

    def test_dry_air_duration_does_not_invent_an_airing_benefit(self):
        result = assess(zone(indoor_humidity=30, outdoor_humidity=None), context={"humidity_ceiling_3h": 35})
        self.assertTrue(result.features["humidity"]["lasting"])
        self.assertIsNone(result.features["humidity"]["reachable"])
        self.assertNotEqual(result.action, "ouvrir")

    def test_the_weathers_own_humidity_is_no_need(self):
        al = assess(zone(indoor_temperature=20.7, indoor_humidity=72.4, **OUT))
        self.assertNotIn("dry", al.needs)
        self.assertEqual((al.action, al.reason, al.level), ("ok", "humid_outdoor", "calm"))
        humidity = al.features["humidity"]
        self.assertEqual((humidity["source"], humidity["reachable"]), ("outside", 72))

    def test_humidity_from_inside_stays_a_need_and_the_walls_are_at_risk(self):
        p = assess(zone(indoor_temperature=20.6, indoor_humidity=85, **OUT))
        self.assertIn("dry", p.needs)
        humidity = p.features["humidity"]
        self.assertEqual((humidity["source"], humidity["mould"]), ("inside", True))
        self.assertGreaterEqual(humidity["surface"], 85)
        self.assertAlmostEqual(humidity["excess"], 2.3, places=1)

    def test_cold_walls_call_for_drying_below_the_comfort_threshold(self):
        # Winter: 60 % in the room looks fine, but the corners of the outer walls sit near 90 %.
        winter = assess(zone(indoor_temperature=20, indoor_humidity=60, outdoor_temperature=-2, outdoor_humidity=80))
        self.assertTrue(winter.features["humidity"]["mould"])
        self.assertIn("dry", winter.needs)
        mild = assess(zone(indoor_temperature=20, indoor_humidity=60, outdoor_temperature=12, outdoor_humidity=80))
        self.assertFalse(mild.features["humidity"]["mould"])
        self.assertNotIn("dry", mild.needs)

    def test_a_passing_peak_is_not_a_mould_risk(self):
        # After a shower the walls are damp for a while: the risk is said only once it has lasted an hour.
        from datetime import datetime, timedelta, timezone
        start = datetime(2026, 10, 20, 21, tzinfo=timezone.utc)
        peak = zone(indoor_temperature=20.6, indoor_humidity=88, **OUT)
        first = assess(peak, now=start)
        self.assertFalse(first.features["humidity"]["mould"])
        self.assertEqual(first.features["humidity"]["damp_since"], start.isoformat())
        later = assess(peak, previous=first, now=start + timedelta(minutes=30))
        self.assertFalse(later.features["humidity"]["mould"])
        hour = assess(peak, previous=later, now=start + timedelta(minutes=61))
        self.assertTrue(hour.features["humidity"]["mould"])
        # Three hours above the threshold already: no wait.
        self.assertTrue(assess(peak, now=start, context={"humidity_floor_3h": 80}).features["humidity"]["mould"])

    def test_a_stopped_ventilation_is_worth_starting_below_the_window_threshold(self):
        # Chambre P, 20 Oct.: 86 %, 1.5 g/m³ above outside, no airing worth it, the room VMC stopped.
        room = zone(indoor_temperature=20.5, indoor_humidity=86, outdoor_temperature=17.8, outdoor_humidity=91, ventilation=False)
        self.assertEqual(assess(room).reason, "ventilation_possible")
        without = zone(indoor_temperature=20.5, indoor_humidity=86, outdoor_temperature=17.8, outdoor_humidity=91)
        self.assertNotEqual(assess(without).reason, "ventilation_possible")

    def test_without_the_outdoor_humidity_the_room_threshold_still_applies(self):
        blind = assess(zone(indoor_humidity=75, outdoor_humidity=None))
        self.assertIn("dry", blind.needs)


if __name__ == "__main__":
    unittest.main()
