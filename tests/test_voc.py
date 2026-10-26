"""VOC judged steadily: mean, margin, delay, strong peak and pause after an airing (engine/voc.py)."""
from datetime import datetime, timedelta, timezone
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "niak_comfort"))

from engine import voc  # noqa: E402
from engine.assessment import assess  # noqa: E402
from engine.sources import Reading  # noqa: E402

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat()


class Judge(unittest.TestCase):
    def test_a_passing_peak_waits_for_the_delay(self):
        first = voc.judge(170, 150, NOW)
        self.assertFalse(first["high"])
        self.assertEqual(first["above_since"], NOW.isoformat())
        self.assertFalse(voc.judge(170, 150, NOW, above_since=ago(9))["high"])
        later = voc.judge(170, 150, NOW, above_since=ago(10))
        self.assertTrue(later["high"])
        self.assertEqual(later["minutes"], 10)

    def test_a_strong_peak_calls_at_once(self):
        self.assertTrue(voc.judge(300, 150, NOW)["high"])

    def test_the_mean_is_judged_not_one_reading(self):
        self.assertIsNone(voc.judge(190, 150, NOW, mean=130)["above_since"])

    def test_margin_once_high(self):
        self.assertTrue(voc.judge(125, 150, NOW, was_high=True, above_since=ago(20))["high"])
        self.assertFalse(voc.judge(115, 150, NOW, was_high=True, above_since=ago(20))["high"])

    def test_pause_after_an_airing(self):
        since = ago(15)
        paused = voc.judge(170, 150, NOW, above_since=since, aired_at=ago(20), aired_after=140)
        self.assertFalse(paused["high"])
        self.assertTrue(paused["paused"])
        # Well above what the airing left: asked again.
        self.assertTrue(voc.judge(195, 150, NOW, above_since=since, aired_at=ago(20), aired_after=140)["high"])
        # The pause is over.
        self.assertTrue(voc.judge(170, 150, NOW, above_since=since, aired_at=ago(50), aired_after=140)["high"])
        # A shorter pause chosen by the person.
        self.assertTrue(voc.judge(170, 150, NOW, above_since=since, aired_at=ago(20), aired_after=140, pause=15)["high"])

    def test_mean_weighs_each_reading_by_its_time(self):
        points = [(NOW - timedelta(minutes=30), 100), (NOW - timedelta(minutes=5), 200), (NOW - timedelta(minutes=1), 100)]
        self.assertAlmostEqual(voc.mean(points, NOW), (100 * 5 + 200 * 4 + 100 * 1) / 10)
        self.assertIsNone(voc.mean([], NOW))


class InAssessment(unittest.TestCase):
    rows = {"indoor_temperature": Reading(21, "valid"), "outdoor_temperature": Reading(15, "valid"),
            "voc": Reading(180, "valid", unit=None)}
    context = {"voc_threshold": {"value": 150, "unit": ""}}

    def test_the_state_carries_from_one_update_to_the_next(self):
        first = assess(self.rows, now=NOW, context=self.context)
        air = first.features["air"]
        self.assertEqual(air["voc_status"], "ok")
        self.assertEqual(air["voc_above_since"], NOW.isoformat())
        later = assess(self.rows, now=NOW + timedelta(minutes=12), previous=first, context=self.context)
        self.assertEqual(later.features["air"]["voc_status"], "high")
        self.assertIn("COV au-dessus de l’habituel depuis 12 min", later.features["air"]["message"])

    def test_delay_from_settings(self):
        first = assess(self.rows, now=NOW, context={**self.context, "voc_delay_minutes": 0})
        self.assertEqual(first.features["air"]["voc_status"], "high")


if __name__ == "__main__":
    unittest.main()
