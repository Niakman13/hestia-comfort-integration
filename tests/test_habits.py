"""Habits become questions; only a « yes » names a cause, and a window open on purpose is no oversight."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine import habits
from engine.assessment import Opening, assess
from test_engine import zone

UTC = timezone.utc


def rows(days=10, rise_hour=21, night_open=False):
    out, t = [], datetime(2026, 10, 5, tzinfo=UTC)
    while t < datetime(2026, 10, 5, tzinfo=UTC) + timedelta(days=days):
        # The shower moves around 21 h from one evening to the next.
        hour = rise_hour + (t.day % 3) - 1
        hi = 85 if t.hour == hour and t.minute == 30 and t.weekday() < 5 else 60
        opened = 1.0 if night_open and t.hour < 6 else 0.0
        out.append([t.isoformat(), 21.0, hi, 15.0, 70.0, 0.0, opened, 0.0, None, None])
        t += timedelta(minutes=30)
    return out


class Habits(unittest.TestCase):
    def test_a_rise_that_comes_back_becomes_a_question_without_a_cause(self):
        found = habits.detect(rows(), UTC)
        self.assertEqual([(h["key"], h["hour"]) for h in found if h["kind"] == "humidity"], [("humidity:all:21", 21)])
        asked = habits.questions("Salle de bain", "sdb", found, {})
        self.assertIn("monte souvent vers 21 h. Est-ce la douche ?", asked[0]["text"])
        self.assertIn("Est-ce une habitude de la maison ?", habits.questions("Chambre P", None, found, {})[0]["text"])
        self.assertEqual(habits.questions("Salle de bain", "sdb", found, {"humidity:all:21": "no"}), [])

    def test_only_a_yes_names_the_cause_and_only_while_it_goes_on(self):
        found = habits.detect(rows(), UTC)
        monday = datetime(2026, 10, 19, 21, 40, tzinfo=UTC)
        self.assertIsNone(habits.now_habit(found, {}, monday, "Salle de bain", "sdb"))
        self.assertIsNone(habits.now_habit(found, {"humidity:all:21": "unknown"}, monday, "Salle de bain", "sdb"))
        said = habits.now_habit(found, {"humidity:all:21": "yes"}, monday, "Salle de bain", "sdb")
        self.assertEqual(said, "habituelle à cette heure : la douche, elle retombe d’elle-même")
        self.assertIsNone(habits.now_habit(found, {"humidity:all:21": "yes"}, monday + timedelta(hours=4), "Salle de bain", "sdb"))

    def test_a_window_open_on_purpose_at_night_is_no_oversight(self):
        self.assertIn("night_open", [h["key"] for h in habits.detect(rows(night_open=True), UTC)])
        cold = zone(indoor_temperature=20.3, outdoor_temperature=12, **{"window:a": True})
        self.assertEqual(assess(cold, openings={"a": Opening(exposure="E")}).action, "fermer")
        kept = assess(cold, openings={"a": Opening(exposure="E")}, context={"intended_open": True})
        self.assertEqual((kept.action, kept.reason), ("ok", "open_neutral"))
        # On purpose, for the cool air: a warmer outside or a room getting too cold still gets its « Refermez ».
        warm = zone(indoor_temperature=22.5, outdoor_temperature=25, **{"window:a": True})
        self.assertEqual(assess(warm, openings={"a": Opening(exposure="E")}, context={"intended_open": True}).action, "fermer")
        chilly = zone(indoor_temperature=18.5, outdoor_temperature=12, **{"window:a": True})
        self.assertEqual(assess(chilly, openings={"a": Opening(exposure="E")}, context={"intended_open": True}).action, "fermer")
        # Rain still closes it.
        wet = zone(rain=True, indoor_temperature=20.3, outdoor_temperature=12, **{"window:a": True})
        self.assertEqual(assess(wet, openings={"a": Opening(exposure="E")}, context={"intended_open": True}).action, "fermer")


class NightBySeason(unittest.TestCase):
    def test_the_answer_holds_for_its_season_and_is_asked_again_in_the_next(self):
        found = [h for h in habits.detect(rows(night_open=True), UTC) if h["kind"] == "night_open"]
        asked = habits.questions("Chambre AL", "chambre_al", found, {}, "summer")
        self.assertEqual([q["key"] for q in asked], ["night_open:summer"])
        self.assertIn("cet été", asked[0]["text"])
        self.assertEqual(habits.questions("Chambre AL", "chambre_al", found, {"night_open:summer": "yes"}, "summer"), [])
        self.assertEqual([q["key"] for q in habits.questions("Chambre AL", "chambre_al", found, {"night_open:summer": "yes"}, "autumn")],
                         ["night_open:between"])
        self.assertEqual(habits.night_key("winter"), "night_open:winter")
        self.assertEqual(habits.night_key(None), "night_open:between")


class Answers(unittest.TestCase):
    def test_an_answer_is_kept_without_blocking_a_room_being_edited(self):
        import asyncio
        from types import SimpleNamespace
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from custom_components.hestia_comfort.configuration import Configuration
        except ImportError:
            self.skipTest("Home Assistant is not installed")
        saved = []
        service = Configuration.__new__(Configuration)
        service.home = {"sources": {}, "revision": 3}
        service.lock = asyncio.Lock()
        service.store = SimpleNamespace(async_save=lambda data: saved.append(data) or asyncio.sleep(0))
        service.entries = lambda: [SimpleNamespace(entry_id="sdb", data={}, options={})]
        before = service.revision()
        asyncio.run(service.answer("sdb", "humidity:all:21", "yes"))
        self.assertEqual(service.home["answers"], {"sdb": {"humidity:all:21": "yes"}})
        self.assertEqual(saved[-1]["answers"]["sdb"]["humidity:all:21"], "yes")
        self.assertEqual(service.revision(), before)
        with self.assertRaises(ValueError):
            asyncio.run(service.answer("sdb", "night_open", "maybe"))


if __name__ == "__main__":
    unittest.main()
