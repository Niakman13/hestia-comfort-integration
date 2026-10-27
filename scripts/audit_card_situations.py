"""Every situation through the real engine, as views the card reads, for card/scripts/audit-coherence.mjs.

Usage: audit_card_situations.py <out.json>. One room alone, then two rooms of one air."""
from dataclasses import asdict
from datetime import datetime, timezone
import itertools, json, sys
from pathlib import Path
repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "custom_components" / "niak_comfort"))
from engine.assessment import Opening, Settings, Sun, absolute_humidity, assess
from engine.sources import normalize
from engine.volume import arbitrate
S = Settings(minimum=20, maximum=24, humidity_high=60, co2_potential=800, co2_action=1000, co2_urgent=1500)
NOON, NIGHT = datetime(2026, 10, 27, 12, tzinfo=timezone.utc), datetime(2026, 10, 27, 1, tzinfo=timezone.utc)
OUT_T, OUT_H = (3, 12, 17, 22.3, 31), (40, 54, 85)
ROOM_T, SRC = (18.7, 19.4, 20.3, 21.5, 26.5), (0.0, 1.3, 2.0, 4.0)
def view(title, ti, hi, te, he, co2, opened, weather, equipment, now, extra=None, volume=None):
    vals = {"indoor_temperature": ("temperature", ti, "°C"), "outdoor_temperature": ("temperature", te, "°C"),
            "indoor_humidity": ("humidity", hi, "%"), "outdoor_humidity": ("humidity", he, "%"), "co2": ("co2", co2, "ppm"),
            "rain": ("rain", weather == "rain", None), "pollution": ("pollution", False, None), "wind_gust": ("wind", 10, "km/h")}
    rows = {k: normalize(kind, v, u, source=f"sensor.{k}", reported_at=now, now=now) for k, (kind, v, u) in vals.items()}
    for w, o in (extra or {"w": opened}).items():
        rows[f"window:binary_sensor.{w}"] = normalize("window", o, source=f"binary_sensor.{w}", reported_at=now, now=now)
    if equipment in ("heating_off_home", "heating_off_away", "heating_on"):
        rows["heating"] = normalize("heating", "heating" if equipment == "heating_on" else "off", source="climate.x", reported_at=now, now=now)
    ctx = {"heated": True, "occupied": {"heating_off_home": True, "heating_off_away": False}.get(equipment)}
    if volume: ctx["volume"] = volume
    sun = Sun(-10 if now == NIGHT else 35, 200)
    a = assess(rows, S, None, {f"binary_sensor.{w}": Opening(exposure="O") for w in (extra or {"w": 0})}, sun,
               {"station": ("rain_rate", "wind_gust")}, now, context=ctx).to_dict()
    return {"version": 1, "entry_id": title, "area_id": title, "title": title, "comfort_minimum": 20, "computed_at": now.isoformat(),
            "assessment": a, "observations": {k: asdict(r) for k, r in rows.items()}}
cases = []
for te, he, ti, src, co2, opened, weather, eq, now in itertools.product(OUT_T, OUT_H, ROOM_T, SRC, (600, 1100), (False, True), ("calm", "rain"), ("none", "heating_off_home", "heating_on", "heating_off_away"), (NOON, NIGHT)):
    hi = min(99.0, (absolute_humidity(te, he) + src) / absolute_humidity(ti, 100) * 100)
    cases.append({"case": [te, he, ti, src, co2, opened, weather, eq, str(now.hour)], "rooms": [view("Salon", ti, hi, te, he, co2, opened, weather, eq, now)]})
# Two rooms of one air: their own temperatures, one window each, one judged volume.
for te, he, (t1, t2), src, w1, w2, eq, now in itertools.product(OUT_T, OUT_H, ((20.3, 19.6), (18.7, 21.5), (21.5, 26.5), (19.4, 20.3)), SRC, (False, True), (False, True), ("none", "heating_on", "heating_off_home"), (NOON, NIGHT)):
    ae = absolute_humidity(te, he)
    h1, h2 = (min(99.0, (ae + src) / absolute_humidity(t, 100) * 100) for t in (t1, t2))
    h2 = min(99.0, h2 + 6)
    volume = {"water": (absolute_humidity(t1, h1) + absolute_humidity(t2, h2)) / 2, "temperature": (t1 + t2) / 2, "drying_model": None}
    win = {"salon": w1, "cuisine": w2}
    s = view("Salon", t1, h1, te, he, 700, None, "calm", eq, now, win, volume)
    k = view("Cuisine", t2, h2, te, he, 700, None, "calm", eq, now, win, volume)
    sa, ka = s["assessment"], k["assessment"]
    s["assessment"], k["assessment"] = arbitrate(sa, [("Cuisine", ka)]), arbitrate(ka, [("Salon", sa)])
    cases.append({"case": ["pair", te, he, t1, t2, src, w1, w2, eq, str(now.hour)], "rooms": [s, k]})
json.dump(cases, open(sys.argv[1], "w"), ensure_ascii=False)
print(len(cases), "situations")
