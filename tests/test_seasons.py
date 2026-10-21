"""The advice follows the home's season (Niak Weather's, or a season sensor): not the same in summer and winter.

Born on 21 October 2026: « Aérez vers 3 h », a window left open at night told it was fine whatever the weather,
and one set of rules for the whole year."""
from datetime import datetime, timezone
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.assessment import Opening, Settings, Sun, absolute_humidity, assess, seasonal
from engine.sources import Reading

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
SETTINGS = Settings(minimum=19, maximum=24, summer_maximum=26, humidity_high=60)


def room(ti, te, hi=55, he=60, opened=False, solar=0, season=None, model=None):
    values = {"indoor_temperature": ti, "outdoor_temperature": te, "indoor_humidity": hi, "outdoor_humidity": he,
              "rain": False, "pollution": False, "wind_gust": 10, "solar": solar, "window:w": opened}
    context = {"season_name": season, "heated": True, **({"drying_model": model} if model else {})}
    return assess({k: Reading(v, "valid", "s") for k, v in values.items()}, SETTINGS, None, {"w": Opening(exposure="S")},
                  Sun(30, 180), {"station": ("rain_rate", "wind_gust")}, NOW, context=context).to_dict()


class Seasons(unittest.TestCase):
    def test_the_range_follows_the_season(self):
        self.assertEqual(seasonal(SETTINGS, 25.0, "winter")[0].maximum, 24)
        self.assertEqual(seasonal(SETTINGS, 5.0, "summer")[0].maximum, 26)
        self.assertEqual(seasonal(SETTINGS, None, "autumn")[0].maximum, 25)
        # No season known: the last week's outdoor mean, as before.
        self.assertEqual(seasonal(SETTINGS, 20.0)[1]["weight"], 1.0)

    def test_a_hot_room_is_not_cooled_by_opening_in_winter(self):
        self.assertEqual(room(25.5, 10, season="autumn")["action"], "ouvrir")
        winter = room(25.5, 10, season="winter")
        self.assertNotEqual(winter["action"], "ouvrir")
        self.assertIn("cool", winter["needs"])

    def test_a_winter_airing_is_short(self):
        # 20 °C at 68 %, 5 °C outside: a damp room, a dry winter air.
        winter = room(20, 5, hi=68, he=80, season="winter")
        self.assertEqual((winter["action"], winter["reason"]), ("ouvrir", "drying_possible"))
        self.assertEqual(winter["features"]["ventilation"]["duration_minutes"], {"min": 5, "max": 10})
        self.assertEqual(winter["features"]["drying"]["minutes"], 10)
        self.assertGreater(room(20, 5, hi=68, he=80, season="autumn")["features"]["drying"]["minutes"], 10)

    def test_the_sun_by_season(self):
        kinds = lambda r: [b["kind"] for b in r["features"]["benefits"]]
        # 22.5 °C, above the middle of the range: welcome in winter, not sought in between seasons.
        self.assertEqual(kinds(room(22.5, 8, solar=600, season="winter")), ["sun_warms"])
        self.assertEqual(kinds(room(22.5, 8, solar=600, season="autumn")), [])
        # Summer: never sought, kept out as soon as the room nears its top, even with a cooler outside.
        self.assertEqual(kinds(room(19.5, 15, solar=600, season="summer")), [])
        self.assertEqual(kinds(room(25.2, 22, solar=600, season="summer")), ["sun_heats"])
        self.assertEqual(kinds(room(23.2, 8, solar=600, season="winter")), ["sun_warms"])

    def test_every_situation_follows_its_season(self):
        broken = {}
        for season, ti, te, hi, opened, solar in itertools.product(("summer", "autumn", "winter", None), (18.5, 21.5, 25.5),
                                                                    (2, 12, 18, 28), (50, 70), (False, True), (0, 600)):
            a = room(ti, te, hi=hi, he=80, opened=opened, solar=solar, season=season)
            kinds = [b["kind"] for b in a["features"]["benefits"]]
            case = (season, ti, te, hi, opened, solar)
            if season == "winter" and a["reason"] in ("cooling_possible", "precool_possible"):
                broken.setdefault("never open to cool in winter", case)
            if season == "summer" and "sun_warms" in kinds:
                broken.setdefault("the sun is not sought in summer", case)
            if season == "winter" and "sun_heats" in kinds:
                broken.setdefault("the sun is not kept out in winter", case)
            span = (a["features"].get("ventilation") or {}).get("duration_minutes")
            if season == "winter" and a["reason"] == "drying_possible" and span and span["max"] > 10:
                broken.setdefault("a winter airing is short", case)
        self.assertEqual(broken, {})


if __name__ == "__main__":
    unittest.main()


class SteadySun(unittest.TestCase):
    def test_a_passing_cloud_does_not_make_the_sun_come_and_go(self):
        """21 October at 12 h 44: the station falls to 78 W/m² for one minute between 470 and 500."""
        try:
            from custom_components.niak_comfort.coordinator import ComfortCoordinator
        except ImportError:
            self.skipTest("Home Assistant is not installed")
        from collections import deque
        from datetime import timedelta
        room = ComfortCoordinator.__new__(ComfortCoordinator)
        room._sun_samples = deque(maxlen=120)
        t = NOW
        for value in (470, 480, 500, 490, 78, 495, 488):
            seen = room._steady_sun(Reading(value, "valid", "sensor.solar"), t)
            t += timedelta(minutes=1)
        self.assertGreater(seen.value, 250)
        # A quarter of an hour later, the old ones are forgotten.
        for _ in range(16):
            seen = room._steady_sun(Reading(90, "valid", "sensor.solar"), t)
            t += timedelta(minutes=1)
        self.assertEqual(seen.value, 90)
        self.assertEqual(room._steady_sun(Reading(None, "unknown", "sensor.solar"), t).value, None)
