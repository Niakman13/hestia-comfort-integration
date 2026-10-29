"""The « Lumières » settings keep only what makes sense: a light, its looks per state, the home or room mode."""
import unittest


from custom_components.hestia_comfort.configuration import clean_lights


class LightsTest(unittest.TestCase):
    def test_a_light_keeps_its_looks_and_its_safeguards(self):
        lights = clean_lights({"mode": "home", "home": {"entity_id": "light.bandeau", "states": {"action": {"colour": "#f1b277", "effect": "Breathe", "brightness": 140}}}})
        rule = lights["home"]
        self.assertEqual(rule["states"]["action"], {"colour": "#f1b277", "effect": "Breathe", "brightness": 100})
        self.assertTrue(rule["night"] and rule["presence"])
        self.assertFalse(rule["wake"])

    def test_anything_but_a_light_is_dropped(self):
        lights = clean_lights({"mode": "rooms", "home": {"entity_id": "switch.prise"}, "rooms": {"a": {"entity_id": "light.lampe"}, "b": {"entity_id": 3}}})
        self.assertEqual(lights["mode"], "rooms")
        self.assertIsNone(lights["home"])
        self.assertEqual(list(lights["rooms"]), ["a"])

    def test_settings_that_are_not_a_dict_are_refused(self):
        with self.assertRaises(ValueError):
            clean_lights([])


if __name__ == "__main__":
    unittest.main()
