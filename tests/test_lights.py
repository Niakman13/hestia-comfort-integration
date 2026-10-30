"""The « Lumières » settings keep only what makes sense: a light, its looks per state, the home or room mode."""
import unittest


from custom_components.hestia_comfort.configuration import clean_lights


class LightsTest(unittest.TestCase):
    def test_a_light_keeps_its_looks_and_its_safeguards(self):
        lights = clean_lights({"mode": "home", "home": {"entity_id": "light.bandeau", "states": {"action": {"colour": "#f1b277", "effect": "Breathe", "brightness": 140}}}})
        rule = lights["home"]
        self.assertEqual(rule["states"]["action"], {"colour": "#f1b277", "effect": "Breathe", "brightness": 100, "speed": "normal"})
        self.assertTrue(rule["night"] and rule["presence"])
        self.assertFalse(rule["wake"])

    def test_a_wled_effect_keeps_its_speed(self):
        looks = {"action": {"effect": "Heartbeat", "speed": "fast"}, "benefit": {"effect": "Breathe", "speed": "très vite"}}
        rule = clean_lights({"mode": "home", "home": {"entity_id": "light.wled_segment_2", "states": looks}})["home"]
        self.assertEqual(rule["states"]["action"]["speed"], "fast")
        self.assertEqual(rule["states"]["benefit"]["speed"], "normal")

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
