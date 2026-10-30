"""The room's range follows its Versatile Thermostat: the set point stands as the minimum, the season moves the maximum."""
import unittest

from custom_components.hestia_comfort.engine.assessment import Reading, Settings, assess

ROOM = Settings(minimum=18, maximum=25, summer_maximum=26)


def season(thermostat, follow=True):
    readings = {"indoor_temperature": Reading(20.0, "valid")}
    result = assess(readings, ROOM, context={"thermostat": thermostat, "thermostat_reference": follow, "season_name": "winter"})
    s = result.features["season"]
    return s["minimum"], s["maximum"]


class ThermostatRangeTest(unittest.TestCase):
    def test_comfort_at_19_makes_the_range_19_to_25(self):
        self.assertEqual(season({"preset": "comfort", "target": 19.0, "comfort": 19.0}), (19.0, 25))

    def test_the_saved_range_stays_when_the_thermostat_is_not_followed(self):
        self.assertEqual(season({"preset": "comfort", "target": 19.0, "comfort": 19.0}, follow=False), (18, 25))

    def test_frost_protection_counts_the_comfort_temperature_not_the_frost_one(self):
        self.assertEqual(season({"preset": "frost", "target": 14.0, "comfort": 20.0}), (20.0, 25))


if __name__ == "__main__":
    unittest.main()
