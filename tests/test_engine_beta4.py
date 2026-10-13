"""Template rules ported in beta 4: gusts, frost, heating, rain per opening and sun on facades."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Opening, Settings, Sun, assess, facade_irradiance, facade_share
from engine.sources import normalize
from test_engine import zone

NOW = datetime(2026, 10, 13, 15, tzinfo=timezone.utc)


class Beta4Rules(unittest.TestCase):
    def test_gusts_close_open_windows_and_block_closed_ones(self):
        opened = assess(zone(**{"wind_gust": 60, "window:a": True}))
        self.assertEqual((opened.action, opened.reason, opened.level), ("fermer", "gust_open_windows", "urgent"))
        closed = assess(zone(wind_gust=60, indoor_temperature=27, outdoor_temperature=18))
        self.assertEqual((closed.action, closed.reason), ("attendre", "opening_blocked"))
        self.assertIn("gust", closed.constraints)
        self.assertEqual(assess(zone(wind_gust=30)).constraints, ())

    def test_frost_or_heating_still_allow_a_short_airing_for_co2(self):
        for changes in ({"outdoor_temperature": -2}, {"heating": "heating"}):
            with self.subTest(changes=changes):
                result = assess(zone(co2=1400, **changes))
                self.assertEqual((result.action, result.reason), ("ouvrir", "short_air_change"))

    def test_frost_closes_an_open_window_without_need(self):
        result = assess(zone(**{"outdoor_temperature": 0, "window:a": True}))
        self.assertEqual((result.action, result.reason, result.level), ("fermer", "opening_blocked", "action"))
        self.assertIn("frost", result.constraints)

    def test_rain_only_concerns_exposed_openings(self):
        both = zone(**{"rain": True, "window:a": True, "window:b": True})
        sheltered = {"a": Opening(sheltered=True), "b": Opening(sheltered=True)}
        self.assertEqual(assess(both, openings=sheltered).action, "ok")
        mixed = assess(both, openings={"a": Opening(sheltered=True)})
        self.assertEqual((mixed.action, mixed.reason), ("fermer", "rain_open_windows"))
        flags = {d["entity_id"]: d["flags"] for d in mixed.openings}
        self.assertEqual(flags, {"a": [], "b": ["rain_exposed"]})

    def test_rain_never_asks_to_close_a_sheltered_opening(self):
        result = assess(zone(**{"rain": True, "window:a": True, "window:b": False}), openings={"a": Opening(sheltered=True)})
        self.assertEqual((result.action, result.reason), ("attendre", "opening_blocked"))
        self.assertNotIn("rain_exposed", result.openings[0]["flags"])

    def test_all_sheltered_openings_make_rain_irrelevant_even_unmeasured(self):
        result = assess(zone(**{"rain": None, "window:a": False}), openings={"a": Opening(sheltered=True)})
        self.assertNotIn("rain", result.missing)

    def test_sun_share_follows_the_template_formula(self):
        afternoon = Sun(elevation=30, azimuth=250)
        self.assertGreater(facade_share("O", afternoon), facade_share("S", afternoon))
        self.assertEqual(facade_share("E", afternoon), 0)
        self.assertEqual(facade_share(None, afternoon), 0)
        self.assertEqual(facade_share("O", Sun(-5, 250)), 0)
        self.assertIsNone(facade_irradiance(0.8, afternoon, None))
        self.assertEqual(facade_irradiance(0, afternoon, 400), 60)  # diffuse light only

    def test_open_window_in_the_sun_is_where_the_heat_comes_in(self):
        sun = Sun(elevation=30, azimuth=260)
        readings = zone(**{"indoor_temperature": 27, "outdoor_temperature": 29, "solar": 600, "window:a": True, "window:b": False})
        openings = {"a": Opening(exposure="O"), "b": Opening(exposure="E")}
        result = assess(readings, openings=openings, sun=sun)
        by_id = {d["entity_id"]: d for d in result.openings}
        self.assertIn("sun_entering", by_id["a"]["flags"])
        self.assertGreaterEqual(by_id["a"]["sun_wm2"], 250)
        self.assertEqual(by_id["b"]["flags"], [])
        self.assertEqual(result.sun, {"elevation": 30, "azimuth": 260})

    def test_shelter_divides_direct_sun(self):
        sun = Sun(elevation=30, azimuth=260)
        readings = zone(**{"indoor_temperature": 27, "outdoor_temperature": 29, "solar": 600, "window:a": True})
        free = assess(readings, openings={"a": Opening(exposure="O")}, sun=sun).openings[0]["sun_wm2"]
        covered = assess(readings, openings={"a": Opening(exposure="O", sheltered=True)}, sun=sun).openings[0]["sun_wm2"]
        self.assertEqual(covered, round(free / 3))

    def test_wind_and_irradiance_units(self):
        self.assertAlmostEqual(normalize("wind", "10", "m/s", source="s", reported_at=NOW, now=NOW).value, 36)
        self.assertEqual(normalize("wind", "10", "Bft", source="s", reported_at=NOW, now=NOW).detail, "incompatible_unit")
        self.assertEqual(normalize("irradiance", "650", "W/m²", source="s", reported_at=NOW, now=NOW).value, 650)

    def test_new_thresholds_are_validated(self):
        with self.assertRaises(ValueError):
            Settings(gust_max=0)
        with self.assertRaises(ValueError):
            Settings(frost=40)


if __name__ == "__main__":
    unittest.main()
