"""The technical state shown on the « Confort » tab: orange only for what stops working, tips for what could be better."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.niak_comfort.health import Facts, Room, Sensor, ago, report


def room(title="Salon", sensors=None, **extra):
    sensors = sensors if sensors is not None else [Sensor("indoor_temperature", "Salon température", "ok", 1),
                                                   Sensor("windows", "Fenêtre", "ok", 3)]
    return Room(entry_id=title.lower(), title=title, sensors=sensors, **extra)


class HealthTests(unittest.TestCase):
    def test_everything_answering_is_blue(self):
        r = report(Facts(rooms=[room()], configured=True, weather="Gardanne", exterior=[Sensor("outdoor_temperature", "T", "ok", 1)], version="0.5.0"))
        self.assertEqual((r["level"], r["summary"], r["rooms_summary"]), ("ok", "Tout est suivi", "1 pièce suivie"))
        self.assertEqual(r["sources"][0], {"label": "Extérieur", "level": "ok", "text": "Niak Weather · Gardanne"})
        self.assertEqual(r["versions"][1]["text"], "Relié à Niak Weather · Gardanne")
        self.assertEqual([c["text"] for c in r["rooms"][0]["cells"]], ["répond", "—", "—", "1 contact", "—"])

    def test_a_silent_sensor_is_to_fix_with_what_it_stops(self):
        r = report(Facts(rooms=[room("Cuisine", [Sensor("indoor_temperature", "T", "ok", 1), Sensor("co2", "Cuisine CO₂", "silent", 300),
                                                 Sensor("windows", "F", "ok", 1)])], configured=True))
        self.assertEqual(r["todo"][0]["text"], "Cuisine : le CO₂ ne répond pas")
        self.assertEqual(r["todo"][0]["why"], "Depuis 5 h. Cuisine CO₂ · Le conseil d’aération est en pause.")
        self.assertEqual(r["todo"][0]["target"], {"kind": "room", "entry_id": "cuisine", "label": "Cuisine"})
        self.assertEqual(r["rooms"][0]["cells"][2], {"level": "bad", "text": "ne répond pas"})

    def test_exterior_missing_or_silent(self):
        r = report(Facts(rooms=[room()]))
        self.assertEqual(r["todo"][0]["text"], "Extérieur à configurer")
        self.assertEqual(r["sources"][0]["level"], "bad")
        r = report(Facts(rooms=[room()], configured=True, exterior=[Sensor("rain", "Pluie", "silent", 20)]))
        self.assertEqual(r["todo"][0]["text"], "Extérieur : la pluie ne répond pas")

    def test_tips_name_what_home_assistant_already_has(self):
        r = report(Facts(rooms=[room(available={"indoor_humidity": "Salon humidité"}), room("Salle de bain", [Sensor("indoor_temperature", "T", "ok", 1)])],
                         configured=True, weather_installed=True, free_areas=[("ete", "Séjour d’été")]))
        texts = [t["text"] for t in r["tips"]]
        self.assertEqual(texts, ["Salon : ajouter l’humidité", "Salle de bain : ouvrants non mesurés", "Séjour d’été pas encore suivie",
                                 "Reprendre l’extérieur de Niak Weather"])
        self.assertIn("« Salon humidité » est disponible", r["tips"][0]["why"])
        self.assertEqual(r["tips"][2]["target"], {"kind": "area", "area_id": "ete", "label": "Ajouter"})
        self.assertEqual(r["level"], "ok")

    def test_ages_read_naturally(self):
        self.assertEqual([ago(0.5), ago(12), ago(300)], ["à l’instant", "il y a 12 min", "il y a 5 h"])




class Counts(unittest.TestCase):
    def test_one_sensor_count_for_rooms_and_exterior(self):
        r = report(Facts(rooms=[room(sensors=[Sensor("indoor_temperature", "T", "ok", 1), Sensor("presence", "P", "silent", 9),
                                              Sensor("windows", "F", "ok", 1), Sensor("windows", "G", "ok", 1)])],
                         configured=True, exterior=[Sensor("rain", "Pluie", "ok", 1)]))
        # The presence sensor has no column of its own: it still counts, and is still a point to fix.
        self.assertEqual(r["sensors"], {"answering": 4, "total": 5})
        self.assertEqual([t["text"] for t in r["todo"]], ["Salon : la présence ne répond pas"])

    def test_stale_reading_is_named(self):
        r = report(Facts(rooms=[room(sensors=[Sensor("indoor_temperature", "T", "stale", 300), Sensor("windows", "F", "ok", 1)])], configured=True))
        self.assertEqual(r["todo"][0]["text"], "Salon : la température ne donne pas de mesure exploitable")
        self.assertEqual(r["sensors"], {"answering": 1, "total": 2})

    def test_windows_without_contact_on_purpose_are_not_suggested(self):
        r = report(Facts(rooms=[room("Garage", [Sensor("indoor_temperature", "T", "ok", 1)], windows_intended=True)], configured=True))
        self.assertNotIn("Garage : ouvrants non mesurés", [t["text"] for t in r["tips"]])


if __name__ == "__main__":
    unittest.main()
