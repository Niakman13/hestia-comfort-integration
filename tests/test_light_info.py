"""« Lumières »: a WLED strip as the hub shows it, on the real house (30 October): six segments of one LED, two driven by automations."""
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from custom_components.hestia_comfort import light_driver

MAC = "a0b7654d4ffc"
ENTRIES = [NS(entity_id="light.wled_principal", domain="light", platform="wled", unique_id=MAC, config_entry_id="w"),
           *[NS(entity_id=f"light.wled_segment_{n}", domain="light", platform="wled", unique_id=f"{MAC}_{n}", config_entry_id="w") for n in range(6)],
           *[NS(entity_id=f"number.wled_vitesse_{n}", domain="number", platform="wled", unique_id=f"{MAC}_speed_{n}", config_entry_id="w") for n in range(6)],
           NS(entity_id="light.salon", domain="light", platform="hue", unique_id="hue1", config_entry_id="h")]


class Registry:
    def async_get(self, entity_id):
        return next((e for e in ENTRIES if e.entity_id == entity_id), None)

    def async_get_entity_id(self, domain, platform, unique_id):
        return next((e.entity_id for e in ENTRIES if e.domain == domain and e.platform == platform and e.unique_id == unique_id), None)


def hass():
    segments = {0: NS(start=0, stop=9, length=9), **{n: NS(start=2 * n - 2, stop=2 * n - 1, length=1) for n in range(1, 6)}}
    entry = NS(runtime_data=NS(data=NS(state=NS(segments=segments))))
    return NS(config_entries=NS(async_get_entry=lambda _id: entry))


class LightInfoTest(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.object(light_driver.er, "async_get", return_value=Registry()),
                   mock.patch.object(light_driver.er, "async_entries_for_config_entry", side_effect=lambda _r, cid: [e for e in ENTRIES if e.config_entry_id == cid]),
                   mock.patch.object(light_driver, "_automations", side_effect=lambda _h, e: ["Led Alarme"] if e == "light.wled_segment_3" else [])]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_a_segment_says_its_leds_and_its_strip(self):
        info = light_driver.light_info(hass(), "light.wled_segment_2")
        self.assertEqual((info["wled"], info["leds"]), (True, 1))
        self.assertEqual([s["segment"] for s in info["segments"]], [0, 1, 2, 3, 4, 5])
        self.assertEqual(info["segments"][3]["automations"], ["Led Alarme"])
        self.assertEqual(info["segments"][0]["leds"], 9)

    def test_each_segment_has_its_own_speed(self):
        self.assertEqual(light_driver.speed_entity(hass(), "light.wled_segment_5"), "number.wled_vitesse_5")
        self.assertIsNone(light_driver.speed_entity(hass(), "light.wled_principal"))
        self.assertIsNone(light_driver.speed_entity(hass(), "light.salon"))

    def test_a_bulb_has_no_board(self):
        self.assertEqual(light_driver.light_info(hass(), "light.salon"), {"wled": False, "leds": None, "segments": []})


if __name__ == "__main__":
    unittest.main()
