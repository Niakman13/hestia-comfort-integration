"""Home synthesis: it summarises rooms and never invents what a room did not measure."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.home import synthesis


def view(entry, title, level="calm", action="ok", t=None, needs=(), openings=(), outdoor=None, partial=False):
    obs = {}
    if t is not None:
        obs["indoor_temperature"] = {"value": t, "quality": "valid"}
    if outdoor is not None:
        obs["outdoor_temperature"] = {"value": outdoor, "quality": "valid"}
    return {"entry_id": entry, "title": title, "observations": obs, "names": {o["entity_id"]: o["entity_id"].upper() for o in openings},
            "assessment": {"level": level, "action": action, "needs": list(needs), "partial": partial, "openings": list(openings)}}


def opening(entity_id, open_=False, exposure=None, flags=()):
    return {"entity_id": entity_id, "open": open_, "exposure": exposure, "flags": list(flags)}


class HomeSynthesis(unittest.TestCase):
    def test_the_room_needing_most_attention_leads(self):
        result = synthesis([view("a", "Salon", "calm", t=22), view("b", "Chambre", "urgent", "fermer", t=21), view("c", "Cuisine", "action", "attendre", t=25)])
        self.assertEqual(result["focus"], "b")
        self.assertEqual(result["level"], "urgent")

    def test_hottest_coolest_and_spread_need_two_measured_rooms(self):
        result = synthesis([view("a", "Salon", t=22.4), view("b", "Chambre", t=19.1), view("c", "Grenier")])
        self.assertEqual((result["hottest"]["title"], result["coolest"]["title"], result["spread"]), ("Salon", "Chambre", 3.3))
        alone = synthesis([view("a", "Salon", t=22)])
        self.assertIsNone(alone["hottest"])
        self.assertIsNone(alone["spread"])

    def test_cross_ventilation_from_opposite_open_exposures_across_rooms(self):
        east = view("a", "Cuisine", openings=[opening("e", True, "E")])
        west = view("b", "Salon", openings=[opening("o", True, "O"), opening("s", False, "S")])
        self.assertEqual(synthesis([east, west])["crossing"], "strong")
        south = view("b", "Salon", openings=[opening("s", True, "S")])
        self.assertEqual(synthesis([east, south])["crossing"], "partial")
        self.assertEqual(synthesis([east])["crossing"], "none")
        self.assertIsNone(synthesis([view("a", "Salon")])["crossing"])
        self.assertEqual(synthesis([east, west])["open_rooms"], [{"title": "Cuisine", "open": ["E"]}, {"title": "Salon", "open": ["O"]}])

    def test_start_with_the_warmest_room_that_can_be_cooled_now(self):
        rooms = [view("a", "Salon", "action", "ouvrir", 26, ("cool",)), view("b", "Chambre", "action", "ouvrir", 27.5, ("cool",)),
                 view("c", "Bureau", "action", "attendre", 29, ("cool",))]
        self.assertEqual(synthesis(rooms)["start_with"], "Chambre")
        self.assertIsNone(synthesis([view("a", "Salon", t=22)])["start_with"])

    def test_sun_and_outdoor_come_from_the_rooms(self):
        result = synthesis([view("a", "Salon", outdoor=14.2, openings=[opening("o", True, "O", ["sun_entering"])])])
        self.assertEqual(result["sun_entering"], [{"title": "Salon", "openings": ["O"]}])
        self.assertEqual(result["outdoor_temperature"], 14.2)

    def test_no_room_gives_an_unknown_home(self):
        result = synthesis([])
        self.assertEqual((result["focus"], result["level"]), (None, "neutral"))


if __name__ == "__main__":
    unittest.main()
