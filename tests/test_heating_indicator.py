"""The heating indicator: the words it understands, and what discovery offers for it."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.hestia_comfort.discovery import suggestions
from custom_components.hestia_comfort.engine.sources import indicator_state


class IndicatorWords(unittest.TestCase):
    def test_running_and_resting_words(self):
        for word in ("on", "heating", "open", "Open", True):
            self.assertEqual(indicator_state(word), "heating", word)
        for word in ("off", "idle", "close", "closed", False):
            self.assertEqual(indicator_state(word), "idle", word)

    def test_anything_else_is_never_guessed(self):
        for word in (None, "unknown", "unavailable", "", "42", "auto"):
            self.assertIsNone(indicator_state(word), word)

    def test_never_chosen_for_the_person(self):
        found = {key: [] for key in ("indoor_temperature", "indoor_humidity", "co2", "windows", "heating", "illuminance", "pm25",
                                     "voc", "purifier", "ventilation", "ventilation_boost", "presence")}
        found["heating_indicator"] = [{"entity_id": "binary_sensor.vanne", "local": True, "available": True, "warnings": [], "reference": False}]
        self.assertNotIn("heating_indicator", suggestions(found, "bureau"))


if __name__ == "__main__":
    unittest.main()
