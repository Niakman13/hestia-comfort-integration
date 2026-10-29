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

    def test_the_pause_holds_right_after_closing_even_while_high(self):
        # The home, 28 Oct.: cooking, « Aérez » from 22:45, Fenêtre Ouest open 23:07–23:14, the index still 323 at the
        # closing. Seven seconds later « Aérez » came back: it was already high, and a strong peak.
        just_shut = (NOW - timedelta(seconds=7)).isoformat()
        again = voc.judge(323, 150, NOW, mean=330, was_high=True, above_since=ago(29), aired_at=just_shut, aired_after=330)
        self.assertFalse(again["high"])
        self.assertTrue(again["paused"])
        # Climbing well above what the airing left still calls for air.
        self.assertTrue(voc.judge(400, 150, NOW, mean=390, was_high=True, above_since=ago(29), aired_at=just_shut,
                                  aired_after=330)["high"])
        # Still high once the pause is over: asked again.
        self.assertTrue(voc.judge(323, 150, NOW, mean=330, was_high=True, above_since=ago(80), aired_at=ago(46),
                                  aired_after=330)["high"])

    def test_mean_weighs_each_reading_by_its_time(self):
        points = [(NOW - timedelta(minutes=30), 100), (NOW - timedelta(minutes=5), 200), (NOW - timedelta(minutes=1), 100)]
        self.assertAlmostEqual(voc.mean(points, NOW), (100 * 5 + 200 * 4 + 100 * 1) / 10)
        # A reading just received counts too.
        self.assertAlmostEqual(voc.mean([(NOW - timedelta(minutes=10), 100), (NOW, 220)], NOW), (100 * 600 + 220 * 30) / 630)
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

    def test_falling_by_itself_or_learned_outdoor_calls_for_nothing(self):
        context = {**self.context, "voc_delay_minutes": 0}
        falling = assess(self.rows, now=NOW, context={**context, "voc_falling": True}).features["air"]
        self.assertEqual((falling["voc_status"], falling["voc_falling"]), ("ok", True))
        outdoor = assess(self.rows, now=NOW, context={**context, "voc_outdoor": True}).features["air"]
        self.assertEqual((outdoor["voc_status"], outdoor["voc_outdoor"]), ("ok", True))

    def test_climbing_with_the_window_open_says_close(self):
        # 28 Oct., 23:07–23:14: opened at 175, the index at 354 four minutes later.
        rows = {**self.rows, "outdoor_temperature": Reading(20.8, "valid"), "voc": Reading(354, "valid", unit=None),
                "window:binary_sensor.w": Reading(True, "valid")}
        context = {**self.context, "voc_opened_level": 175, "voc_mean": 300}
        first = assess(rows, now=NOW, context=context)
        self.assertTrue(first.features["air"]["voc_rising_open"])
        self.assertEqual((first.action, first.reason), ("fermer", "voc_outdoor"))
        # Opened on a high index that goes down: the airing works, it stays open.
        down = assess({**rows, "voc": Reading(200, "valid", unit=None)}, now=NOW, context={**context, "voc_opened_level": 330, "voc_mean": 220})
        self.assertNotEqual(down.reason, "voc_outdoor")
        # Opened on a low index that a meal sends up (26 Oct., 12:41: 105 → 234): the airing helps, not the outside.
        meal = assess({**rows, "voc": Reading(234, "valid", unit=None)}, now=NOW, context={**context, "voc_opened_level": 105, "voc_mean": 200})
        self.assertNotEqual(meal.reason, "voc_outdoor")
        # A source inside already climbing at the opening: not the outside either.
        going = assess(rows, now=NOW, context={**context, "voc_going": True})
        self.assertNotEqual(going.reason, "voc_outdoor")


class Learned(unittest.TestCase):
    def test_falling_compares_two_means(self):
        # 28 Oct.: 434 at 22:52, 172 at 23:04, the windows shut.
        values = [(-24, 225), (-22, 329), (-20, 436), (-18, 435), (-16, 383), (-14, 434), (-12, 356), (-10, 366),
                  (-8, 261), (-6, 211), (-4, 185), (-2, 172)]
        points = [(NOW + timedelta(minutes=m), v) for m, v in values]
        self.assertTrue(voc.is_falling(points, NOW, 150))
        # A plateau is not falling, and twenty minutes are needed to tell.
        flat = [(NOW + timedelta(minutes=m), 180) for m, _ in values]
        self.assertFalse(voc.is_falling(flat, NOW, 150))
        self.assertFalse(voc.is_falling(points[-5:], NOW, 150))

    def test_airings_teach_the_hours_when_outside_air_brings_voc(self):
        def airing(day, hour, before, after, rising_before=False):
            start = datetime(2026, 10, day, hour, 0, tzinfo=timezone.utc)
            points = [(start - timedelta(minutes=4), before - (40 if rising_before else 0)), (start, before),
                      (start + timedelta(minutes=3), after), (start + timedelta(minutes=8), after)]
            return [(start, True), (start + timedelta(minutes=8), False)], points
        cases = [airing(20, 21, 175, 350), airing(21, 21, 180, 185), airing(22, 21, 170, 300), airing(23, 21, 160, 290),
                 airing(23, 12, 200, 380, rising_before=True), airing(24, 12, 200, 190)]
        contacts = {"w": [row for rows, _ in cases for row in rows]}
        points = sorted(p for _, pts in cases for p in pts)
        records = voc.airings(contacts, points, 150)
        # The noon one began while a source inside was already sending it up: left out.
        self.assertEqual([r["slot"] for r in records], ["evening"] * 4 + ["afternoon"])
        self.assertEqual(voc.outdoor_slots(records), ["evening"])
        # Two out of three are not enough: the index jumps a lot.
        self.assertEqual(voc.outdoor_slots(records[:3]), [])


if __name__ == "__main__":
    unittest.main()
