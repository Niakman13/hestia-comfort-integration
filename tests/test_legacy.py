"""The former technical name: a shared air's id keeps its rooms' entry ids in order once they change."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.legacy import rekey  # noqa: E402

A, B = "01M4ZNA8QE6NYZKBW8BR8W8QAJ", "01M55XYZPFS0AR3PAAQV88VM74"


class Rekey(unittest.TestCase):
    def test_a_shared_air_names_its_rooms_in_order(self):
        self.assertEqual(rekey(f"volume_{B}_{A}"), f"volume_{A}_{B}")
        self.assertEqual(rekey(f"volume_{B}_{A}_trop_humide"), f"volume_{A}_{B}_trop_humide")

    def test_older_entry_ids_too(self):
        old, new = "f" * 32, "0" * 32
        self.assertEqual(rekey(f"volume_{old}_{new}_advice"), f"volume_{new}_{old}_advice")

    def test_anything_else_stays(self):
        for value in (f"{B}_advice", "room_abc", "volume_salon", f"volume_{A}"):
            self.assertEqual(rekey(value), value)


if __name__ == "__main__":
    unittest.main()
