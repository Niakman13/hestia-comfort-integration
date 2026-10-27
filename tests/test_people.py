"""People per room and the home's alarm: who the room is for, whether they are home, and a window left open when armed."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import people
from engine.assessment import Settings, assess
from engine.sources import Reading

NOW = datetime(2026, 10, 26, 22, tzinfo=timezone.utc)


def run(window=False, ti=21.0, te=12.0, **context):
    values = {"indoor_temperature": ti, "outdoor_temperature": te, "indoor_humidity": 50, "outdoor_humidity": 70,
              "heating": "off", "window:w": window}
    readings = {k: Reading(v, "valid", "sensor.x") for k, v in values.items()}
    return assess(readings, Settings(minimum=20, maximum=24), None, {}, None, {}, NOW, context={"heated": True, **context})


class People(unittest.TestCase):
    def test_a_bedroom_follows_its_person(self):
        paul_away = people.people([("Paul", "not_home")])
        self.assertFalse(people.occupied(paul_away, None, zone_count=2))  # others at home, not Paul
        self.assertTrue(people.occupied(people.people([("Paul", "home")]), None, zone_count=0))

    def test_a_shared_room_is_empty_only_when_all_are_away(self):
        self.assertTrue(people.occupied(people.people([("Paul", "not_home"), ("Marie", "home")]), None))
        self.assertFalse(people.occupied(people.people([("Paul", "not_home"), ("Marie", "Travail")]), None))
        self.assertIsNone(people.occupied(people.people([("Paul", "not_home"), ("Marie", "unavailable")]), None))

    def test_without_people_the_household_counts(self):
        self.assertTrue(people.occupied(None, None, zone_count=1))
        self.assertFalse(people.occupied(None, None, zone_count=0))
        self.assertIsNone(people.occupied(None, None))

    def test_alarm_away_empties_the_home(self):
        away = people.alarm("armed_away")
        self.assertFalse(people.occupied(people.people([("Paul", "home")]), away))
        self.assertTrue(people.occupied(None, people.alarm("disarmed")))
        self.assertTrue(people.alarm("armed_night")["night"])
        self.assertIsNone(people.alarm("unavailable"))


class Advice(unittest.TestCase):
    def test_window_open_alarm_away_is_urgent(self):
        a = run(window=True, alarm=people.alarm("armed_away"), occupied=False)
        self.assertEqual((a.action, a.reason, a.level), ("fermer", "alarm_open", "urgent"))

    def test_window_open_alarm_night_unless_on_purpose(self):
        a = run(window=True, alarm=people.alarm("armed_night"), occupied=True)
        self.assertEqual((a.action, a.reason, a.level), ("fermer", "alarm_open", "action"))
        self.assertNotEqual(run(window=True, alarm=people.alarm("armed_night"), occupied=True, intended_open=True).reason, "alarm_open")

    def test_alarm_home_and_closed_windows_change_nothing(self):
        self.assertNotEqual(run(window=True, alarm=people.alarm("armed_home"), occupied=True).reason, "alarm_open")
        self.assertNotEqual(run(window=False, alarm=people.alarm("armed_away"), occupied=False).reason, "alarm_open")

    def test_window_open_with_the_rooms_people_away_is_said(self):
        found = people.people([("Paul", "not_home")])
        a = run(window=True, people=found, occupied=False)
        self.assertTrue(a.features["household"]["away_open"])
        self.assertEqual(a.features["people"], {"home": [], "away": ["Paul"]})

    def test_the_alarm_reason_is_known_to_the_sensor(self):
        from custom_components.niak_comfort.engine.assessment import REASONS
        self.assertIn("alarm_open", REASONS)


if __name__ == "__main__":
    unittest.main()
