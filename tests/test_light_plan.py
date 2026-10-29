"""« Lumières »: a light changes only under the person's safeguards, and goes back to how it was."""
import unittest

from custom_components.hestia_comfort.engine import light_plan as lp

RULE = {"entity_id": "light.bandeau", "wake": False, "night": True, "presence": True, "states": lp.DEFAULT_LOOKS}
DAY = {"hour": 15, "someone_home": True}


class LightPlanTest(unittest.TestCase):
    def test_a_light_already_on_takes_the_gestures_colour(self):
        action = lp.plan(RULE, "action", is_on=True, ours=False, **DAY)
        self.assertEqual(action, ("on", {"brightness_pct": 70, "rgb_color": [241, 178, 119]}))

    def test_a_light_off_stays_off_unless_waking_is_allowed_for_a_gesture(self):
        self.assertIsNone(lp.plan(RULE, "action", is_on=False, ours=False, **DAY))
        awake = {**RULE, "wake": True}
        self.assertEqual(lp.plan(awake, "action", is_on=False, ours=False, **DAY)[0], "on")
        # A chance to take is not worth turning a light on.
        self.assertIsNone(lp.plan(awake, "benefit", is_on=False, ours=False, **DAY))

    def test_all_is_well_puts_back_what_hestia_changed(self):
        self.assertEqual(lp.plan(RULE, "calm", is_on=True, ours=True, **DAY), ("restore", None))
        self.assertIsNone(lp.plan(RULE, "calm", is_on=True, ours=False, **DAY))

    def test_night_and_an_empty_home_stop_the_light(self):
        self.assertEqual(lp.plan(RULE, "action", is_on=True, ours=True, hour=23, someone_home=True), ("restore", None))
        self.assertIsNone(lp.plan(RULE, "action", is_on=True, ours=False, hour=15, someone_home=False))
        free = {**RULE, "night": False, "presence": False}
        self.assertEqual(lp.plan(free, "action", is_on=True, ours=False, hour=23, someone_home=False)[0], "on")

    def test_effects_are_sent_as_the_light_names_them(self):
        rule = {**RULE, "states": {**lp.DEFAULT_LOOKS, "action": {"colour": "#f1b277", "effect": "Breathe", "brightness": 70}}}
        self.assertEqual(lp.plan(rule, "action", is_on=True, ours=False, **DAY)[1]["effect"], "Breathe")
        self.assertEqual(lp.plan(RULE, "urgent", is_on=True, ours=False, **DAY)[1]["flash"], "long")

    def test_the_state_follows_the_banner(self):
        self.assertEqual(lp.state_key({"gesture": "keep_open", "mood": "calm"}), "airing")
        self.assertEqual(lp.state_key({"gesture": "none", "mood": "best"}), "calm")
        self.assertIsNone(lp.state_key({"gesture": "none", "mood": "neutral"}))

    def test_a_light_goes_back_as_it_was(self):
        before = lp.snapshot("on", {"brightness": 120, "rgb_color": (255, 200, 150), "effect": "Solid", "effect_list": ["Solid"]})
        self.assertEqual(lp.restore(before), ("turn_on", {"brightness": 120, "rgb_color": [255, 200, 150], "effect": "Solid"}))
        self.assertEqual(lp.restore(lp.snapshot("off", {})), ("turn_off", {}))


if __name__ == "__main__":
    unittest.main()
