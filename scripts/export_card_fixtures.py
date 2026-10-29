"""Render approved fictional situations using the real Python engine."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components/hestia_comfort"))
from engine.assessment import assess
from engine.sources import normalize

now = datetime.now(timezone.utc)
scenarios = json.loads((ROOT / "tests/fixtures/approved-scenarios.json").read_text())
fixtures = []
for scene in scenarios:
    rows = {}
    for key, field, kind, unit in (
        ("indoor_temperature", "ti", "temperature", "°C"), ("outdoor_temperature", "te", "temperature", "°C"),
        ("indoor_humidity", "hi", "humidity", "%"), ("outdoor_humidity", "he", "humidity", "%"),
        ("co2", "co2", "co2", "ppm"), ("rain", "rain", "rain", None), ("pollution", "pollution", "pollution", None),
    ):
        rows[key] = normalize(kind, scene[field], unit, source=f"sensor.demo_{key}", reported_at=now, now=now)
    for i in range(2):
        rows[f"window:binary_sensor.demo_{i}"] = normalize("window", scene["windows"]>i, source=f"binary_sensor.demo_{i}", reported_at=now, now=now)
    if scene["heat"] != "absent":
        rows["heating"] = normalize("heating", "heating" if scene["heat"] == "stale" else scene["heat"],
            source="climate.demo", reported_at=now-timedelta(hours=1) if scene["heat"] == "stale" else now, now=now)
    fixtures.append({"id": scene["id"], "name": scene["name"], "view": {
        "version": 1, "entry_id": "demo-salon", "area_id": "demo-salon", "title": "Salon",
        "computed_at": now.isoformat(), "assessment": assess(rows).to_dict(),
        "observations": {k: asdict(r) for k,r in rows.items()}}})
output = ROOT / "dist/card-fixtures.json"
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2)+"\n")
print(output)
