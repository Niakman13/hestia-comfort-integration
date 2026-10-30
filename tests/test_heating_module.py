"""The « Chauffage » module (30 October): the heating's power, and how long the room heated over the last day."""
from datetime import datetime, timedelta, timezone
import unittest

from custom_components.hestia_comfort.coordinator import heated_minutes, heating_power
from custom_components.hestia_comfort.recorder_history import Row

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def row(minutes, action):
    at = T0 + timedelta(minutes=minutes)
    return Row(at - timedelta(hours=2), at, "heat", {"hvac_action": action})


class HeatingModuleTest(unittest.TestCase):
    def test_power_from_versatile_thermostat_or_from_the_action(self):
        self.assertEqual(heating_power({"power_percent": 45}), 45.0)
        self.assertEqual(heating_power({"on_percent": 0.3}), 30.0)
        self.assertEqual(heating_power({"hvac_action": "heating"}), 100.0)
        self.assertEqual(heating_power({"hvac_action": "idle"}), 0.0)
        self.assertIsNone(heating_power({}))

    def test_minutes_heated_count_each_heating_stretch_until_the_end(self):
        rows = [row(-30, "idle"), row(0, "heating"), row(40, "idle"), row(100, "heating")]
        # 40 min, then from 100 to 130 (now): 70 min; what was before the window's start counts from its start.
        self.assertEqual(heated_minutes(rows, T0 - timedelta(minutes=10), T0 + timedelta(minutes=130)), 70)
        self.assertEqual(heated_minutes([row(-60, "heating")], T0, T0 + timedelta(minutes=15)), 15)


if __name__ == "__main__":
    unittest.main()
