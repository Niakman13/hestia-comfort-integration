"""Bloc 5: wind against the openings, Niak Weather signals and the next hours."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Opening, Sun, assess
from engine.wind import crossing, open_first, side
from engine.outlook import rain_soon, slot
from test_engine import zone

NOW = datetime(2026, 10, 14, 15, tzinfo=timezone.utc)


class WindSides(unittest.TestCase):
    def test_windward_leeward_and_side(self):
        self.assertEqual(side("O", 270), "windward")      # west wind on a west facade
        self.assertEqual(side("E", 270), "leeward")
        self.assertEqual(side("N", 270), "side")
        self.assertEqual(side("SO", 250), "windward")      # 25° from the facade
        self.assertEqual(side("SO", 300), "side")          # 75°: the wind slides along the facade
        self.assertIsNone(side(None, 270))
        self.assertIsNone(side("O", None))

    def test_crossing_and_what_to_open(self):
        o = lambda e, opened, exp, s, kind="window", flags=(): {"entity_id": e, "open": opened, "exposure": exp, "wind_side": s, "kind": kind, "flags": list(flags)}
        self.assertEqual(crossing([o("a", True, "O", "windward"), o("b", True, "E", "leeward")]), "wind")
        self.assertEqual(crossing([o("a", True, "N", None), o("b", True, "S", None)]), "opposite")
        self.assertEqual(crossing([o("a", True, "O", "windward")]), "one_side")
        self.assertIsNone(crossing([o("a", False, "O", "windward")]))
        rooms = [o("w", False, "O", "windward"), o("big", False, "O", "windward", "french"), o("l", False, "E", "leeward")]
        self.assertEqual(open_first(rooms), ["big", "l"])
        self.assertEqual(open_first([o("a", False, "N", "side"), o("b", False, "S", "side")]), ["a", "b"])


class WindRules(unittest.TestCase):
    def test_wind_driven_rain_reaches_a_sheltered_windward_opening_only(self):
        readings = zone(**{"rain": True, "wind_gust": 35, "wind_bearing": 270, "window:o": True, "window:e": True})
        openings = {"o": Opening(exposure="O", sheltered=True), "e": Opening(exposure="E", sheltered=True)}
        result = assess(readings, openings=openings)
        flags = {d["entity_id"]: d["flags"] for d in result.openings}
        self.assertEqual(flags["o"], ["rain_exposed"])
        self.assertEqual(flags["e"], [])
        self.assertEqual(result.reason, "rain_open_windows")
        calm = assess(zone(**{"rain": True, "wind_gust": 10, "wind_bearing": 270, "window:o": True}), openings={"o": Opening(exposure="O", sheltered=True)})
        self.assertNotEqual(calm.reason, "rain_open_windows")

    def test_open_first_into_and_out_of_the_wind(self):
        readings = zone(**{"indoor_temperature": 27, "outdoor_temperature": 19, "wind_bearing": 270, "window:o": False, "window:e": False, "window:n": False})
        openings = {"o": Opening(exposure="O"), "e": Opening(exposure="E"), "n": Opening(exposure="N")}
        result = assess(readings, openings=openings)
        self.assertEqual(result.action, "ouvrir")
        self.assertEqual(result.open_first, ("o", "e"))
        self.assertEqual(result.wind_bearing, 270)


class WeatherSignals(unittest.TestCase):
    def test_storm_closes_and_vigilance_blocks(self):
        storm = assess(zone(**{"window:a": True}), outlook={"storm": True})
        self.assertEqual((storm.action, storm.level), ("fermer", "urgent"))
        self.assertIn("storm", storm.constraints)
        orange = assess(zone(indoor_temperature=27, outdoor_temperature=18), outlook={"vigilance": 2})
        self.assertEqual((orange.action, orange.reason), ("attendre", "opening_blocked"))
        yellow = assess(zone(indoor_temperature=27, outdoor_temperature=18), outlook={"vigilance": 1})
        self.assertEqual(yellow.action, "ouvrir")

    def test_rain_coming_closes_exposed_openings_only(self):
        soon = assess(zone(**{"window:a": True}), outlook={"rain_in_hours": 0.5})
        self.assertEqual((soon.action, soon.reason, soon.rain_soon_minutes), ("fermer", "rain_soon", 30))
        sheltered = assess(zone(**{"window:a": True}), openings={"a": Opening(sheltered=True)}, outlook={"rain_in_hours": 0.5})
        self.assertNotEqual(sheltered.reason, "rain_soon")
        far = assess(zone(**{"window:a": True}), outlook={"rain_in_hours": 3})
        self.assertIsNone(far.rain_soon_minutes)
        self.assertEqual(rain_soon(0.25), 15)

    def test_precool_at_night_before_a_hot_day(self):
        readings = zone(indoor_temperature=23, outdoor_temperature=17)
        result = assess(readings, sun=Sun(-10, 300), outlook={"tomorrow_max": 31})
        self.assertIn("precool", result.needs)
        self.assertEqual((result.action, result.reason), ("ouvrir", "precool_possible"))
        self.assertEqual(result.level, "benefit")
        day = assess(readings, sun=Sun(30, 200), outlook={"tomorrow_max": 31})
        self.assertNotIn("precool", day.needs)
        still_hot = assess(zone(indoor_temperature=23, outdoor_temperature=26), sun=Sun(-10, 300), outlook={"tomorrow_max": 31})
        self.assertEqual((still_hot.action, still_hot.reason, still_hot.level), ("attendre", "precool_later", "benefit"))


class NextHours(unittest.TestCase):
    def hours(self, temps):
        return [{"time": (NOW + timedelta(hours=i + 1)).isoformat(), "temperature": t, "wind_bearing": 270} for i, t in enumerate(temps)]

    def test_opening_slot_when_outside_becomes_fresh(self):
        found = slot(self.hours([29, 27, 24, 21]), NOW, 26, hot=True, cool_now=False, margin=1.5)
        self.assertEqual((found["kind"], found["temperature"], found["wind_bearing"]), ("open", 24, 270))
        self.assertEqual(found["time"], (NOW + timedelta(hours=3)).isoformat())

    def test_closing_slot_when_outside_warms_again(self):
        found = slot(self.hours([22, 24, 27]), NOW, 25, hot=True, cool_now=True, margin=1.5)
        self.assertEqual((found["kind"], found["temperature"]), ("close", 27))

    def test_no_slot_without_need_or_forecast(self):
        self.assertIsNone(slot(self.hours([20]), NOW, 22, hot=False, cool_now=False, margin=1.5))
        self.assertIsNone(slot([], NOW, 26, hot=True, cool_now=False, margin=1.5))

    def test_assessment_carries_the_slot(self):
        result = assess(zone(indoor_temperature=27, outdoor_temperature=29), outlook={"hours": self.hours([28, 24])}, now=NOW)
        self.assertEqual(result.slot["kind"], "open")


if __name__ == "__main__":
    unittest.main()
