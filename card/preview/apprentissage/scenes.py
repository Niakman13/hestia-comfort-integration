"""Learned versus estimated advice, with the twins really learned at home on 20 Oct. (run: python scenes.py)."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "custom_components" / "hestia_comfort"))
from engine.assessment import Opening, Settings, Sun, assess
from engine.sources import Reading

NOW = datetime(2026, 10, 21, 10, tzinfo=timezone.utc)
S = Settings(minimum=20, maximum=24, humidity_high=60, co2_potential=800, co2_action=1000, co2_urgent=1500)
UNITS = {"indoor_temperature": "°C", "outdoor_temperature": "°C", "indoor_humidity": "%", "outdoor_humidity": "%", "co2": "ppm"}
DRY = {"outdoor_temperature": 14, "outdoor_humidity": 62, "rain": False, "pollution": False, "wind_gust": 8}
HUMID = {"outdoor_temperature": 16.5, "outdoor_humidity": 90, "rain": False, "pollution": False, "wind_gust": 8}
# What the twins had learned at home on 20 Oct. (hestia_comfort/twins).
TWINS = {"cuisine": (10.0, 0.24, 1.5), "chambre_m": (10.1, 0.35, 0.7), "chambre_al": (10.0, 1.14, 4.7), "chambre_p": (10.1, None, None), "nouvelle": (3.2, None, None)}


def view(eid, title, values, window, opened=False, context=None, twin=None, learned=None):
    readings = {k: Reading(v, "valid", f"sensor.{eid}_{k}", NOW.isoformat()) for k, v in values.items()}
    readings[f"window:{window}"] = Reading(opened, "valid", window, NOW.isoformat())
    a = assess(readings, S, None, {window: Opening(exposure="O")}, Sun(25, 150), {"station": ("rain_rate", "wind_gust")}, NOW, context=context or {}).to_dict()
    if learned:
        a["features"]["learned"] = learned
    days, temperature, humidity = TWINS[twin]
    ready = days >= 3
    return {"version": 1, "entry_id": eid, "area_id": eid, "title": title, "comfort_minimum": 20, "computed_at": NOW.isoformat(), "assessment": a,
            "observations": {k: {**asdict(r), "unit": UNITS.get(k)} for k, r in readings.items()}, "names": {window: "Fenêtre"}, "starting": False,
            "twin": {"status": "ready" if ready else "learning", "days": days, "samples": int(days * 48), "next_hour": None,
                     "precision": {"hours": 24, "temperature": temperature, "humidity": humidity} if temperature is not None else None}}


scenes = [
    {"id": "appris", "title": "Conseil appris", "note": "La cuisine est apprise : Hestia annonce le résultat, d’après ses 31 aérations.",
     "view": view("appris", "Cuisine", {**DRY, "indoor_temperature": 21.6, "indoor_humidity": 76}, "fenetre_c", twin="cuisine",
                  context={"drying_model": {"tau": 37.2, "residual": 1.5, "rebound": 0.4, "openings": 31}},
                  learned={"now": 76, "after": 68, "minutes": 15, "measure": "humidity", "openings": 31, "days": 10,
                           "precision": {"temperature": 0.24, "humidity": 1.5}})},
    {"id": "calme", "title": "Pièce apprise, rien à faire", "note": "Pas de geste, donc pas de repère : la carte reste sobre.",
     "view": view("calme", "Chambre M", {**DRY, "indoor_temperature": 20.9, "indoor_humidity": 55}, "fenetre_m", twin="chambre_m")},
    {"id": "imprecis", "title": "Prévisions pas encore assez justes", "note": "Chambre AL : ±1,1 °C sur 24 h. Le conseil est estimé, À savoir le dit.",
     "view": view("imprecis", "Chambre AL", {**HUMID, "indoor_temperature": 20.3, "indoor_humidity": 72}, "fenetre_al", opened=True, twin="chambre_al")},
    {"id": "verifier", "title": "Pas encore vérifiable", "note": "Chambre P : il manque 24 h continues (contact muet par moments).",
     "view": view("verifier", "Chambre P", {**HUMID, "indoor_temperature": 20.5, "indoor_humidity": 87, "ventilation": False}, "fenetre_p", twin="chambre_p",
                  context={"drying_model": {"tau": 171.7, "residual": 1.5, "rebound": 0.4, "openings": 4}})},
    {"id": "nouvelle", "title": "Pièce nouvelle, en apprentissage", "note": "Trois jours de mesures : apprentissage en cours.",
     "view": view("nouvelle", "Bureau", {**DRY, "indoor_temperature": 21.5, "indoor_humidity": 50, "co2": 1180}, "fenetre_b", twin="nouvelle")},
]
Path(__file__).with_name("scenes.json").write_text(json.dumps({"scenes": scenes}, ensure_ascii=False, default=list, indent=1))
for s in scenes:
    a = s["view"]["assessment"]
    print(s["id"], a["action"], a["reason"], a["level"])
