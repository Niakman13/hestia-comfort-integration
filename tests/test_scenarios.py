"""Replay the twelve user-approved situations on the Python engine.

No equivalence to the whole legacy Jinja template is claimed.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "hestia_comfort"))
from engine.assessment import assess
from engine.sources import Reading

EXPECTED = {
    "calm": ("ok", "calm"), "potential": ("ok", "benefit"),
    "evening": ("ouvrir", "action"), "heat": ("fermer", "action"),
    "winter": ("ouvrir", "urgent"), "humidity": ("ouvrir", "action"),
    "rain": ("fermer", "urgent"), "pollution": ("attendre", "action"),
    "missing": ("unknown", "neutral"), "unknown": ("unknown", "action"),
    "standalone": ("ouvrir", "action"), "expired": ("ok", "urgent"),
}


class ScenarioTests(unittest.TestCase):
    def test_approved_situations(self):
        scenarios = json.loads((ROOT / "tests/fixtures/approved-scenarios.json").read_text())
        self.assertEqual({s["id"] for s in scenarios}, set(EXPECTED))
        for s in scenarios:
            with self.subTest(scenario=s["id"]):
                values = {"indoor_temperature": s["ti"], "outdoor_temperature": s["te"],
                          "indoor_humidity": s["hi"], "outdoor_humidity": s["he"],
                          "co2": s["co2"], "rain": s["rain"], "pollution": s["pollution"],
                          "window:salon": s["windows"] > 0}
                readings = {k: Reading(v, "unknown" if v is None else "valid", "fictitious") for k, v in values.items()}
                if s["heat"] != "absent":
                    readings["heating"] = Reading(s["heat"] if s["heat"] != "stale" else None,
                        "valid" if s["heat"] != "stale" else "stale", "climate.fictitious")
                result = assess(readings)
                self.assertEqual((result.action, result.level), EXPECTED[s["id"]])
                self.assertEqual(result.coordination, "not_connected")


if __name__ == "__main__":
    unittest.main()
