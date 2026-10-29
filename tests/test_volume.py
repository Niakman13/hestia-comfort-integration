"""Rooms open onto each other: shared openings, one gesture for the shared air."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.assessment import Opening, assess
from engine.volume import arbitrate, weight
from test_engine import zone


class SharedVolume(unittest.TestCase):
    def test_the_kitchen_window_airs_the_open_plan_salon(self):
        # 20 Oct.: the kitchen window open since 13 h 09, the salon's VOC high. The salon asked to open its own.
        alone = assess(zone(co2=1300, **{"window:ouest": False}), openings={"ouest": Opening(exposure="O")})
        self.assertEqual(alone.action, "ouvrir")
        shared = assess(zone(co2=1300, **{"window:ouest": False, "window:cuisine": True}),
                        openings={"ouest": Opening(exposure="O"), "cuisine": Opening(exposure="E")})
        self.assertEqual((shared.action, shared.reason), ("ok", "air_needed"))

    def test_a_weightier_partner_speaks_for_the_volume(self):
        salon = assess(zone(co2=1300, **{"window:a": True})).to_dict()
        kitchen = assess(zone(indoor_temperature=20.5, outdoor_temperature=8, **{"window:a": True})).to_dict()
        self.assertEqual((kitchen["action"], salon["action"]), ("fermer", "ok"))
        settled = arbitrate(kitchen, [("Salon", salon)])
        self.assertEqual((settled["action"], settled["reason"]), ("ok", "shared_volume"))
        volume = settled["features"]["volume"]
        self.assertEqual((volume["lead"], volume["reason"], volume["action"]), ("Salon", salon["reason"], "ok"))
        self.assertEqual(volume["assessment"]["reason"], salon["reason"])
        # The salon keeps its own words: its reason outweighs the kitchen's.
        self.assertIs(arbitrate(salon, [("Cuisine", kitchen)]), salon)

    def test_rain_on_the_shared_window_outweighs_a_need_for_air(self):
        radar = {"rain": {"minutes": 10, "precision": "minute"}}
        kitchen = assess(zone(**{"window:a": True}), outlook=radar).to_dict()
        salon = assess(zone(co2=1300), outlook={}).to_dict()
        self.assertEqual(kitchen["reason"], "rain_soon")
        self.assertGreater(weight(kitchen), weight(salon))
        settled = arbitrate(salon, [("Cuisine", kitchen)])
        self.assertEqual((settled["action"], settled["reason"]), ("fermer", "shared_volume"))

    def test_same_gestures_stay_and_quiet_rooms_follow(self):
        a = assess(zone(co2=1300, **{"window:a": True})).to_dict()
        b = assess(zone(indoor_humidity=75, outdoor_humidity=50, outdoor_temperature=12, **{"window:a": True})).to_dict()
        calm = assess(zone()).to_dict()
        self.assertIs(arbitrate(a, [("B", b)]), a)
        # One verdict per volume: a quiet room shows its partner's advice instead of its own « nothing to do ».
        follows = arbitrate(calm, [("A", a)])
        self.assertEqual((follows["action"], follows["reason"], follows["level"]), ("ok", "shared_volume", a["level"]))
        self.assertIs(arbitrate(calm, [("B", calm)]), calm)


if __name__ == "__main__":
    unittest.main()


class VolumeDeclaration(unittest.TestCase):
    def test_open_onto_is_mutual_and_passes_from_room_to_room(self):
        from types import SimpleNamespace
        try:
            from custom_components.hestia_comfort.configuration import Configuration
        except ImportError:  # the engine's own test run, without Home Assistant
            self.skipTest("Home Assistant is not installed")
        rooms = {"salon": ["cuisine"], "cuisine": [], "entree": ["cuisine"], "chambre": []}
        entries = [SimpleNamespace(entry_id=k, data={}, options={"open_to": v}) for k, v in rooms.items()]
        service = Configuration.__new__(Configuration)
        service.entries = lambda: entries
        self.assertEqual(service.volume("salon"), ["cuisine", "entree"])
        self.assertEqual(service.volume("cuisine"), ["entree", "salon"])
        self.assertEqual(service.volume("chambre"), [])


class SharedSources(unittest.TestCase):
    def test_the_kitchen_reads_the_heating_and_air_of_its_living_room(self):
        """Cuisine, 21 October: no thermostat of its own, heated by the Salon's, breathing the air its CO₂ sensor measures."""
        try:
            from custom_components.hestia_comfort.coordinator import ComfortCoordinator
        except ImportError:  # the engine's own test run, without Home Assistant
            self.skipTest("Home Assistant is not installed")
        room = ComfortCoordinator.__new__(ComfortCoordinator)
        room.config = {"sources": {"indoor_temperature": "sensor.cuisine_t", "indoor_humidity": "sensor.cuisine_h"}}
        room.partners = [{"title": "Salon", "shared": {"heating": "climate.salon", "co2": "sensor.salon_co2"}}]
        room.sources = room._sources()
        self.assertEqual(room.sources, {"indoor_temperature": "sensor.cuisine_t", "indoor_humidity": "sensor.cuisine_h",
                                        "heating": "climate.salon", "co2": "sensor.salon_co2"})
        self.assertEqual(room.inherited(), {"heating": "Salon", "co2": "Salon"})
        # Its own sensor wins; a room declared unheated takes no thermostat.
        room.config = {"sources": {"co2": "sensor.cuisine_co2"}, "heated": False}
        room.sources = room._sources()
        self.assertEqual(room.sources, {"co2": "sensor.cuisine_co2"})
