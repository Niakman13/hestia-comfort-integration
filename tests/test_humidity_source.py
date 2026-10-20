"""Humidity judged on what airing can gain, and mould judged on the cold walls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import assess
from test_engine import zone

# 20 Oct., 13 h 50: 16.9 °C and 90 % outdoors, 12.9 g/m³ of water; no room can be aired below about 71 %.
OUT = dict(outdoor_temperature=16.9, outdoor_humidity=90)


class HumiditySource(unittest.TestCase):
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

    def test_without_the_outdoor_humidity_the_room_threshold_still_applies(self):
        blind = assess(zone(indoor_humidity=75, outdoor_humidity=None))
        self.assertIn("dry", blind.needs)


if __name__ == "__main__":
    unittest.main()
