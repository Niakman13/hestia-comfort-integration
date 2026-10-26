"""« Prochaines heures »: the subject follows the advice, and each drawing says what the gesture changes."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine import horizon

MODEL = {"thermal": {"a": 0.5 / 40, "b": 0.35, "c": 0.22, "d": 0.25, "e": 0.015, "f": 0.0, "x": 0.0, "z": 0.1},
         "water": {"n": 0.04, "m": 0.6, "g": 0.09, "k": 0.0, "y": 0.0}}


def forecast(now, mean, amp, humidity=lambda h: 70, hours=32):
    out = []
    for i in range(hours):
        t = now + timedelta(hours=i)
        out.append({"time": t.isoformat(), "temperature": round(mean + amp * math.cos((t.hour - 15) / 24 * 2 * math.pi), 1),
                    "humidity": humidity(t.hour), "precipitation": 0, "cloud_coverage": 0})
    return out


def sun(when, hour):
    return 0.5 * max(0.0, math.cos((when.hour - 13) / 5 * math.pi / 2)) if abs(when.hour - 13) < 5 else 0.0


class Horizon(unittest.TestCase):
    def test_a_hot_room_compares_shut_and_aired(self):
        now = datetime(2026, 7, 14, 18, tzinfo=timezone(timedelta(hours=2)))
        out = horizon.build({"reason": "cooling_unavailable", "action": "attendre", "needs": ["cool"], "features": {}},
                            MODEL, {"ti": 27.5, "hi": 50, "te": 31}, forecast(now, 26, 7), now, minimum=20, mass=27.5, sun=sun)
        self.assertEqual(out[0]["kind"], "cool")
        self.assertTrue(out[0]["bands"])
        self.assertGreater(out[0]["result"]["gain"], 0)
        self.assertEqual(len(out[0]["base"]), len(out[0]["gesture"]))

    def test_a_winter_airing_says_its_cost_and_when_it_is_back(self):
        now = datetime(2026, 1, 20, 14, tzinfo=timezone(timedelta(hours=1)))
        out = horizon.build({"reason": "air_needed", "action": "ouvrir", "needs": ["air"], "features": {}},
                            MODEL, {"ti": 20.2, "hi": 50, "te": 5, "holding": True}, forecast(now, 4, 4), now, minimum=19, sun=sun)
        a = out[0]
        self.assertEqual(a["kind"], "air")
        self.assertGreater(a["result"]["drop"], 0.2)
        self.assertIsNotNone(a["result"]["back"])

    def test_the_sun_warming_a_cool_room_is_drawn_without_a_gesture(self):
        now = datetime(2026, 4, 10, 8, tzinfo=timezone(timedelta(hours=2)))
        out = horizon.build({"reason": "heat_needed", "action": "ok", "needs": ["heat"], "features": {"warmth": {"warming": True}}},
                            MODEL, {"ti": 19.0, "hi": 55, "te": 8}, forecast(now, 11, 5), now, minimum=19, sun=sun)
        self.assertEqual((out[0]["kind"], out[0]["gesture"]), ("sun", None))
        self.assertGreater(out[0]["result"]["top"], 19.3)

    def test_drying_comes_first_and_lowers_the_humidity(self):
        now = datetime(2026, 10, 26, 15, tzinfo=timezone(timedelta(hours=1)))
        a = {"reason": "drying_possible", "action": "ouvrir", "needs": ["dry", "heat"],
             "features": {"drying": {"minutes": 20}, "warmth": {"warming": True}}}
        out = horizon.build(a, MODEL, {"ti": 20.5, "hi": 72, "te": 15}, forecast(now, 12, 5, humidity=lambda h: 55), now,
                            minimum=19, sun=sun)
        self.assertEqual(out[0]["subject"], "humidity")
        self.assertLess(out[0]["result"]["with"], out[0]["result"]["without"])
        self.assertLessEqual(len(out), 2)

    def test_nothing_without_forecast_or_measure(self):
        now = datetime(2026, 7, 14, 18, tzinfo=timezone.utc)
        self.assertEqual(horizon.build({"reason": "cooling_possible", "needs": ["cool"]}, MODEL, {"ti": 27, "hi": 50}, [], now, minimum=20), [])
        self.assertEqual(horizon.build({"reason": "cooling_possible"}, MODEL, {"ti": None, "hi": 50}, forecast(now, 26, 7), now, minimum=20), [])


if __name__ == "__main__":
    unittest.main()
