"""A home installed under the former technical name, carried over to « hestia_comfort » with a real Home Assistant:
nothing the user has is lost. Skipped without Home Assistant: ../ha-test/venv/bin/python -m unittest tests/test_domain_migration_ha.py

A first Home Assistant sets the home up with the former integration (a stand-in written by the test, under legacy.DOMAIN):
« Mon logement », a living room and a kitchen sharing one air (one device for both), their learning, the home's
settings linked to a Hestia Weather place that has moved to its Hestia name already, and a dashboard. A second one
starts on the same folder with this version next to the former code, still installed, as HACS may leave it.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

try:
    from homeassistant import loader
    from homeassistant.components.lovelace import LovelaceData
    from homeassistant.components.lovelace.dashboard import LovelaceStorage
    from homeassistant.components.lovelace.resources import ResourceStorageCollection
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import CoreState, HomeAssistant
    from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, frame, issue_registry as ir
    from homeassistant.helpers.storage import Store
except ImportError:  # pragma: no cover - the engine's own test run
    raise unittest.SkipTest("Home Assistant is not installed")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import custom_components.hestia_comfort as integration  # noqa: E402
from custom_components.hestia_comfort import domain_migration  # noqa: E402
from custom_components.hestia_comfort.configuration import DATA_CONFIG, get_configuration  # noqa: E402
from custom_components.hestia_comfort.engine import legacy  # noqa: E402

OLD = legacy.DOMAIN
FORMER = {new: old for old, new in legacy.VALUES.items()}
# A Hestia Weather place, already carried over to its Hestia name: the shared table says so.
WEATHER_OLD, WEATHER_NEW = "01OLDWEATHERPLACE000000000", "01NEWWEATHERPLACE000000000"
OLD_INIT = """from homeassistant.const import Platform
async def async_setup_entry(hass, entry):
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True
async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
"""
# Each room has its own sensor; the shared air's sensor is on the « volume_<id>_<id> » device, carried by the living room.
OLD_SENSOR = """from homeassistant.components.sensor import SensorEntity
DOMAIN = {domain!r}
async def async_setup_entry(hass, entry, add):
    if entry.data.get("home"):
        return
    rooms = sorted(e.entry_id for e in hass.config_entries.async_entries(DOMAIN) if not e.data.get("home"))
    volume = "volume_" + "_".join(rooms)
    add([Old(entry.entry_id + "_advice", (DOMAIN, entry.entry_id), entry.title, f"sensor.{{entry.title.lower()}}_conseil")])
    if entry.title == "Salon":
        add([Old(volume + "_humid", (DOMAIN, volume), "Salon · Cuisine", "sensor.salon_cuisine_trop_humide")])
class Old(SensorEntity):
    _attr_native_value = 1
    def __init__(self, unique_id, identifier, device, entity_id):
        self._attr_unique_id = unique_id
        self._attr_device_info = {{"identifiers": {{identifier}}, "name": device}}
        self.entity_id = entity_id
"""


class DomainMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name)
        old = self.config / "custom_components" / OLD
        old.mkdir(parents=True)
        (old / "manifest.json").write_text(json.dumps({"domain": OLD, "name": "Hestia Confort", "codeowners": ["@hestiaFB"],
                                                       "config_flow": True, "version": "1.7.27", "dependencies": []}))
        (old / "__init__.py").write_text(OLD_INIT)
        (old / "sensor.py").write_text(OLD_SENSOR.format(domain=OLD))
        (old / "config_flow.py").write_text(f"from homeassistant import config_entries\nclass Flow(config_entries.ConfigFlow, domain={OLD!r}):\n    VERSION = 1\n")
        (self.config / "custom_components" / "hestia_comfort").symlink_to(ROOT / "custom_components" / "hestia_comfort")
        sys.path.insert(0, str(self.config))
        await self.first_home()

    async def asyncTearDown(self):
        sys.path.remove(str(self.config))
        for name in [m for m in sys.modules if m.startswith(f"custom_components.{OLD}")]:
            del sys.modules[name]
        self.directory.cleanup()

    async def start(self) -> HomeAssistant:
        hass = HomeAssistant(str(self.config))
        frame.async_setup(hass)
        loader.async_setup(hass)
        hass.config_entries = ConfigEntries(hass, {})
        await hass.config_entries.async_initialize()
        await ar.async_load(hass)
        dr.async_setup(hass)
        await dr.async_load(hass)
        await er.async_load(hass)
        await ir.async_load(hass)
        default = LovelaceStorage(hass, None)
        hass.data["lovelace"] = LovelaceData("storage", {None: default}, ResourceStorageCollection(hass, default), {})
        return hass

    async def stop(self, hass: HomeAssistant) -> None:
        """Stopped as Home Assistant stops: every file written."""
        hass.set_state(CoreState.running)
        await hass.async_stop()

    def add(self, hass: HomeAssistant, title: str, data: dict, unique_id: str) -> ConfigEntry:
        entry = ConfigEntry(domain=OLD, title=title, data=data, options={}, unique_id=unique_id,
                            version=1, minor_version=1, source="user", discovery_keys={}, subentries_data=None)
        hass.config_entries._entries[entry.entry_id] = entry  # added without starting: the rooms start together below
        return entry

    async def first_home(self) -> None:
        """The home as the former version left it."""
        hass = await self.start()
        home = self.add(hass, "Mon logement", {"home": True}, FORMER["hestia_home"])
        salon = self.add(hass, "Salon", {"name": "Salon"}, "salon")
        cuisine = self.add(hass, "Cuisine", {"name": "Cuisine"}, "cuisine")
        hass.config_entries.async_update_entry(salon, options={"open_to": [cuisine.entry_id]})
        for entry in (home, salon, cuisine):
            if entry.state is ConfigEntryState.NOT_LOADED:  # the first one sets the integration up, with every entry
                await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        self.ids = {"home": home.entry_id, "salon": salon.entry_id, "cuisine": cuisine.entry_id}
        area = ar.async_get(hass).async_create("Rez-de-chaussée")
        devices, entities = dr.async_get(hass), er.async_get(hass)
        volume = "volume_" + "_".join(sorted([salon.entry_id, cuisine.entry_id]))
        [shared] = [d for d in dr.async_entries_for_config_entry(devices, salon.entry_id) if (OLD, volume) in d.identifiers]
        devices.async_update_device(shared.id, area_id=area.id, name_by_user="Pièce de vie")
        entities.async_update_entity("sensor.salon_cuisine_trop_humide", name="Trop humide en bas")
        await Store(hass, 1, f"{OLD}.home").async_save({
            "configured": True, "weather": WEATHER_OLD, "revision": 3, "disabled": [FORMER["hestia_weather"]],
            "sources": {"pollution": {"entity_id": "sensor.qualite_air", "adapter": FORMER["hestia_air"], "block_from": 4}}})
        for name in ("learning", "twin", "feedback"):
            await Store(hass, 1, f"{OLD}.{name}.{salon.entry_id}").async_save({"room": salon.entry_id, "kind": name, "openings": 12})
        await Store(hass, 1, domain_migration.TABLE).async_save({"entries": {WEATHER_OLD: WEATHER_NEW}, "done": {}})
        await hass.data["lovelace"].dashboards[None].async_save({"views": [{"cards": [
            {"type": f"custom:{OLD.replace('_', '-')}-card", "entry_id": salon.entry_id},
            {"type": f"custom:{OLD.replace('_', '-')}-home-card"}]}]})
        await self.stop(hass)

    async def test_nothing_is_lost(self):
        hass = await self.start()
        for entry_id in self.ids.values():  # the former code is still installed
            if hass.config_entries.async_get_entry(entry_id).state is ConfigEntryState.NOT_LOADED:
                await hass.config_entries.async_setup(entry_id)
        await hass.async_block_till_done()
        # This version: its files are carried over as it is set up, the rest once Home Assistant has started.
        with patch.object(integration, "async_setup_entry", AsyncMock(return_value=True)):
            await integration.async_setup(hass, {})
            hass.config.components.add("hestia_comfort")
            configuration = await get_configuration(hass)
            hass.set_state(CoreState.running)
            await domain_migration.async_carry_over(hass)
            await hass.async_block_till_done()

        self.assertEqual(hass.config_entries.async_entries(OLD), [])
        news = {e.title: e for e in hass.config_entries.async_entries("hestia_comfort")}
        self.assertEqual(sorted(news), ["Cuisine", "Mon logement", "Salon"])
        self.assertTrue(all(e.state is ConfigEntryState.LOADED for e in news.values()))
        self.assertEqual(news["Mon logement"].unique_id, "hestia_home")
        salon, cuisine = news["Salon"], news["Cuisine"]
        # « Open onto » follows the kitchen's new id.
        self.assertEqual(salon.options["open_to"], [cuisine.entry_id])
        # The shared air keeps its device (area, name) and entity (name, id): its id names the new ids, in order.
        volume = "volume_" + "_".join(sorted([salon.entry_id, cuisine.entry_id]))
        entities, devices = er.async_get(hass), dr.async_get(hass)
        humid = entities.async_get("sensor.salon_cuisine_trop_humide")
        self.assertEqual((humid.platform, humid.unique_id, humid.name), ("hestia_comfort", volume + "_humid", "Trop humide en bas"))
        shared = devices.async_get(humid.device_id)
        self.assertEqual(shared.identifiers, {("hestia_comfort", volume)})
        self.assertEqual((shared.name_by_user, ar.async_get(hass).async_get_area(shared.area_id).name), ("Pièce de vie", "Rez-de-chaussée"))
        advice = entities.async_get("sensor.cuisine_conseil")
        self.assertEqual((advice.config_entry_id, advice.unique_id), (cuisine.entry_id, cuisine.entry_id + "_advice"))
        self.assertFalse([e for e in entities.entities.values() if e.entity_id.endswith("_2")])
        # The home's settings: the Hestia Weather place's new id, the air source and the extension under their new names.
        home = await Store(hass, 1, "hestia_comfort.home").async_load()
        self.assertEqual(home["weather"], WEATHER_NEW)
        self.assertEqual(home["sources"]["pollution"]["adapter"], "hestia_air")
        self.assertEqual(home["disabled"], ["hestia_weather"])
        self.assertEqual(configuration.home["weather"], WEATHER_NEW)  # read after the copy, never before
        self.assertIs(hass.data[DATA_CONFIG], configuration)
        # Each room's learning, twin and answers, under the room's new id.
        for name in ("learning", "twin", "feedback"):
            self.assertEqual(await Store(hass, 1, f"hestia_comfort.{name}.{salon.entry_id}").async_load(),
                             {"room": salon.entry_id, "kind": name, "openings": 12})
            self.assertFalse((self.config / ".storage" / f"{OLD}.{name}.{self.ids['salon']}").exists())
        # The dashboard's cards.
        cards = (await hass.data["lovelace"].dashboards[None].async_load(False))["views"][0]["cards"]
        self.assertEqual(cards, [{"type": "custom:hestia-comfort-card", "entry_id": salon.entry_id}, {"type": "custom:hestia-comfort-home-card"}])
        # The former folder is gone; a restart is asked for.
        self.assertFalse((self.config / "custom_components" / OLD).exists())
        self.assertIn(("hestia_comfort", "migration_restart"), ir.async_get(hass).issues)
        await self.stop(hass)


    async def test_add_an_integration_resumes_the_home(self):
        """« Add an integration → Hestia Confort » with the former code running: the home is resumed, never set up twice."""
        hass = await self.start()
        for entry_id in self.ids.values():
            if hass.config_entries.async_get_entry(entry_id).state is ConfigEntryState.NOT_LOADED:
                await hass.config_entries.async_setup(entry_id)
        await hass.async_block_till_done()
        hass.set_state(CoreState.running)
        hass.config.components.update({"frontend", "http", "websocket_api", "lovelace", "recorder"})  # there in a real home
        with patch.object(integration, "async_setup_entry", AsyncMock(return_value=True)):
            result = await hass.config_entries.flow.async_init("hestia_comfort", context={"source": "user"})
            await hass.async_block_till_done()
        self.assertEqual((result["type"], result["reason"]), ("abort", "migrated"))
        self.assertEqual(hass.config_entries.async_entries(OLD), [])
        self.assertEqual(sorted(e.title for e in hass.config_entries.async_entries("hestia_comfort")), ["Cuisine", "Mon logement", "Salon"])
        from custom_components.hestia_comfort.panel import migration_status
        status = await migration_status(hass)
        self.assertEqual((status["state"], status["summary"], status["restart"]), ("done", {"rooms": 2, "learning": 1}, True))
        await self.stop(hass)

if __name__ == "__main__":
    unittest.main()
