"""« Chauffez un peu plus » for damp walls that no airing nor running ventilation dries."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))
from engine.assessment import Settings, assess
from engine.sources import Reading

NOW = datetime(2026, 10, 26, 15, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 26, 2, tzinfo=timezone.utc)
SETTINGS = Settings(minimum=18, maximum=24)


def run(ti=18.7, hi=70, te=9.3, he=95, heating="idle", ventilation=None, settings=SETTINGS, now=NOW, **context):
    values = {"indoor_temperature": ti, "indoor_humidity": hi, "outdoor_temperature": te, "outdoor_humidity": he}
    if heating is not None:
        values["heating"] = heating
    if ventilation is not None:
        values["ventilation"] = ventilation
    readings = {k: Reading(v, "valid", "sensor." + k) for k, v in values.items()}
    return assess(readings, settings, None, {}, None, {}, now,
                  context={"heated": True, "occupied": True, "humidity_floor_3h": hi - 1, **context})


class WarmWalls(unittest.TestCase):
    def test_chambre_p_one_degree_is_enough(self):
        # 26 Oct., Chambre P: 18.7 °C, 70 %, 9.3 °C outside; the wall corner at about 83 %.
        a = run()
        self.assertEqual((a.reason, a.level), ("warm_walls", "action"))
        w = a.features["warm_walls"]
        self.assertEqual(w["degrees"], 1)
        self.assertGreaterEqual(w["surface"], 80)
        self.assertLess(w["after"], 80)

    def test_a_running_ventilation_is_the_remedy(self):
        self.assertNotEqual(run(ventilation=True).reason, "warm_walls")

    def test_no_heating_known_no_gesture(self):
        self.assertNotEqual(run(heating=None).reason, "warm_walls")

    def test_not_asked_when_two_degrees_are_not_enough(self):
        a = run(hi=80)
        self.assertNotEqual(a.reason, "warm_walls")
        self.assertIsNone(a.features["warm_walls"])

    def test_never_above_a_degree_under_the_maximum(self):
        self.assertNotEqual(run(ti=22.5, settings=Settings(minimum=18, maximum=23)).reason, "warm_walls")

    def test_never_at_night(self):
        self.assertNotEqual(run(now=NIGHT).reason, "warm_walls")

    def test_never_against_a_thermostat_lowered_on_purpose(self):
        eco = {"name": "Versatile Thermostat", "mode": "heat", "preset": "eco", "target": 17.0}
        self.assertNotEqual(run(thermostat=eco).reason, "warm_walls")

    def test_not_at_the_threshold(self):
        # About 80 % against the wall: a risk to say, not yet worth heating for.
        self.assertNotEqual(run(hi=67.5).reason, "warm_walls")

    def test_empty_home_is_not_asked(self):
        self.assertNotEqual(run(occupied=False).reason, "warm_walls")


if __name__ == "__main__":
    unittest.main()
