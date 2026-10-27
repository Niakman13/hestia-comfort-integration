"""Which device carries what: a room alone, the shared air of several rooms, the home; and the VMC never stopped while it dries."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.niak_comfort.entities import binary_value, room_keys, units, volume_id, volume_owner  # noqa: E402


def verdict(gesture="none", level="calm", humidity="normal"):
    return {"gesture": gesture, "level": level, "humidity": humidity, "title": gesture}


def room(entry_id, name, partners=(), volume_name=None, v=None, ventilation=None):
    data = {"verdict": v or verdict(), "assessment": {"features": {"air": {"ventilation": {"on": ventilation}}}}}
    return SimpleNamespace(entry_id=entry_id, partners=[{"entry_id": p} for p in partners], volume_name=volume_name,
                           config={"name": name}, config_entry=SimpleNamespace(title=name), data=data)


class Entities(unittest.TestCase):
    def test_a_room_alone_carries_its_verdict(self):
        keys = room_keys(room("a", "Chambre"))
        self.assertIn("advice", keys["sensor"])
        self.assertIn("ventilation", keys["binary_sensor"])
        self.assertFalse(any(k.startswith("volume:") for k in keys["sensor"]))

    def test_the_shared_air_has_one_device_carried_by_the_best_equipped_room(self):
        salon = room("s", "Salon", ["c"], "Salon · Cuisine")
        cuisine = room("c", "Cuisine", ["s"], "Salon · Cuisine")
        self.assertTrue(volume_owner(salon))
        self.assertFalse(volume_owner(cuisine))
        self.assertEqual(volume_id(salon), volume_id(cuisine))
        self.assertIn("volume:advice", room_keys(salon)["sensor"])
        # Each room keeps only its own measures: no second « Conseil » telling another story.
        for keys in (room_keys(salon), room_keys(cuisine)):
            self.assertNotIn("advice", keys["sensor"])
            self.assertIn("humidity", keys["sensor"])
        self.assertNotIn("volume:advice", room_keys(cuisine)["sensor"])

    def test_the_vmc_stays_useful_while_it_dries_a_humid_room(self):
        humid = room("p", "Chambre P", v=verdict(humidity="very_humid"), ventilation=True)
        self.assertTrue(binary_value("ventilation", humid.data["verdict"], [humid.data]))
        dry = room("p", "Chambre P", v=verdict(humidity="normal"), ventilation=True)
        self.assertFalse(binary_value("ventilation", dry.data["verdict"], [dry.data]))
        asked = room("p", "Chambre P", v=verdict("ventilation"), ventilation=False)
        self.assertTrue(binary_value("ventilation", asked.data["verdict"], [asked.data]))

    def test_the_home_counts_a_shared_air_once(self):
        salon = room("s", "Salon", ["c"], "Salon · Cuisine", verdict("open", "action"))
        cuisine = room("c", "Cuisine", ["s"], "Salon · Cuisine", verdict("open", "action"))
        chambre = room("a", "Chambre", v=verdict("none"))
        coordinators = {"s": salon, "c": cuisine, "a": chambre}
        entries = [SimpleNamespace(entry_id=k, title=c.config["name"], runtime_data=c) for k, c in coordinators.items()]
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=lambda i: next(e for e in entries if e.entry_id == i)))
        found = units(hass, entries)
        self.assertEqual([n for n, _ in found], ["Salon · Cuisine", "Chambre"])
        self.assertEqual(found[0][1]["gesture"], "open")


if __name__ == "__main__":
    unittest.main()
