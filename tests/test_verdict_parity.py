"""The entities say what the card says: every audited situation, and variants reaching each branch, through the card's
TypeScript (card/scripts/verdict-cases.mjs) and the Python port (engine/verdict.py)."""
import copy
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "niak_comfort"))
from engine.verdict import advice, humidity_label, verdict  # noqa: E402
from engine.assessment import REASONS  # noqa: E402

WORDS = {"normal": "Dans votre plage", "slightly_humid": "Légèrement humide", "humid": "Air humide", "very_humid": "Très humide",
         "slightly_dry": "Légèrement sec", "dry": "Air sec", "very_dry": "Très sec"}
FEATURES = {
    "learned": [None, {"measure": "humidity", "now": 70, "after": 62, "minutes": 12, "openings": 9},
                {"closing": True, "measure": "temperature", "now": 21, "after": 19.5, "minutes": 30, "openings": 6}],
    "drying": [None, {"now": 72, "gain": 6, "openings": 7, "later": {"time": "2026-10-27T21:00:00+00:00", "after": 61, "minutes": 10}},
               {"now": 72, "gain": 0.4, "openings": 2}],
    "ventilation": [None, {"duration_minutes": {"min": 5, "max": 10}}, {"duration_minutes": {"min": 5, "max": 10}, "opened_minutes": 4.5},
                    {"duration_minutes": {"min": 5, "max": 10}, "opened_minutes": 12}],
    "rain_ahead": [None, {"minutes": 17}],
    "warmth": [None, {"slight": False, "heating": None, "occupied": True}],
    "air": [None, {"ventilation": {"on": False}}],
    "humidity": [None, {"status": "high", "degree": 3}, {"status": "low", "degree": 1}, {"status": "normal"}],
    "season": [None, {"group": "winter"}],
}
SLOTS = [None, {"kind": "open", "time": "2026-10-27T00:00:00+00:00", "temperature": 17.5, "wind_bearing": 95}]


def variants(base, count=6000):
    """Every reason and action with features drawn at random, starting and silent sensors included: each branch of the banner."""
    rng = random.Random(7)
    out = []
    for reason, action, level in itertools.product((*REASONS, "shutter_protection"), ("ok", "ouvrir", "fermer", "attendre"),
                                                    ("calm", "benefit", "action", "neutral")):
        for _ in range(max(1, count // (len(REASONS) * 16))):
            v = copy.deepcopy(rng.choice(base))
            a = v["assessment"]
            a.update(reason=reason, action=action, level=level, needs=rng.choice([[], ["dry"], ["heat"], ["air", "cool"], ["heat", "dry"]]),
                     slot=rng.choice(SLOTS), open_first=rng.choice([[], ["binary_sensor.w"]]), missing=rng.choice([[], ["co2"], ["co2", "voc"],
                     ["indoor_temperature"], ["co2", "voc", "rain"]]))
            a["features"] = {**(a.get("features") or {}), **{k: rng.choice(options) for k, options in FEATURES.items()}}
            v["starting"] = rng.random() < 0.3
            for key in a["missing"]:
                v["observations"].setdefault(key, {"quality": "missing", "value": None})
            out.append(v)
    return out


@unittest.skipIf(not shutil.which("node") or not (ROOT / "card" / "node_modules" / "esbuild").exists(), "card not built")
class VerdictParity(unittest.TestCase):
    def test_entities_say_what_the_card_says(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.json"
            subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "audit_card_situations.py"), str(cases)], check=True, capture_output=True)
            audited = json.loads(cases.read_text())
            base = [v for c in audited for v in c["rooms"]]
            views = base + variants(base)
            cases.write_text(json.dumps([{"rooms": views}]))
            card = json.loads(subprocess.run(["node", str(ROOT / "card" / "scripts" / "verdict-cases.mjs"), str(cases)], check=True,
                                             capture_output=True, text=True, cwd=ROOT / "card", env={**os.environ, "TZ": "UTC"}).stdout)
        self.assertGreater(len(base), 1000)
        self.assertEqual(len(card), len(views))
        utc = lambda d: d.astimezone(timezone.utc)  # noqa: E731
        for view, expected in zip(views, card):
            a, v, label = advice(view, utc), verdict(view, utc), humidity_label(view)
            words = "Trop humide" if label == "humid" and expected["humidity"] == "Trop humide" else WORDS.get(label)
            said = {"title": a["title"], "disk": a["disk"], "cap": a.get("cap"), "learned": a.get("learned"), "pill": v["pill"],
                    "level": v["level"], "humidity": words}
            self.assertEqual(said, expected, (view["title"], view["assessment"]["reason"], view["assessment"]["action"]))


if __name__ == "__main__":
    unittest.main()
