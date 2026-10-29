"""Situations de la maquette, calculées par le vrai moteur Hestia Confort (engine/), écrites dans scenes.json.

Lancer depuis le dépôt : ../ha-test/venv/bin/python card/preview/refonte/scenes.py
Données fictives inspirées de la maison de Frank ; aucune connexion à Home Assistant.
"""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from custom_components.niak_comfort.engine.assessment import Settings, Sun, assess  # noqa: E402
from custom_components.niak_comfort.engine.home import synthesis  # noqa: E402
from custom_components.niak_comfort.engine.sources import Reading  # noqa: E402

NOW = datetime(2026, 10, 18, 15, 0, tzinfo=timezone.utc)
UNITS = {"indoor_temperature": "°C", "outdoor_temperature": "°C", "indoor_humidity": "%", "outdoor_humidity": "%", "co2": "ppm"}
DAY = {"indoor_day_range": {"min": 19.6, "max": 22.4}, "heated": True, "outdoor_mean_7d": 15.9}
VMC = "fan.vmc"


def view(entry_id, title, values, *, context=None, sun=Sun(25, 220), outlook=None, names=None, silent=(), starting=False):
    readings = {k: Reading(v, "valid", f"sensor.demo_{k.replace(':', '_')}", NOW.isoformat(), None, UNITS.get(k)) for k, v in values.items()}
    for k in silent:  # a configured sensor that does not answer (unavailable in Home Assistant)
        readings[k] = Reading(None, "unknown", f"sensor.demo_{k.replace(':', '_')}", None, "unavailable", UNITS.get(k))
    if "ventilation" in readings:
        readings["ventilation"] = Reading(values["ventilation"], "valid", VMC, NOW.isoformat())
    result = assess(readings, Settings(humidity_high=60), None, None, sun, outlook or {}, NOW, context={**DAY, **(context or {})})
    return {"version": 1, "entry_id": entry_id, "area_id": entry_id, "title": title, "comfort_minimum": 20,
            "computed_at": NOW.isoformat(), "assessment": result.to_dict(),
            "observations": {k: asdict(r) for k, r in readings.items()},
            "names": names or {"binary_sensor.demo_fenetre": "Fenêtre ouest"}, "starting": starting}


def base(**extra):
    return {"indoor_temperature": 21.1, "outdoor_temperature": 13.0, "indoor_humidity": 52.0, "outdoor_humidity": 70.0,
            "co2": 640.0, "rain": False, "window:binary_sensor.demo_fenetre": False, **extra}


LEARNED = {"drying_model": {"tau": 35.0, "residual": 1.3, "rebound": 0.45, "openings": 8}}
SLOW = {"drying_model": {"tau": 165.0, "residual": 2.0, "rebound": 0.37, "openings": 6}}
EVENING = [{"time": (NOW + timedelta(hours=h)).isoformat(), "temperature": 13.0 if h < 6 else 6.0,
            "humidity": 80.0, "precipitation": 0} for h in range(13)]

SCENES = [
    ("calme", "Tout va bien", "Bleu : rien à faire.", view("calme", "Salon", base())),
    ("inutile", "Un conseil qui n’apporterait rien",
     "Le Salon du 18 octobre : 66 %, mais l’air du dehors est aussi chargé en eau. Avant : « Humidité à surveiller » en orange. Maintenant : bandeau calme, tuile Humidité entourée de jaune.",
     view("inutile", "Salon", base(indoor_humidity=66.0, outdoor_humidity=92.0))),
    ("geste", "Geste conseillé",
     "Orange : un geste utile maintenant. Gain et durée appris des aérations de la pièce ; le rond envoie des ondes.",
     view("geste", "Cuisine", base(indoor_humidity=72.0, outdoor_humidity=78.0, outdoor_temperature=10.0), context=LEARNED)),
    ("plus-tard", "À saisir plus tard",
     "Vert : un moment précis, calculé avec la prévision de Hestia Weather.",
     view("plus-tard", "Chambre AL", base(indoor_humidity=70.0, outdoor_humidity=88.0),
          context={"drying_model": {"tau": 60.0, "residual": 2.6, "rebound": 0.4, "openings": 5}}, outlook={"hours": EVENING})),
    ("vmc", "Un autre équipement aide",
     "Aérer sèche peu cette pièce (fenêtre en oscillo-battant) : Hestia propose la VMC, l’hélice tourne.",
     view("vmc", "Chambre P", base(indoor_humidity=76.0, outdoor_humidity=81.0, indoor_temperature=20.2, ventilation=False), context=SLOW,
          names={"binary_sensor.demo_fenetre": "Fenêtre chambre P", VMC: "VMC"})),
    ("urgent", "Urgent", "Rouge : la pluie entre par une fenêtre exposée.",
     view("urgent", "Chambre M", base(rain=True, **{"window:binary_sensor.demo_fenetre": True}), names={"binary_sensor.demo_fenetre": "Fenêtre Marylou"})),
    ("demarrage", "Juste après un démarrage",
     "Ce n’est pas un conseil : Home Assistant vient de démarrer, les capteurs arrivent un à un. Pastille « Démarrage », tuiles qui scintillent.",
     view("demarrage", "Salon", base(), silent=("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity", "co2"), starting=True)),
    ("muette", "La pièce ne répond plus",
     "Ce n’est pas un conseil : gris, « Capteurs muets », le nombre plutôt qu’une liste ; pas d’échelle vide ; tuiles en pointillés.",
     view("muette", "Salon", base(), silent=("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity", "co2"))),
    ("isole", "Un capteur secondaire muet",
     "Le reste fonctionne : bandeau calme, seule la tuile CO₂ passe en pointillés.",
     view("isole", "Chambre A", base(), silent=("co2",))),
]

home_rooms = [SCENES[1][3] | {"entry_id": "h-salon", "title": "Salon"},
              SCENES[2][3] | {"entry_id": "h-cuisine", "title": "Cuisine"},
              SCENES[4][3] | {"entry_id": "h-chp", "title": "Chambre P"},
              SCENES[0][3] | {"entry_id": "h-sdb", "title": "Salle de bain"}]
for room in home_rooms:
    room["floor"] = None
out = {"generated": NOW.isoformat(),
       "scenes": [{"id": i, "title": t, "note": n, "view": v} for i, t, n, v in SCENES],
       "home": {"version": 1, "rooms": home_rooms, "home": synthesis(home_rooms)}}
Path(__file__).with_name("scenes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for i, t, n, v in SCENES:
    a = v["assessment"]
    print(f"{i:10} {a['action']:9} {a['reason']:22} {a['level']}")
print("logement", out["home"]["home"]["level"])
