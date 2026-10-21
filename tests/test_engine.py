"""Behavioral checks on the production engine, without Home Assistant."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Settings, assess
from engine.sources import Reading, normalize

NOW = datetime(2026, 10, 11, 18, tzinfo=timezone.utc)


def zone(**changes):
    values = {"indoor_temperature": 22, "outdoor_temperature": 19,
              "indoor_humidity": 50, "outdoor_humidity": 55, "co2": 700,
              "rain": False, "pollution": False, "window:a": False}
    values.update(changes)
    return {k: Reading(v, "unknown" if v is None else "valid", "sensor.test") for k, v in values.items()}


class EngineTests(unittest.TestCase):
    def test_five_levels(self):
        cases = [({}, "calm"), ({"co2": 1050}, "benefit"), ({"indoor_temperature": 27}, "action"),
                 ({"co2": 1700}, "urgent"), ({"co2": None}, "neutral")]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assertEqual(assess(zone(**changes)).level, expected)

    def test_simultaneous_needs_are_kept(self):
        result = assess(zone(indoor_temperature=28, indoor_humidity=75, co2=1800))
        self.assertEqual(result.needs, ("air", "cool", "dry"))
        self.assertEqual(result.level, "urgent")

    def test_airing_does_not_resolve_measured_air(self):
        result = assess(zone(**{"co2": 1800, "window:a": True}))
        self.assertEqual((result.action, result.level), ("ok", "urgent"))
        self.assertIn("air", result.needs)

    def test_rain_with_open_window(self):
        result = assess(zone(**{"rain": True, "window:a": True}))
        self.assertEqual((result.action, result.level, result.reason), ("fermer", "urgent", "rain_open_windows"))

    def test_rain_does_not_erase_air(self):
        result = assess(zone(co2=1800, rain=True))
        self.assertEqual((result.action, result.level), ("attendre", "urgent"))
        self.assertIn("air", result.needs)

    def test_closed_windows_without_need_do_not_make_rain_an_alarm(self):
        self.assertEqual(assess(zone(rain=True)).level, "calm")

    def test_unknown_exterior_keeps_known_need(self):
        result = assess(zone(co2=1800, outdoor_temperature=None))
        self.assertEqual((result.action, result.level), ("unknown", "urgent"))

    def test_unconfigured_protections_are_named_but_do_not_block(self):
        values = zone(indoor_temperature=28)
        values.pop("rain")
        values.pop("pollution")
        result = assess(values)
        self.assertEqual((result.action, result.level), ("ouvrir", "action"))
        self.assertEqual(result.unverified, ("pollution", "rain"))
        self.assertFalse(result.partial)

    def test_a_configured_protection_that_does_not_answer_still_blocks(self):
        result = assess(zone(indoor_temperature=28, rain=None))
        self.assertEqual(result.action, "unknown")
        self.assertIn("rain", result.missing)

    def test_missing_contacts_never_claim_closed(self):
        values = zone(rain=True)
        values.pop("window:a")
        self.assertEqual(assess(values).level, "neutral")

    def test_humidity_uses_absolute_water(self):
        self.assertIn("dry", assess(zone(indoor_humidity=75, outdoor_humidity=80, outdoor_temperature=5)).opportunities)
        self.assertNotIn("dry", assess(zone(indoor_humidity=75, outdoor_humidity=50, outdoor_temperature=35)).opportunities)

    def test_co2_absent_is_not_600(self):
        result = assess(zone(co2=None))
        self.assertNotIn("air", result.needs)
        self.assertTrue(result.partial)
        self.assertEqual(result.level, "neutral")

    def test_temperature_hysteresis_and_restart(self):
        first = assess(zone(indoor_temperature=25))
        held = assess(zone(indoor_temperature=23.8), previous=first)
        self.assertIn("cool", held.needs)
        self.assertNotIn("cool", assess(zone(indoor_temperature=23.4), previous=held).needs)
        self.assertNotIn("cool", assess(zone(indoor_temperature=23.8)).needs)

    def test_missing_value_clears_old_need_without_claiming_resolution(self):
        first = assess(zone(co2=1700))
        result = assess(zone(co2=None), previous=first)
        self.assertEqual(result.level, "neutral")
        self.assertTrue(result.partial)

    def test_co2_hysteresis(self):
        first = assess(zone(co2=1250))
        self.assertIn("air", assess(zone(co2=1150), previous=first).needs)
        self.assertNotIn("air", assess(zone(co2=1090), previous=first).needs)

    def test_no_heating_pause_claimed(self):
        result = assess(zone(co2=1700, heating="heating"))
        self.assertEqual(result.heating_action, "heating")
        self.assertEqual(result.coordination, "not_connected")

    def test_custom_thresholds(self):
        self.assertIn("cool", assess(zone(indoor_temperature=23), Settings(minimum=18, maximum=22)).needs)

    def test_protect_comfort_before_overheating(self):
        result = assess(zone(**{"indoor_temperature": 22, "outdoor_temperature": 35, "window:a": True}))
        self.assertEqual((result.action, result.level), ("fermer", "action"))

    def test_partial_contact_does_not_hide_known_open_window(self):
        result = assess(zone(**{"rain": True, "window:a": None, "window:b": True}))
        self.assertEqual((result.action, result.level), ("fermer", "urgent"))
        self.assertTrue(result.partial)


class SourceTests(unittest.TestCase):
    def read(self, kind, value, unit=None, **kwargs):
        return normalize(kind, value, unit, source="sensor.test", reported_at=kwargs.pop("reported_at", NOW), now=NOW, **kwargs)

    def test_fahrenheit_and_kelvin(self):
        self.assertAlmostEqual(self.read("temperature", 68, "°F").value, 20)
        self.assertAlmostEqual(self.read("temperature", 293.15, "K").value, 20)

    def test_non_finite_values_and_units(self):
        for v in ("nan", "inf", "-inf", True, "unavailable", "bad"):
            self.assertIsNone(self.read("temperature", v, "°C").value)
        self.assertIsNone(self.read("co2", 1200, "µg/m³").value)

    def test_ranges(self):
        self.assertIsNone(self.read("humidity", 101, "%").value)
        self.assertIsNone(self.read("humidity", -1, "%").value)

    def test_expiry_and_future(self):
        self.assertEqual(self.read("co2", 1700, "ppm", reported_at=NOW-timedelta(hours=1)).quality, "stale")
        self.assertEqual(self.read("co2", 1700, "ppm", reported_at=NOW+timedelta(hours=1)).quality, "unknown")

    def test_contact_unknown_is_not_closed(self):
        self.assertIsNone(self.read("window", "unavailable").value)
        self.assertFalse(self.read("window", "off").value)
        self.assertTrue(self.read("window", "on").value)

    def test_hvac_mode_not_action(self):
        self.assertIsNone(self.read("heating", "heat").value)
        self.assertEqual(self.read("heating", "idle").value, "idle")

    def test_settings_reject_invalid_values(self):
        for kwargs in ({"minimum": 30, "maximum": 20}, {"co2_action": 1700}, {"max_age_seconds": -1},
                       {"minimum": float("nan")}, {"temperature_hysteresis": 5}, {"co2_hysteresis": 300}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Settings(**kwargs)


if __name__ == "__main__":
    unittest.main()


class SunBenefits(unittest.TestCase):
    """Chambre A, 21 October at 15 h: south window in the sun, 19.5 °C inside, 17.5 °C outside."""
    def assess(self, ti, te, opened=False, solar=430):
        from engine.assessment import Opening, Sun
        readings = zone(indoor_temperature=ti, outdoor_temperature=te, indoor_humidity=55, outdoor_humidity=60, solar=solar, **{"window:a": opened})
        return assess(readings, Settings(minimum=19, maximum=25), None, {"a": Opening(exposure="S")}, Sun(30.6, 210.7), None, NOW).to_dict()

    def test_the_sun_that_warms_a_cool_room_is_said(self):
        found = self.assess(19.5, 17.5)["features"]["benefits"]
        self.assertEqual([(b["kind"], b["keep_shut"]) for b in found], [("sun_warms", True)])

    def test_no_sun_no_shade_nothing_said(self):
        self.assertEqual(self.assess(19.5, 17.5, solar=40)["features"]["benefits"], [])
        self.assertEqual(self.assess(22.5, 17.5)["features"]["benefits"], [])

    def test_lowering_the_shutter_only_when_the_heat_is_too_much(self):
        # Mid-season, 24.2 °C, cooler outside: the warmth is kept for the night.
        self.assertEqual(self.assess(24.2, 17.5)["features"]["benefits"], [])
        self.assertEqual([b["kind"] for b in self.assess(24.2, 27.0)["features"]["benefits"]], ["sun_heats"])
        self.assertEqual([b["kind"] for b in self.assess(26.0, 22.0)["features"]["benefits"]], ["sun_heats"])
