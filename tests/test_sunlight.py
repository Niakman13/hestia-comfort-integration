"""The sun the station cannot see (engine/sunlight.py): the shade of the house, learned, then estimated.

Frank's station, 21 October 2026: on the east side, it loses three quarters of the sun every sunny afternoon
from 16 h, and the west windows were told there was none."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine import sunlight

GARDANNE = (43.45, 5.47)
DAY = datetime(2026, 10, 12, 5, tzinfo=timezone.utc)


def station(days=8, shade=(220, 250), cloudy=()):
    """A clear-sky station, 1.2 times the model, shaded by the house when the sun is in `shade`."""
    points = []
    for d in range(days):
        t = DAY + timedelta(days=d)
        while t < DAY + timedelta(days=d, hours=13):
            clear = sunlight.clear_sky(t, *GARDANNE) * 1.2
            _, azimuth = sunlight.sun_position(t, *GARDANNE)
            value = clear * (0.25 if shade[0] <= azimuth < shade[1] else 1.0) * (0.2 if d in cloudy else 1.0)
            points.append((t, value))
            t += timedelta(minutes=5)
    return points


class Sunlight(unittest.TestCase):
    def test_the_shade_of_the_house_is_found_and_only_it(self):
        learned = sunlight.learn(station(cloudy=(2, 5)), *GARDANNE)
        self.assertAlmostEqual(learned["scale"], 1.2, delta=0.05)
        self.assertEqual(learned["shaded"], [220, 230, 240])
        self.assertEqual(learned["sunny_days"], 6)
        # A station in the open: nothing shaded, nothing changes.
        self.assertEqual(sunlight.learn(station(shade=(0, 0)), *GARDANNE)["shaded"], [])

    def test_the_hidden_sun_is_estimated_from_the_cloud_cover(self):
        learned = sunlight.learn(station(), *GARDANNE)
        four = datetime(2026, 10, 21, 14, tzinfo=timezone.utc)  # 16 h in Gardanne, the sun at 230°
        clear = sunlight.clear_sky(four, *GARDANNE) * learned["scale"]
        self.assertEqual(sunlight.estimate(60, four, *GARDANNE, learned, sky=1.0), (round(clear, 1), True))
        cloudy = sunlight.sky_factor({"cloud_coverage": 90})
        self.assertLess(sunlight.estimate(60, four, *GARDANNE, learned, sky=cloudy)[0], clear / 2)
        self.assertEqual(sunlight.sky_factor({"condition": "partlycloudy"}), 0.6)
        # No forecast and no measure before the shade: the measure is kept, nothing invented.
        self.assertEqual(sunlight.estimate(60, four, *GARDANNE, learned), (60, False))
        # In the open, the measure is the truth.
        noon = datetime(2026, 10, 21, 10, tzinfo=timezone.utc)
        self.assertEqual(sunlight.estimate(480, noon, *GARDANNE, learned, sky=0.2), (480, False))

    def test_the_twin_learns_from_the_history_set_right(self):
        points = station()
        learned = sunlight.learn(points, *GARDANNE)
        fixed = dict(sunlight.corrected(points, *GARDANNE, learned))
        four = next(t for t, _ in points if t.astimezone(timezone(timedelta(hours=2))).hour == 16 and t.minute == 0)
        self.assertGreater(fixed[four], dict(points)[four] * 3)


class NearestHour(unittest.TestCase):
    def test_the_forecast_that_starts_at_the_next_hour_still_gives_the_sky(self):
        """21 October at 16 h 26: the forecast list began at 17 h, and the shade estimate found no sky."""
        now = datetime(2026, 10, 21, 14, 26, tzinfo=timezone.utc)
        hours = [{"time": "2026-10-21T15:00:00+00:00", "cloud_coverage": 10}, {"time": "2026-10-21T16:00:00+00:00", "cloud_coverage": 80}]
        self.assertEqual(sunlight.nearest_hour(hours, now)["cloud_coverage"], 10)
        self.assertIsNone(sunlight.nearest_hour([{"time": "2026-10-21T19:00:00+00:00"}], now))
        self.assertIsNone(sunlight.nearest_hour([], now))
