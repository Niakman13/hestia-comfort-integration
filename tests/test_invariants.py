"""Every situation, every time: the engine's advice must stay coherent whatever the combination.

Born from the audit of 20 October 2026 (12 960 then 32 400 situations through the real engine and card):
it caught a « close » shown as « nothing to do », an airing kept open that dried nothing, a hot room left
open to a hotter outside, a cold room or damp walls told « nothing to do », and two rooms of one air telling
two stories. Each rule below is one of those, checked on every combination.
"""
from datetime import datetime, timezone
import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.assessment import REASONS, Opening, Settings, Sun, absolute_humidity, assess
from engine.sources import Reading
from engine.volume import arbitrate

NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
SETTINGS = Settings(minimum=20, maximum=24, humidity_high=60, co2_potential=800, co2_action=1000, co2_urgent=1500)
OUTSIDE = {"winter": (3, 85), "humid_autumn": (17, 91), "dry_autumn": (15, 55), "hot_summer": (31, 40), "summer_night": (18, 70)}
ROOM = {"cold": 19.0, "comfortable": 21.5, "hot": 26.5}
SOURCE = {"outside": 0.0, "inside": 2.0, "strong": 4.0}
CO2 = {"ok": 600, "high": 1100, "urgent": 1700}
WINDOW = {"closed": (False, False), "open": (True, False), "open_sheltered": (True, True)}
WEATHER = ("calm", "rain", "rain_imminent", "rain_later", "rain_hourly", "gusts", "storm_forecast", "bad_air")
EQUIPMENT = ("none", "ventilation_off", "heating_off_home", "heating_off_away", "heating_on")
WINDOW_MODEL = {"ordinary": None, "renews_little": {"tau": 170.0, "residual": 1.5, "rebound": 0.4, "openings": 10}}
# What the card shows as « Rien à faire » (card/src/views/room.ts, advice()): the banner only carries gestures,
# the rest is said under it, in « À savoir ».
CARD_QUIET = ("drying_unavailable", "drying_slow", "drying_night", "drying_alone", "opening_blocked", "cooling_unavailable", "precool_later")


def nothing_to_do(a):
    if a["action"] == "fermer":
        return False
    ventilation_off = ((a["features"].get("air") or {}).get("ventilation") or {}).get("on") is False
    return (a["reason"] == "within_comfort" or (a["reason"] in CARD_QUIET and a["level"] in ("calm", "neutral"))
            or a["reason"] in ("humid_outdoor", "open_neutral", "drying_unavailable")
            or (a["reason"] == "drying_slow" and not ventilation_off)
            or (a["reason"] == "heat_needed" and a["level"] != "action"))


def situation(outside, room, source, co2, window, weather, equipment, model, volume=None):
    te, he = OUTSIDE[outside]
    ti = ROOM[room]
    hi = min(99.0, (absolute_humidity(te, he) + SOURCE[source]) / absolute_humidity(ti, 100) * 100)
    values = {"indoor_temperature": ti, "outdoor_temperature": te, "indoor_humidity": hi, "outdoor_humidity": he,
              "co2": CO2[co2], "rain": weather == "rain", "pollution": weather == "bad_air",
              "wind_gust": 60 if weather == "gusts" else 10, "window:w": WINDOW[window][0]}
    if equipment == "ventilation_off":
        values["ventilation"] = False
    if equipment.startswith("heating"):
        values["heating"] = "heating" if equipment == "heating_on" else "off"
    readings = {k: Reading(v, "valid", "sensor.x") for k, v in values.items()}
    outlook = {"station": ("rain_rate", "wind_gust")}
    outlook.update({"rain_imminent": {"rain": {"minutes": 10, "precision": "minute"}}, "rain_later": {"rain": {"minutes": 50, "precision": "minute"}},
                    "rain_hourly": {"rain": {"minutes": 0, "precision": "hour"}}, "storm_forecast": {"storm": True}}.get(weather, {}))
    context = {"heated": True, "occupied": {"heating_off_home": True, "heating_off_away": False}.get(equipment)}
    if WINDOW_MODEL[model]:
        context["drying_model"] = WINDOW_MODEL[model]
    if volume:
        context["volume"] = volume
    sun = Sun(-10 if outside == "summer_night" else 35, 200)
    return assess(readings, SETTINGS, None, {"w": Opening(exposure="O", sheltered=WINDOW[window][1])}, sun, outlook, NOW, context=context).to_dict()


class EveryCombination(unittest.TestCase):
    def test_every_situation_is_coherent(self):
        broken, seen = {}, set()
        def check(rule, ok, case, a):
            if not ok:
                broken.setdefault(rule, (case, a["action"], a["reason"], a["level"]))
        for case in itertools.product(OUTSIDE, ROOM, SOURCE, CO2, WINDOW, WEATHER, EQUIPMENT, WINDOW_MODEL):
            outside, room, source, co2, window, weather, equipment, model = case
            a = situation(*case)
            act, reason, level = a["action"], a["reason"], a["level"]
            seen.add(reason)
            opened, exposed = window != "closed", window == "open"
            te, ti = OUTSIDE[outside][0], ROOM[room]
            drying = a["features"].get("drying") or {}
            check("an exposed open window under rain (now or within 20 min) is closed",
                  not (exposed and weather in ("rain", "rain_imminent")) or act == "fermer", case, a)
            check("an open window under gusts or bad outdoor air is closed", not (opened and weather in ("gusts", "bad_air")) or act == "fermer", case, a)
            check("never « open » under rain, gusts or bad outdoor air", not (act == "ouvrir" and weather in ("rain", "rain_imminent", "gusts", "bad_air")), case, a)
            check("an open window kept for drying still dries", not (opened and act == "ok" and reason == "drying_possible") or drying.get("gain", 99) >= 1, case, a)
            check("an airing proposed for drying is worth it", not (act == "ouvrir" and reason == "drying_possible") or drying.get("gain", 99) >= 5, case, a)
            check("a hot room open to a hotter outside is closed", not (opened and room == "hot" and te > ti and co2 == "ok") or act == "fermer", case, a)
            check("a cold room open to a colder outside is closed", not (opened and room == "cold" and te < ti - 2 and co2 == "ok") or act == "fermer", case, a)
            check("an urgent CO₂ is never calm", not (co2 == "urgent" and level == "calm"), case, a)
            check("a hot room is never « nothing to do »", not (room == "hot" and nothing_to_do(a)), case, a)
            # One degree under the range is within the room's tolerance: said in « À savoir », never « Rallumez ».
            check("a room just under its range is never told to switch the heating on",
                  not (room == "cold" and reason == "heat_needed" and act != "fermer") or level in ("calm", "neutral"), case, a)
            check("a gesture to make is never shown as « nothing to do »", not (level in ("action", "urgent") and nothing_to_do(a)), case, a)
            # 27 October: 19 °C inside, much milder outside, and the card said « opening would bring nothing ».
            check("a cold room with a clearly milder outside is never told that opening brings nothing",
                  not (room == "cold" and te >= ti + SETTINGS.cooling_delta and weather in ("calm", "rain_later") and co2 == "ok"
                       and equipment in ("none", "heating_off_home") and outside != "summer_night" and not opened) or act == "ouvrir", case, a)
            check("a cold room in an empty home stays blue",
                  not (room == "cold" and equipment == "heating_off_away" and reason == "heat_needed" and act != "fermer") or level in ("calm", "neutral"), case, a)
        self.assertEqual(broken, {})
        # Every reason the engine gives is one the « Raison » sensor knows: Home Assistant refuses the others.
        self.assertEqual(sorted(r for r in seen if r not in REASONS), [])

    def test_rooms_of_one_air_never_tell_two_stories(self):
        different = []
        for outside, weather, kitchen_open, salon_open, steam, co2 in itertools.product(
                OUTSIDE, ("calm", "rain_imminent", "storm_forecast"), (False, True), (False, True), (0.0, 2.0), (600, 1100)):
            te, he = OUTSIDE[outside]
            ae = absolute_humidity(te, he)
            rooms = [(21.1, min(99, ae / absolute_humidity(21.1, 100) * 100)), (21.6, min(99, (ae + steam) / absolute_humidity(21.6, 100) * 100))]
            volume = {"water": sum(absolute_humidity(t, h) for t, h in rooms) / 2, "temperature": 21.35, "drying_model": None}
            def room(ti, hi, room_co2):
                values = {"indoor_temperature": ti, "outdoor_temperature": te, "indoor_humidity": hi, "outdoor_humidity": he, "co2": room_co2,
                          "rain": False, "pollution": False, "wind_gust": 10, "window:salon": salon_open, "window:cuisine": kitchen_open}
                outlook = {"station": ("rain_rate", "wind_gust"), **({"rain": {"minutes": 10, "precision": "minute"}} if weather == "rain_imminent" else {}),
                           **({"storm": True} if weather == "storm_forecast" else {})}
                return assess({k: Reading(v, "valid", "s") for k, v in values.items()}, SETTINGS, None,
                              {"salon": Opening(exposure="O"), "cuisine": Opening(exposure="E")}, Sun(30, 200), outlook, NOW,
                              context={"volume": volume}).to_dict()
            salon, kitchen = room(*rooms[0], co2), room(*rooms[1], 600)
            shown = lambda a: (a["action"], (a["features"].get("volume") or {}).get("reason", a["reason"]))
            s, k = arbitrate(salon, [("Cuisine", kitchen)]), arbitrate(kitchen, [("Salon", salon)])
            if shown(s) != shown(k):
                different.append(((outside, weather, kitchen_open, salon_open, steam, co2), shown(s), shown(k)))
        self.assertEqual(different, [])


if __name__ == "__main__":
    unittest.main()
