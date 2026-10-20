"""Situations for the « conseils / À savoir » mock-up, computed by the real engine (run: python scenes.py)."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "custom_components" / "niak_comfort"))
from engine.assessment import Opening, Settings, Sun, absolute_humidity, assess
from engine.sources import Reading
from engine.volume import arbitrate

NOW = datetime(2026, 10, 20, 14, tzinfo=timezone.utc)
S = Settings(minimum=20, maximum=24, humidity_high=60, co2_potential=800, co2_action=1000, co2_urgent=1500)
UNITS = {"indoor_temperature": "°C", "outdoor_temperature": "°C", "indoor_humidity": "%", "outdoor_humidity": "%", "co2": "ppm", "pm25": "µg/m³"}


def view(entry, title, values, windows, outlook=None, context=None, sun=Sun(30, 200)):
    readings = {k: Reading(v, "valid", f"sensor.{entry}_{k.replace(':', '_')}", NOW.isoformat()) for k, v in values.items()}
    for w, opened in windows.items():
        readings[f"window:{w}"] = Reading(opened, "valid", w, NOW.isoformat())
    a = assess(readings, S, None, {w: Opening(exposure="O") for w in windows}, sun, outlook or {}, NOW, context=context or {}).to_dict()
    return {"version": 1, "entry_id": entry, "area_id": entry, "title": title, "comfort_minimum": 20, "computed_at": NOW.isoformat(),
            "assessment": a, "observations": {k: {**asdict(r), "unit": UNITS.get(k)} for k, r in readings.items()},
            "names": {w: "Fenêtre " + title.split()[-1] if not w.startswith("binary_sensor.fenetre_c") else "Fenêtre cuisine" for w in windows},
            "starting": False}


AUTUMN = {"outdoor_temperature": 17.8, "outdoor_humidity": 91, "rain": False, "pollution": False, "wind_gust": 8}
WINTER = {"outdoor_temperature": 4, "outdoor_humidity": 80, "rain": False, "pollution": False, "wind_gust": 8}
scenes = []
def add(id_, title, note, v):
    v["entry_id"] = v["area_id"] = id_
    scenes.append({"id": id_, "title": title, "note": note, "view": v})

add("a", "Air humide dehors, risque de moisissure", "Avant : « Murs humides » dans le bandeau, avec « Tout va bien ».",
    view("a", "Chambre A", {**AUTUMN, "indoor_temperature": 20.7, "indoor_humidity": 76.2}, {"fenetre_a": False}, context={"lasting": True, "humidity_floor_3h": 74}))
add("m", "Air humide dehors seulement", "Avant : « Air humide dehors » en titre de conseil.",
    view("m", "Chambre M", {**AUTUMN, "indoor_temperature": 20.7, "indoor_humidity": 73.3}, {"fenetre_m": False}))
# Salon and kitchen, one air: kitchen window open, nothing to gain.
vol = {"water": (absolute_humidity(21.1, 73) + absolute_humidity(21.6, 81)) / 2, "temperature": 21.35,
       "drying_model": {"tau": 37.2, "residual": 1.5, "rebound": 0.4, "openings": 31}}
w = {"fenetre_ouest": False, "binary_sensor.fenetre_c": True}
salon = view("salon1", "Salon", {**AUTUMN, "indoor_temperature": 21.1, "indoor_humidity": 73, "co2": 620}, w, context={"volume": vol})
add("salon1", "Même air, fenêtre de la cuisine ouverte pour rien", "Avant : Salon « Murs humides », Cuisine « Murs humides », bandeaux bleus sans geste.", salon)
# Salon needs air, kitchen follows.
s2 = view("salon2", "Salon", {**AUTUMN, "indoor_temperature": 21.1, "indoor_humidity": 70, "co2": 1180}, w, context={"volume": vol})
k2 = view("cuisine2", "Cuisine", {**AUTUMN, "indoor_temperature": 21.6, "indoor_humidity": 78}, w, context={"volume": vol})
k2["assessment"] = arbitrate(k2["assessment"], [("Salon", s2["assessment"])])
if k2["assessment"]["features"].get("volume"):
    k2["assessment"]["features"]["volume"]["observations"] = s2["observations"]
add("salon2", "Salon : CO₂ élevé, la cuisine est ouverte", "Le geste est déjà en cours : on le dit, avec sa durée.", s2)
add("cuisine2", "Cuisine : même air que le salon", "Même bandeau que le salon, et « Même air » dans À savoir.", k2)
add("p", "Humidité venue de l’intérieur, VMC arrêtée", "Un vrai geste : le bandeau le dit ; les murs humides passent dessous.",
    view("p", "Chambre P", {**AUTUMN, "indoor_temperature": 20.5, "indoor_humidity": 87, "ventilation": False}, {"fenetre_p": False},
         context={"drying_model": {"tau": 171.7, "residual": 1.5, "rebound": 0.4, "openings": 4}}))
add("al", "Fenêtre ouverte, la pièce refroidit", "Un geste : refermer.",
    view("al", "Chambre AL", {**AUTUMN, "indoor_temperature": 20.3, "indoor_humidity": 72.8}, {"fenetre_al": True}))
add("froid1", "Hiver : pièce froide, chauffage coupé, quelqu’un là", "Orange : un geste à faire.",
    view("froid1", "Chambre A", {**WINTER, "indoor_temperature": 18.6, "indoor_humidity": 50, "heating": "off"}, {"fenetre_a": False}, context={"occupied": True}))
add("froid2", "Hiver : pièce froide, maison vide (Alarmo en absence)", "Bleu : rien à faire, l’explication passe dans À savoir.",
    view("froid2", "Chambre A", {**WINTER, "indoor_temperature": 18.6, "indoor_humidity": 50, "heating": "off"}, {"fenetre_a": False}, context={"occupied": False}))
add("pluie", "Pluie dans 10 min, fenêtre ouverte", "Un geste urgent.",
    view("pluie", "Chambre AL", {**AUTUMN, "indoor_temperature": 21, "indoor_humidity": 65}, {"fenetre_al": True},
         outlook={"rain": {"minutes": 10, "precision": "minute"}, "station": ("rain_rate", "wind_gust")}))
add("douche", "Après la douche, dehors plus sec", "Un geste qui vaut le coup, avec sa durée.",
    view("douche", "Salle de bain", {"outdoor_temperature": 12, "outdoor_humidity": 70, "rain": False, "pollution": False, "wind_gust": 8,
                                     "indoor_temperature": 22, "indoor_humidity": 86}, {"fenetre_sdb": False}))
add("purif", "Tout va bien, le purificateur tourne", "Avant : « Le purificateur filtre » défilait dans le bandeau.",
    view("purif", "Salon", {**AUTUMN, "outdoor_humidity": 60, "indoor_temperature": 21.5, "indoor_humidity": 55, "co2": 650, "pm25": 18, "purifier": True}, {"fenetre_ouest": False}))
out = Path(__file__).with_name("scenes.json")
out.write_text(json.dumps({"generated": NOW.isoformat(), "scenes": scenes}, ensure_ascii=False, default=list, indent=1))
for sc in scenes:
    a = sc["view"]["assessment"]
    print(f"{sc['id']:9} {a['action']:8} {a['reason']:22} {a['level']}")
