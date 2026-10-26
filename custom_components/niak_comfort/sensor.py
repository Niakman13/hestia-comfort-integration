"""Small stable states for automations; rich observations stay out of Recorder."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .engine.assessment import ACTIONS, LEVELS

DESCRIPTIONS = (
    SensorEntityDescription(key="level", translation_key="level", device_class=SensorDeviceClass.ENUM, options=list(LEVELS)),
    SensorEntityDescription(key="action", translation_key="action", device_class=SensorDeviceClass.ENUM, options=list(ACTIONS)),
    SensorEntityDescription(key="reason", translation_key="reason", device_class=SensorDeviceClass.ENUM,
                            options=["within_comfort", "rain_open_windows", "opening_blocked", "verify_exterior",
                                     "air_needed", "cooling_possible", "drying_possible", "exchange_harmful",
                                     "cooling_unavailable", "heat_needed", "drying_unavailable", "drying_later", "drying_slow", "ventilation_possible", "incomplete_data", "optional_air_change",
                                     "gust_open_windows", "short_air_change", "sun_entering", "rain_soon", "precool_possible", "precool_later", "shared_volume", "humid_outdoor", "open_neutral", "rehumidification_risk", "alarm_open", "warm_walls"]),
    SensorEntityDescription(key="heating_action", translation_key="heating_action", device_class=SensorDeviceClass.ENUM,
                            options=["heating", "idle", "off", "cooling", "unknown", "not_configured"]),
    SensorEntityDescription(key="coverage", translation_key="coverage", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENUM, options=["partial", "configured_sources_available"]),
    # The twin's view of the coming hour, to lay over the real sensors in the history: off until asked for.
    SensorEntityDescription(key="twin_temperature", translation_key="twin_temperature", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                            suggested_display_precision=1, entity_registry_enabled_default=False),
    SensorEntityDescription(key="twin_humidity", translation_key="twin_humidity", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.HUMIDITY, native_unit_of_measurement=PERCENTAGE,
                            entity_registry_enabled_default=False),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ComfortSensor(entry.runtime_data, entry, description) for description in DESCRIPTIONS)


class ComfortSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title,
                                  "manufacturer": "Niak", "model": "Comfort · observation",
                                  "configuration_url": "homeassistant://niak/confort"}

    @property
    def native_value(self):
        assessment = self.coordinator.data["assessment"]
        if self.entity_description.key.startswith("twin_"):
            coming = (self.coordinator.data.get("twin") or {}).get("next_hour") or {}
            return coming.get(self.entity_description.key[5:])
        if self.entity_description.key == "coverage":
            return "partial" if assessment["partial"] else "configured_sources_available"
        return assessment[self.entity_description.key]

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "reason":
            result = self.coordinator.data["assessment"]
            return {k: result[k] for k in ("needs", "constraints", "partial", "missing")}
        return None
