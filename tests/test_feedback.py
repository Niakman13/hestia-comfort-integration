"""The feedback loop: airings followed become measured experiments that correct the next predictions."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine import feedback, twin

T0 = datetime(2026, 10, 21, 10, tzinfo=timezone.utc)
DRYING = {"action": "ouvrir", "reason": "drying_possible", "features": {"drying": {"now": 76, "after": 68, "minutes": 15, "openings": 31},
                                                                       "learned": {"measure": "humidity", "after": 68}}}


def airing(before, after, predicted, at):
    record = feedback.start({**DRYING, "features": {**DRYING["features"], "learned": {"measure": "humidity", "after": predicted}}},
                            {"indoor_humidity": before}, at)
    return feedback.finish(record, {"indoor_humidity": after}, at + timedelta(minutes=15))


class FeedbackLoop(unittest.TestCase):
    def test_a_followed_airing_is_measured_against_its_prediction(self):
        record = feedback.start(DRYING, {"indoor_humidity": 76}, T0)
        self.assertEqual((record["measure"], record["before"], record["predicted"], record["learned"]), ("humidity", 76, 68, True))
        done = feedback.finish(record, {"indoor_humidity": 70}, T0 + timedelta(minutes=15))
        self.assertEqual((done["after"], done["minutes"]), (70, 15))
        self.assertTrue(feedback.held(done))  # 70 for 68 predicted: within 3 points
        summary = feedback.summarize([done], T0 + timedelta(hours=1))
        self.assertEqual(summary["last"]["after"], 70)
        self.assertEqual(summary["week"], {"followed": 1, "ignored": 0, "evaluated": 1, "held": 1, "gains": {"humidity": -6.0}})
        # A window left open three hours is not an experiment any more.
        self.assertIsNone(feedback.finish(record, {"indoor_humidity": 70}, T0 + timedelta(hours=4)))

    def test_a_door_crossed_is_not_an_airing_and_the_result_is_read_after_closing(self):
        """The Salon, 21 October: a French window opened 26 seconds, its VOC read before the sensor spoke again."""
        voc = {"action": "ouvrir", "reason": "air_needed", "features": {"air": {"voc_status": "high"}}}
        record = feedback.start(voc, {"voc": 283}, T0)
        self.assertIsNone(feedback.finish({**record, "closed": (T0 + timedelta(seconds=26)).isoformat()}, {"voc": 288}, T0 + timedelta(minutes=5)))
        # A real airing: closed after 20 minutes, read four minutes later, the minutes are those it stood open.
        done = feedback.finish({**record, "closed": (T0 + timedelta(minutes=20)).isoformat()}, {"voc": 120}, T0 + timedelta(minutes=24))
        self.assertEqual((done["minutes"], done["after"], done["end"], "closed" in done), (20, 120, (T0 + timedelta(minutes=20)).isoformat(), False))
        # Such a record kept before is dropped: it would bend the next predictions.
        flash = {**record, "end": (T0 + timedelta(seconds=26)).isoformat(), "minutes": 0, "after": 288}
        self.assertEqual(feedback.keep([flash, done, feedback.ignored(T0, T0 + timedelta(minutes=1))], T0 + timedelta(hours=1)),
                         [done, feedback.ignored(T0, T0 + timedelta(minutes=1))])

    def test_the_air_advice_is_measured_on_the_air(self):
        air = {"action": "ouvrir", "reason": "air_needed", "features": {"air": {"co2_status": "high"}}}
        self.assertEqual(feedback.measure(air), "co2")
        self.assertEqual(feedback.measure({**air, "features": {"air": {"co2_status": "ok", "voc_status": "high"}}}), "voc")
        follower = {"action": "ok", "reason": "shared_volume", "features": {"volume": {"reason": "air_needed", "assessment": {"features": {"air": {"co2_status": "high"}}}}}}
        self.assertEqual(feedback.measure(follower), "co2")

    def test_an_advice_left_aside_is_counted(self):
        records = [feedback.ignored(T0, T0 + timedelta(minutes=40))]
        self.assertEqual(feedback.summarize(records, T0 + timedelta(hours=1))["week"]["ignored"], 1)

    def test_the_gaps_correct_the_next_prediction_and_misses_bring_back_estimates(self):
        drier = [airing(76, 72, 68, T0 + timedelta(hours=i)) for i in range(3)]  # always 4 points less dry than predicted
        summary = feedback.summarize(drier, T0 + timedelta(hours=4))
        self.assertEqual(summary["bias"]["humidity"], 4.0)
        self.assertFalse(summary["trusted"])  # 72 for 68: missed three times out of three
        good = [airing(76, 70, 68, T0 + timedelta(hours=i)) for i in range(3)]
        summary = feedback.summarize(good, T0 + timedelta(hours=4))
        self.assertTrue(summary["trusted"])
        self.assertEqual(summary["bias"]["humidity"], 2.0)
        rows, end = __import__("test_twin").known_room()
        ready = {**twin.summary(rows, end), "days": 10, "precision": {"hours": 24, "temperature": 0.2, "humidity": 1.5}}
        learned = twin.learned_advice(DRYING, ready, feedback=summary)
        self.assertEqual((learned["after"], learned.get("corrected")), (70, True))
        self.assertIsNone(twin.learned_advice(DRYING, ready, feedback=feedback.summarize(drier, T0 + timedelta(hours=4))))


if __name__ == "__main__":
    unittest.main()
