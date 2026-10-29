"""« Prochaines heures » on a shared air: the card draws the graph of the room whose advice it shows."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from custom_components.hestia_comfort.coordinator import ComfortCoordinator  # noqa: E402
from engine.assessment import assess  # noqa: E402
from test_engine import zone  # noqa: E402

AIRING = [{"subject": "temperature", "kind": "air", "needed": True}]
TREND = [{"subject": "temperature", "kind": "trend", "needed": False}]


def room(own, partners):
    entries = {p["entry_id"]: SimpleNamespace(runtime_data=c) for p, c in partners}
    return SimpleNamespace(partners=[p for p, _ in partners], _own_gesture=None,
                           hass=SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=entries.get)))


class VolumeHorizon(unittest.TestCase):
    def test_the_leading_rooms_graph_comes_with_its_advice(self):
        salon = assess(zone(co2=1300, **{"window:a": True})).to_dict()
        kitchen = assess(zone(indoor_temperature=20.5, outdoor_temperature=8, **{"window:a": True})).to_dict()
        salon["features"]["horizon"], kitchen["features"]["horizon"] = AIRING, TREND
        leader = SimpleNamespace(own=salon, data={"observations": {}})
        settled = ComfortCoordinator._settle(room(kitchen, [({"entry_id": "s", "title": "Salon"}, leader)]), kitchen)
        self.assertEqual(settled["features"]["volume"]["lead"], "Salon")
        self.assertEqual(settled["features"]["horizon"], AIRING)
        # The room keeps its own graph for itself: only the card's view changes.
        self.assertEqual(kitchen["features"]["horizon"], TREND)


if __name__ == "__main__":
    unittest.main()
