"""Tonight simulated (after NADIR): open when the outside is cooler, keep shut under the sun, store coolness for tomorrow."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine import night

NOW = datetime(2026, 7, 10, 16, tzinfo=timezone.utc)
# A heavy room: inertia of 40 h, walls following the air (z), open windows that renew the air well.
MODEL = {"thermal": {"a": 0.5 / 40, "b": 0.3, "c": 0.0, "d": 0.4, "e": 0.02, "f": 0.0, "x": 0.0, "z": 0.1},
         "water": {"n": 0.15, "m": 0.3, "g": 0.0, "k": 0.0, "y": 0.0}}


def heatwave(hours=34, rain_at=None, humidity=50):
    """A hot day: 33 °C at 16 h, 19 °C at 5 h, then hot again."""
    out = []
    for i in range(hours):
        t = NOW + timedelta(hours=i)
        te = 26 + 7 * math.cos((t.hour - 16) / 24 * 2 * math.pi)
        out.append({"time": t.isoformat(), "temperature": round(te, 1), "humidity": humidity,
                    "precipitation": 2.0 if rain_at is not None and i in rain_at else 0.0, "cloud_coverage": 0})
    return out


def afternoon_sun(when, hour):
    return 0.5 if 9 <= when.hour <= 17 else 0.0


class Night(unittest.TestCase):
    def test_opens_in_the_night_and_saves_tomorrows_heat(self):
        p = night.plan(MODEL, {"ti": 27, "hi": 50}, heatwave(), NOW, minimum=20, mass=27, sun=afternoon_sun)
        first = datetime.fromisoformat(p["windows"][0]["start"])
        self.assertTrue(first.hour >= 19 or first.hour <= 2, first)
        self.assertTrue(p["worth"])
        self.assertGreater(p["peak"]["shut"], p["peak"]["aired"])
        self.assertLess(p["minimum"]["temperature"], 27)
        self.assertFalse(p["humid"])

    def test_the_sun_holds_the_opening_back(self):
        # 27 °C inside, 25 °C outside at 9 h under a strong sun: the sun the open window lets in costs more.
        morning = NOW.replace(hour=9)
        hours = [{"time": (morning + timedelta(hours=i)).isoformat(), "temperature": 25.0, "humidity": 50, "precipitation": 0}
                 for i in range(6)]
        sunny = night.plan(MODEL, {"ti": 27, "hi": 50}, hours, morning, minimum=20, sun=lambda w, h: 0.8)
        cloudy = night.plan(MODEL, {"ti": 27, "hi": 50}, hours, morning, minimum=20, sun=lambda w, h: 0.0)
        # Without sun, 2 °C cooler outside is worth opening at once; under the sun, only once the shut room has warmed
        # enough for the air to make up for the sun the raised shutters let in.
        self.assertEqual(cloudy["windows"][0]["start"], morning.isoformat())
        self.assertGreater(sunny["windows"][0]["start"], morning.isoformat())

    def test_never_under_rain_nor_below_the_minimum(self):
        p = night.plan(MODEL, {"ti": 27, "hi": 50}, heatwave(rain_at=range(0, 34)), NOW, minimum=20)
        self.assertEqual(p["windows"], [])
        # A cool room is aired at night only down to its minimum.
        cool = night.plan(MODEL, {"ti": 21, "hi": 50}, heatwave(), NOW, minimum=21)
        self.assertGreaterEqual(cool["minimum"]["temperature"], 20.6)

    def test_damp_night_is_said(self):
        p = night.plan(MODEL, {"ti": 27, "hi": 50}, heatwave(humidity=95), NOW, minimum=20)
        self.assertTrue(p["humid"])

    def test_nothing_without_forecast_or_measure(self):
        self.assertIsNone(night.plan(MODEL, {"ti": 27, "hi": 50}, [], NOW, minimum=20))
        self.assertIsNone(night.plan(MODEL, {"ti": None, "hi": 50}, heatwave(), NOW, minimum=20))

    def test_ordinary_room_while_learning(self):
        p = night.plan(None, {"ti": 27, "hi": 50}, heatwave(), NOW, minimum=20)
        self.assertTrue(p["windows"])

    def test_dew_point(self):
        self.assertAlmostEqual(night.dew_point(20, 50), 9.3, delta=0.1)


if __name__ == "__main__":
    unittest.main()
