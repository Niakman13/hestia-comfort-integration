"""The review's advice to heat follows a room's own minimum when it was set under 18 °C (forum, a bedroom kept at 16 °C)."""
from datetime import datetime, timedelta, timezone
import unittest

from custom_components.hestia_comfort.engine import review

START = datetime(2026, 1, 1, tzinfo=timezone.utc)
# Three weeks of January at 17 °C: out of every category of the standard, yet above a minimum of 16 °C.
COLD = {"temperature": [(START + timedelta(hours=h), 17.0) for h in range(21 * 24)]}
OUTSIDE = [(START + timedelta(hours=h), 5.0) for h in range(21 * 24)]


def advice(minimum):
    return [a for a in review.advice(review.room(COLD, OUTSIDE, timezone.utc, True, minimum)) if a["key"] == "heat_more"]


class ReviewMinimumTest(unittest.TestCase):
    def test_a_room_set_at_16_is_not_told_to_heat_at_17(self):
        self.assertEqual(advice(16), [])

    def test_a_room_with_the_usual_range_is_told_to_heat_under_18(self):
        found = advice(19)
        self.assertEqual((found[0]["below"], found[0]["share"]), (18.0, 100))

    def test_the_grade_keeps_the_standard(self):
        self.assertEqual(review.room(COLD, OUTSIDE, timezone.utc, True, 16)["themes"]["warmth"]["letter"], "E")


if __name__ == "__main__":
    unittest.main()
