"""Salon · Cuisine as one card: situations computed by the real engine (run: python scenes.py)."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "custom_components" / "niak_comfort"))
from engine.assessment import Opening, Settings, Sun, absolute_humidity, assess
from engine.home import synthesis
from engine.sources import Reading
from engine.volume import arbitrate

NOW = datetime(2026, 10, 20, 14, tzinfo=timezone.utc)
S = Settings(minimum=20, maximum=24, humidity_high=60, co2_potential=800, co2_action=1000, co2_urgent=1500)
UNITS = {"indoor_temperature": "°C", "outdoor_temperature": "°C", "indoor_humidity": "%", "outdoor_humidity": "%", "co2": "ppm", "pm25": "µg/m³", "voc": None, "solar": "W/m²"}
OUT = {"outdoor_temperature": 18.1, "outdoor_humidity": 88, "rain": False, "pollution": False, "wind_gust": 8, "solar": 75}
WINDOWS = {"binary_sensor.fenetre_ouest": ("O", "Fenêtre Ouest"), "binary_sensor.porte_fenetre_sd": ("S", "Porte fenêtre SD"),
           "binary_sensor.porte_fenetre_sg": ("S", "Porte fenêtre SG"), "binary_sensor.fenetre_c": ("E", "Fenêtre cuisine")}
FLOOR = {"floor_id": "rdc", "name": "Rez-de-chaussée", "level": 0}


def pair(sid, salon, cuisine, opened=(), outlook=None):
    water = (absolute_humidity(salon["indoor_temperature"], salon["indoor_humidity"]) + absolute_humidity(cuisine["indoor_temperature"], cuisine["indoor_humidity"])) / 2
    volume = {"water": water, "temperature": (salon["indoor_temperature"] + cuisine["indoor_temperature"]) / 2,
              "drying_model": {"tau": 37.2, "residual": 1.5, "rebound": 0.4, "openings": 31}}
    views = {}
    for key, title, values in (("salon", "Salon", salon), ("cuisine", "Cuisine", cuisine)):
        readings = {k: Reading(v, "valid", f"sensor.{key}_{k}", NOW.isoformat()) for k, v in {**OUT, **values}.items()}
        for w in WINDOWS:
            readings[f"window:{w}"] = Reading(w in opened, "valid", w, NOW.isoformat())
        a = assess(readings, S, None, {w: Opening(exposure=e, sheltered=e == "S") for w, (e, _) in WINDOWS.items()}, Sun(30, 200),
                   outlook or {"station": ("rain_rate", "wind_gust")}, NOW, context={"volume": volume, "voc_threshold": {"value": 150, "unit": ""}}).to_dict()
        views[key] = {"version": 1, "entry_id": f"{sid}-{key}", "area_id": key, "title": title, "comfort_minimum": 20, "computed_at": NOW.isoformat(),
                      "assessment": a, "observations": {k: {**asdict(r), "unit": UNITS.get(k)} for k, r in readings.items()},
                      "names": {w: n for w, (_, n) in WINDOWS.items()}, "starting": False, "floor": FLOOR}
    for key, other, other_title in (("salon", "cuisine", "Cuisine"), ("cuisine", "salon", "Salon")):
        own = views[key]["assessment"]
        settled = arbitrate(own, [(other_title, views[other]["assessment"])])
        if (settled["features"].get("volume") or {}).get("lead"):
            settled["features"]["volume"]["observations"] = views[other]["observations"]
        views[key]["settled"] = settled
    for key, other, other_title in (("salon", "cuisine", "Cuisine"), ("cuisine", "salon", "Salon")):
        views[key]["assessment"] = views[key].pop("settled")
        views[key]["volume"] = [{"entry_id": f"{sid}-{other}", "title": other_title}]
        views[key]["volume_name"] = "Salon · Cuisine"
    return views["salon"], views["cuisine"]


scenes = []
def add(sid, title, note, salon, cuisine, **kw):
    s, c = pair(sid, salon, cuisine, **kw)
    scenes.append({"id": sid, "title": title, "note": note, "salon": s, "cuisine": c})

add("calme", "Aujourd’hui : fenêtre de la cuisine ouverte pour rien", "Une carte, un bandeau ; les mesures de chaque pièce dessous.",
    {"indoor_temperature": 21.1, "indoor_humidity": 73, "co2": 620, "pm25": 4, "voc": 120}, {"indoor_temperature": 21.6, "indoor_humidity": 78},
    opened=("binary_sensor.fenetre_c",))
add("aerer", "COV élevés au salon, tout est fermé", "Le salon mène : son geste vaut pour la cuisine aussi.",
    {"indoor_temperature": 21.1, "indoor_humidity": 73, "co2": 680, "pm25": 5, "voc": 199}, {"indoor_temperature": 21.6, "indoor_humidity": 78})
add("encours", "Porte-fenêtre ouverte : aération en cours", "Le geste suivi se voit tout de suite.",
    {"indoor_temperature": 21.0, "indoor_humidity": 72, "co2": 690, "pm25": 4, "voc": 190}, {"indoor_temperature": 21.5, "indoor_humidity": 77},
    opened=("binary_sensor.porte_fenetre_sd",))
add("pluie", "Pluie dans 10 min, fenêtre de la cuisine ouverte", "La fenêtre exposée est dans la cuisine : la carte commune le dit.",
    {"indoor_temperature": 21.1, "indoor_humidity": 70, "co2": 650, "pm25": 4, "voc": 110}, {"indoor_temperature": 21.6, "indoor_humidity": 76},
    opened=("binary_sensor.fenetre_c",), outlook={"station": ("rain_rate", "wind_gust"), "rain": {"minutes": 10, "precision": "minute"}})
# The home card, built from the first situation and a few other rooms.
salon, cuisine = scenes[1]["salon"], scenes[1]["cuisine"]
def room(eid, title, t, h, floor):
    readings = {k: Reading(v, "valid", f"sensor.{eid}_{k}", NOW.isoformat()) for k, v in {**OUT, "indoor_temperature": t, "indoor_humidity": h}.items()}
    a = assess(readings, S, None, {}, Sun(30, 200), {}, NOW).to_dict()
    return {"version": 1, "entry_id": eid, "area_id": eid, "title": title, "comfort_minimum": 20, "computed_at": NOW.isoformat(), "assessment": a,
            "observations": {k: {**asdict(r), "unit": UNITS.get(k)} for k, r in readings.items()}, "names": {}, "starting": False, "floor": floor}
up = {"floor_id": "etage", "name": "Étage 1", "level": 1}
rooms = [salon, cuisine, room("buanderie", "Buanderie", 20.0, 69, FLOOR), room("chambre-a", "Chambre A", 20.7, 74, up), room("chambre-m", "Chambre M", 20.7, 73, up)]
home = synthesis([{**r, "comfort_minimum": 20} for r in rooms])
out = Path(__file__).with_name("scenes.json")
out.write_text(json.dumps({"generated": NOW.isoformat(), "scenes": scenes, "home": {"version": 1, "home": home, "rooms": rooms},
                           "entries": [{"entry_id": "buanderie", "title": "Buanderie", "area_id": "buanderie", "volume": [], "volume_name": None},
                                       {"entry_id": "chambre-a", "title": "Chambre A", "area_id": "chambre_a", "volume": [], "volume_name": None},
                                       {"entry_id": "cuisine", "title": "Cuisine", "area_id": "cuisine", "volume": ["salon"], "volume_name": "Salon · Cuisine"},
                                       {"entry_id": "salon", "title": "Salon", "area_id": "salon", "volume": ["cuisine"], "volume_name": "Salon · Cuisine"},
                                       {"entry_id": "sdb", "title": "Salle de bain", "area_id": "sdb", "volume": [], "volume_name": None}]},
                          ensure_ascii=False, default=list, indent=1))
for sc in scenes:
    print(sc["id"], "| salon:", sc["salon"]["assessment"]["action"], sc["salon"]["assessment"]["reason"], "| cuisine:", sc["cuisine"]["assessment"]["action"], sc["cuisine"]["assessment"]["reason"])
