"""A shower in a room that declares one (« Équipements »): its peak is expected, never a mould risk."""
from datetime import timedelta
import unittest
from test_engine import NOW, zone
from engine import habits
from engine.assessment import assess
from engine.shower import episode


def history(*points):
    """(minutes ago, humidity) → the coordinator's (iso time, value) samples."""
    return [((NOW - timedelta(minutes=m)).isoformat(), v) for m, v in points]


class ShowerTests(unittest.TestCase):
    def test_a_fast_rise_is_a_shower_in_a_room_that_has_one(self):
        rise = history((30, 58), (25, 60), (18, 74), (10, 80), (0, 76))
        found = episode(rise, NOW, True)
        self.assertEqual((found["minutes"], found["base"], found["peak"]), (30, 58, 80))
        # Never guessed in a room without a shower.
        self.assertIsNone(episode(rise, NOW, False))

    def test_a_slow_rise_or_a_finished_shower_is_not_one(self):
        self.assertIsNone(episode(history((90, 55), (60, 60), (30, 65), (0, 70)), NOW, True))
        # Back near where it started: over.
        self.assertIsNone(episode(history((40, 58), (30, 75), (0, 59)), NOW, True))
        # More than an hour ago.
        self.assertIsNone(episode(history((75, 58), (70, 75), (0, 70)), NOW, True))

    def test_the_peak_starts_no_mould_risk(self):
        # Cold walls, damp air: without a shower the damp is counted from now.
        readings = zone(indoor_temperature=19, indoor_humidity=85, outdoor_temperature=2, outdoor_humidity=80)
        rise = history((20, 60), (15, 78), (0, 85))
        plain = assess(readings, now=NOW, context={"humidity_history": rise}).features["humidity"]
        shower = assess(readings, now=NOW, context={"humidity_history": rise, "equipment": ["shower"]}).features["humidity"]
        self.assertIsNotNone(plain["damp_since"])
        self.assertIsNone(shower["damp_since"])
        self.assertFalse(shower["mould"])
        self.assertEqual(shower["shower"]["minutes"], 20)
        self.assertIsNone(plain["shower"])

    def test_the_shower_is_the_cause_asked_about(self):
        self.assertIsNone(habits.cause("Chambre P"))
        self.assertEqual(habits.cause("Chambre P", None, ["shower"]), "la douche")
        found = [{"key": "humidity:all:7", "kind": "humidity", "days": "all", "hour": 7, "share": 0.8}]
        self.assertIn("la douche", habits.questions("Chambre P", None, found, {}, equipment=["shower"])[0]["text"])


if __name__ == "__main__":
    unittest.main()
