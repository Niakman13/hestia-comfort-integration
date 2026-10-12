"""Explicit zone and source selection; empty optional choices stay empty."""
from dataclasses import asdict
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import DOMAIN, SOURCES
from .engine.assessment import Settings


def source_schema():
    fields = {}
    for key, kind in SOURCES.items():
        entity = {"domain": "climate"} if kind == "heating" else {"domain": "binary_sensor"} if kind in ("rain", "pollution") else {"domain": "sensor", "device_class": {"temperature": "temperature", "humidity": "humidity", "co2": "carbon_dioxide"}[kind]}
        marker = vol.Required if key in ("indoor_temperature", "outdoor_temperature") else vol.Optional
        fields[marker(key)] = selector({"entity": entity})
    fields[vol.Optional("windows")] = selector({"entity": {"domain": "binary_sensor", "device_class": ["window", "door", "opening"], "multiple": True}})
    return vol.Schema(fields)


def settings_schema():
    return vol.Schema({vol.Required(key, default=value): vol.Coerce(float) for key, value in asdict(Settings()).items()})


class SourceSteps:
    async def async_step_sources(self, user_input=None):
        if user_input is not None:
            self.values["sources"] = {k: user_input[k] for k in SOURCES if user_input.get(k)}
            self.values["windows"] = user_input.get("windows", [])
            return await self.async_step_settings()
        selected = {**self.values.get("sources", {}), "windows": self.values.get("windows", [])}
        return self.async_show_form(step_id="sources", data_schema=self.add_suggested_values_to_schema(source_schema(), selected))

    async def async_step_settings(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self.values["settings"] = asdict(Settings(**user_input))
            except (ValueError, TypeError):
                errors["base"] = "invalid_settings"
            else:
                return self._finish()
        return self.async_show_form(step_id="settings", errors=errors,
            data_schema=self.add_suggested_values_to_schema(settings_schema(), user_input or self.values.get("settings", {})))


class ComfortConfigFlow(SourceSteps, ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.values = dict(user_input)
            await self.async_set_unique_id(user_input["area_id"])
            self._abort_if_unique_id_configured()
            return await self.async_step_sources()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("name"): selector({"text": {}}),
            vol.Required("area_id"): selector({"area": {}}),
        }))

    def _finish(self):
        return self.async_create_entry(title=self.values["name"], data=self.values)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ComfortOptionsFlow()


class ComfortOptionsFlow(SourceSteps, OptionsFlow):
    async def async_step_init(self, user_input=None):
        self.values = {**self.config_entry.data, **self.config_entry.options}
        return await self.async_step_sources(user_input)

    def _finish(self):
        return self.async_create_entry(data=self.values)
