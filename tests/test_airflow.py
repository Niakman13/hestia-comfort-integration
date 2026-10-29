"""Where the air goes through: the best openings by the rule, then by what each combination taught."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine import airflow
from engine.assessment import Opening, assess
from engine.wind import plan
from test_engine import zone

T0 = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
o = lambda e, opened, exp, side, kind="window", avoid=None: {"entity_id": e, "open": opened, "exposure": exp, "wind_side": side,
                                                            "kind": kind, "flags": [], "avoid": avoid}


def salon(*opened):
    # The Salon · Cuisine of 26 Oct., wind from the north: no opening faces it.
    rooms = [o("ouest", False, "O", "side"), o("sd", False, "S", "leeward", "french"),
             o("sg", False, "S", "leeward", "french"), o("cuisine", False, "E", "side")]
    return [dict(r, open=True) if r["entity_id"] in opened else r for r in rooms]


class Plan(unittest.TestCase):
    def test_opposite_facades_cross_even_with_a_side_wind(self):
        chosen = plan(salon())
        self.assertEqual(chosen["open"], ["ouest", "cuisine"])
        self.assertEqual(chosen["path"], "opposite")

    def test_completes_what_is_already_open(self):
        chosen = plan(salon("cuisine", "sd"))
        self.assertEqual((chosen["open"], chosen["keep"]), (["ouest"], ["sd", "cuisine"]))
        self.assertIsNone(chosen["faster"])  # nothing learned yet: no promise of speed

    def test_nothing_to_add_when_the_best_is_open(self):
        self.assertEqual(plan(salon("ouest", "cuisine"))["open"], [])

    def test_into_the_wind_first(self):
        chosen = plan([o("e", False, "E", "leeward"), o("w", False, "O", "windward")])
        self.assertEqual((chosen["open"], chosen["path"], chosen["into"]), (["w", "e"], "wind", "O"))

    def test_avoided_openings_are_left_shut_and_named(self):
        rooms = salon()
        rooms[0]["avoid"] = "rain"
        chosen = plan(rooms)
        self.assertNotIn("ouest", chosen["open"])
        self.assertEqual(chosen["avoid"], [{"entity_id": "ouest", "why": "rain"}])
        self.assertIsNone(plan([o("a", False, "O", "side", avoid="gust")]))

    def test_learned_speed_outweighs_the_rule(self):
        # This house: the two French windows together turned out faster than the opposite windows.
        flows = {"cuisine|ouest": {"rate": 2.0, "count": 4}, "sd|sg": {"rate": 5.0, "count": 3}, "sd": {"rate": 1.0, "count": 5}}
        chosen = plan(salon(), flows)
        self.assertEqual(sorted(chosen["open"]), ["sd", "sg"])
        self.assertEqual(chosen["learned"], 3)
        added = plan(salon("sd"), flows)
        self.assertEqual((added["open"], added["faster"]), (["sg"], 5.0))
        # Two airings are not enough to trust a combination.
        self.assertEqual(plan(salon(), {"sd|sg": {"rate": 9.0, "count": 2}})["open"], ["ouest", "cuisine"])


class Flows(unittest.TestCase):
    def test_rate_of_each_combination(self):
        contacts = {"a": [(T0, False), (T0 + timedelta(minutes=10), True), (T0 + timedelta(minutes=40), False)],
                    "b": [(T0, False), (T0 + timedelta(minutes=25), True), (T0 + timedelta(minutes=40), False)]}
        co2 = [(T0, 1220), (T0 + timedelta(minutes=10), 1220), (T0 + timedelta(minutes=20), 820),
               (T0 + timedelta(minutes=25), 720), (T0 + timedelta(minutes=35), 520)]
        found = airflow.flows(contacts, co2)
        self.assertEqual([f["combo"] for f in found], [["a"], ["a", "b"]])
        self.assertAlmostEqual(found[0]["rate"], 3.923, places=2)  # 800 → 300 ppm above outdoors in 15 min
        model = airflow.fit(found + found + found)
        self.assertEqual(model["a"]["count"], 3)

    def test_unreadable_airings_are_skipped(self):
        contacts = {"a": [(T0, True), (T0 + timedelta(minutes=30), False)]}
        self.assertEqual(airflow.flows(contacts, [(T0, 560), (T0 + timedelta(minutes=20), 500)]), [])   # too close to outdoors
        self.assertEqual(airflow.flows(contacts, [(T0, 1000), (T0 + timedelta(minutes=20), 1100)]), [])  # someone came in
        self.assertEqual(airflow.flows(contacts, [(T0 - timedelta(hours=1), 1000)]), [])                   # no report while open
        short = {"a": [(T0, True), (T0 + timedelta(minutes=5), False)]}
        self.assertEqual(airflow.flows(short, [(T0, 1200), (T0 + timedelta(minutes=4), 1000)]), [])

    def test_merge_keeps_recent_summaries(self):
        old = {"start": (T0 - timedelta(days=100)).isoformat(), "combo": ["a"], "rate": 1}
        new = {"start": T0.isoformat(), "combo": ["a"], "rate": 2}
        self.assertEqual(airflow.merge([old], [new], T0), [new])


class Assessment(unittest.TestCase):
    def test_rain_keeps_exposed_openings_out_of_the_plan(self):
        readings = {k: v for k, v in zone(co2=1300, rain=False, wind_bearing=0, **{"window:ouest": False, "window:sd": False}).items() if k != "window:a"}
        openings = {"ouest": Opening(exposure="O"), "sd": Opening(exposure="S", kind="french", sheltered=True)}
        dry = assess(readings, openings=openings, outlook={})
        self.assertEqual(sorted(dry.features["airflow"]["open"]), ["ouest", "sd"])
        wet = assess(readings, openings=openings, outlook={"rain": {"minutes": 40, "precision": "minute"}})
        self.assertEqual(wet.features["airflow"]["open"], ["sd"])
        self.assertEqual(wet.features["airflow"]["avoid"], [{"entity_id": "ouest", "why": "rain"}])


if __name__ == "__main__":
    unittest.main()
