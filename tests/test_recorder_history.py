"""Ten days of a chatty sensor are not held in memory (issue #41): the history is read compacted."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.recorder_history import compact

START = datetime(2026, 10, 20, tzinfo=timezone.utc)


def state(value, seconds, attributes=None):
    when = START + timedelta(seconds=seconds)
    return SimpleNamespace(state=value, last_changed=when, last_updated=when, attributes=attributes or {})


class Compact(unittest.TestCase):
    def test_a_sensor_every_ten_seconds_keeps_one_value_a_minute_and_its_last(self):
        rows = compact([state(str(20 + i / 100), i * 10) for i in range(8640)])  # one day
        self.assertLess(len(rows), 1500)
        self.assertEqual(rows[0].state, "20.0")
        self.assertEqual(rows[-1].state, str(20 + 8639 / 100))
        self.assertTrue(all(b.last_changed - a.last_changed >= timedelta(seconds=60) for a, b in zip(rows, rows[1:-1])))

    def test_a_co2_falling_in_bursts_while_a_window_is_open_keeps_its_whole_fall(self):
        # Every 5 s for two minutes, from 1200 ppm down by 2 % a step: what the airing model reads.
        values = [1200 * 0.98 ** i for i in range(24)]
        rows = compact([state(str(v), i * 5) for i, v in enumerate(values)])
        self.assertEqual(len(rows), 24)

    def test_every_change_of_a_contact_is_kept(self):
        rows = compact([state("off", 0), state("on", 5), state("on", 8), state("off", 12), state("unavailable", 13)])
        self.assertEqual([r.state for r in rows], ["off", "on", "off", "unavailable"])

    def test_a_thermostat_keeps_the_moments_its_action_changes(self):
        rows = compact([state("heat", i * 10, {"hvac_action": "heating" if 20 <= i < 50 else "idle", "temperature": i})
                        for i in range(100)], attribute="hvac_action")
        self.assertEqual([r.attributes for r in rows][:3], [{"hvac_action": "idle"}, {"hvac_action": "heating"}, {"hvac_action": "idle"}])

    def test_slices_follow_each_other(self):
        first = compact([state("20", 0), state("20.1", 30)])
        second = compact([state("20.2", 40), state("20.3", 120)], previous=first[-1])
        self.assertEqual([r.state for r in second], ["20.3"])


if __name__ == "__main__":
    unittest.main()
