"""Room-first setup with reviewable proposals and explicit, persistent choices."""
from copy import deepcopy
from dataclasses import asdict
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.selector import selector

from .const import DOMAIN, SOURCES
from .discovery import catalog, suggestions
from .engine.assessment import Settings

CATEGORIES = {
    "indoor": ("indoor_temperature", "indoor_humidity", "co2"),
    "outdoor": ("outdoor_temperature", "outdoor_humidity", "rain", "pollution"),
    "windows": ("windows",),
    "heating": ("heating",),
}
CLASSES = {"temperature": "temperature", "humidity": "humidity", "co2": "carbon_dioxide"}


def source_schema(keys=None):
    """All entities remain selectable, including mixed indoor/outdoor stations."""
    fields = {}
    for key in keys or (*SOURCES, "windows"):
        if key == "windows":
            entity = {"domain": "binary_sensor", "device_class": ["window", "door", "opening"], "multiple": True}
        else:
            kind = SOURCES[key]
            entity = {"domain": "climate"} if kind == "heating" else {"domain": "binary_sensor"} if kind in ("rain", "pollution") else {"domain": "sensor", "device_class": CLASSES[kind]}
        marker = vol.Required if key == "indoor_temperature" else vol.Optional
        fields[marker(key)] = selector({"entity": entity})
    return vol.Schema(fields)


def settings_schema(keys=None, values=None):
    defaults = {**asdict(Settings()), **(values or {})}
    return vol.Schema({vol.Required(key, default=defaults[key]): vol.Coerce(float) for key in keys or defaults})


def room_candidates(hass, area_id):
    """Use entity area before device area; never infer location from entity names."""
    entities, devices = er.async_get(hass), dr.async_get(hass)
    found = {key: [] for key in ("indoor_temperature", "indoor_humidity", "co2", "windows", "heating")}
    for entity in entities.entities.values():
        if entity.disabled_by or entity.entity_category is not None:
            continue
        device = devices.async_get(entity.device_id) if entity.device_id else None
        if (entity.area_id or (device.area_id if device else None)) != area_id:
            continue
        state = hass.states.get(entity.entity_id)
        if not state:
            continue
        kind = state.attributes.get("device_class") or entity.device_class or entity.original_device_class
        for key in found:
            matches = (
                (key == "windows" and state.domain == "binary_sensor"
                 and kind in ("window", "door", "opening"))
                or (key == "heating" and state.domain == "climate"
                    and any(mode in state.attributes.get("hvac_modes", [])
                            for mode in ("heat", "heat_cool")))
                or (key not in ("windows", "heating") and state.domain == "sensor"
                    and kind == CLASSES[SOURCES[key]])
            )
            if matches:
                found[key].append(entity.entity_id)
    return {key: sorted(ids) for key, ids in found.items()}


def proposals(hass, area_id):
    return suggestions(catalog(hass, area_id), area_id)


class SourceSteps:
    reviewing = False
    editing = False

    def _selected(self):
        return {**self.values.get("sources", {}), "windows": self.values.get("windows", [])}

    def _apply_proposals(self):
        for key, value in proposals(self.hass, self.values["area_id"]).items():
            if key == "windows":
                if "windows" not in self.values:
                    self.values[key] = value
            elif key not in self.values.get("sources", {}):
                self.values.setdefault("sources", {})[key] = value

    def _label(self, french, english):
        return french if self.hass.config.language.startswith("fr") else english

    def _text(self, entity_id):
        state = self.hass.states.get(entity_id)
        if not state:
            return f"{entity_id} — {self._label("Indisponible", "Unavailable")}"
        if state.state in ("unavailable", "unknown"):
            return f"{state.name} — {self._label("Temporairement indisponible", "Temporarily unavailable")}"
        unit = state.attributes.get("unit_of_measurement", "")
        value = state.state
        if state.domain == "binary_sensor" and value in ("on", "off"):
            opened = state.attributes.get("device_class") in ("window", "door", "opening")
            value = self._label("Ouvert", "Open") if opened and value == "on" else self._label("Fermé", "Closed") if opened else self._label("Actif", "Active") if value == "on" else self._label("Inactif", "Inactive")
        return f"{state.name} — {value} {unit}".strip()

    def _details(self, keys):
        selected = self._selected()
        candidates = room_candidates(self.hass, self.values["area_id"])
        lines = {}
        for key in keys:
            value = selected.get(key)
            if value:
                lines[key] = "\n".join(self._text(e) for e in value) if isinstance(value, list) else self._text(value)
            else:
                ids = candidates.get(key, [])
                # Empty translations provide the localized explanation; show actual candidates only.
                lines[key] = "\n".join(self._text(e) for e in ids[:6]) or "—"
                if len(ids) > 6:
                    lines[key] += f"\n(+{len(ids)-6})"
        return lines

    async def _category(self, category, user_input, next_step):
        keys = CATEGORIES[category]
        errors = {}
        if user_input is not None:
            # Validate before editing the draft; a failed form must not remove choices.
            for key in keys:
                value = user_input.get(key)
                ids = value if isinstance(value, list) else [value] if value else []
                for entity_id in ids:
                    state = self.hass.states.get(entity_id)
                    if not state:
                        # Existing unavailable registry entities may still be configured.
                        if not er.async_get(self.hass).async_get(entity_id):
                            errors[key] = "invalid_source"
                    elif key == "windows":
                        if state.domain != "binary_sensor" or state.attributes.get("device_class") not in ("window", "door", "opening"):
                            errors[key] = "invalid_source"
                    else:
                        kind = SOURCES[key]
                        domain = "climate" if kind == "heating" else "binary_sensor" if kind in ("rain", "pollution") else "sensor"
                        if state.domain != domain or (kind in CLASSES and state.attributes.get("device_class") != CLASSES[kind]):
                            errors[key] = "invalid_source"
            if category == "indoor" and not user_input.get("indoor_temperature"):
                errors["indoor_temperature"] = "required_source"
            if not errors:
                for key in keys:
                    if key == "windows":
                        self.values[key] = list(dict.fromkeys(user_input.get(key, [])))
                    else:
                        self.values.setdefault("sources", {}).pop(key, None)
                        if user_input.get(key):
                            self.values["sources"][key] = user_input[key]
                return await self._next(next_step)
        return self.async_show_form(step_id=category, errors=errors, last_step=False,
            data_schema=self.add_suggested_values_to_schema(source_schema(keys), user_input if user_input is not None else self._selected()),
            description_placeholders=self._details(keys))

    async def _next(self, step):
        if self.editing:
            return await self.async_step_init()
        if self.reviewing:
            return await self.async_step_review()
        return await getattr(self, f"async_step_{step}")()

    async def async_step_indoor(self, user_input=None):
        return await self._category("indoor", user_input, "outdoor")

    async def async_step_outdoor(self, user_input=None):
        return await self._category("outdoor", user_input, "windows")

    async def async_step_windows(self, user_input=None):
        return await self._category("windows", user_input, "heating")

    async def async_step_heating(self, user_input=None):
        return await self._category("heating", user_input, "preferences")

    async def _settings(self, step, keys, user_input):
        errors = {}
        if user_input is not None:
            try:
                self.values["settings"] = asdict(Settings(**{**self.values.get("settings", {}), **user_input}))
            except (ValueError, TypeError):
                errors["base"] = "invalid_settings"
            else:
                return await self._next("review")
        return self.async_show_form(step_id=step, errors=errors, last_step=False,
            data_schema=self.add_suggested_values_to_schema(settings_schema(keys, self.values.get("settings")), user_input or self.values.get("settings", {})))

    async def async_step_preferences(self, user_input=None):
        return await self._settings("preferences", ("minimum", "maximum"), user_input)

    async def async_step_advanced(self, user_input=None):
        return await self._settings("advanced", tuple(k for k in asdict(Settings()) if k not in ("minimum", "maximum")), user_input)

    def _summary(self):
        selected = self._selected()
        details = {key: self._text(value) if isinstance(value, str) else "\n".join(self._text(e) for e in value) if value else self._label("Non configuré", "Not configured") for key, value in ((key, selected.get(key)) for key in (*SOURCES, "windows"))}
        sentences = [self._label("Niak suivra la température de cette pièce.", "Niak will monitor this room’s temperature.")]
        if selected.get("co2"):
            sentences.append(self._label("Le CO₂ permettra de détecter un besoin de renouvellement d’air.", "CO₂ will help detect an air renewal need."))
        if not selected.get("outdoor_temperature"):
            sentences.append(self._label("Sans température extérieure, le bénéfice thermique d’une ouverture reste inconnu.", "Without outdoor temperature, the thermal benefit of opening remains unknown."))
        if not all(selected.get(k) for k in ("rain", "pollution")):
            sentences.append(self._label("Vérifiez les conditions extérieures non renseignées avant d’ouvrir.", "Check unconfigured outdoor conditions before opening."))
        if not selected.get("windows"):
            sentences.append(self._label("Sans contacts, l’état des fenêtres n’est pas mesuré.", "Without contacts, window state is not measured."))
        settings = {**asdict(Settings()), **self.values.get("settings", {})}
        details["capabilities"] = " ".join(sentences) + f"\n\n{self._label('Votre plage de confort', 'Your comfort range')} : {settings['minimum']:g}–{settings['maximum']:g} °C."
        return details

    async def async_step_review(self, user_input=None):
        self.reviewing = True
        return self.async_show_menu(step_id="review", menu_options=["finish", *CATEGORIES, "preferences"], description_placeholders=self._summary())

    async def async_step_finish(self, user_input=None):
        if user_input is not None:
            if not self.values.get("sources", {}).get("indoor_temperature"):
                return await self.async_step_indoor()
            return self._finish()
        return self.async_show_form(step_id="finish", data_schema=vol.Schema({}), last_step=True, description_placeholders=self._summary())


class ComfortConfigFlow(SourceSteps, ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input and "panel_config" in user_input:
            from .configuration import get_configuration
            service = await get_configuration(self.hass)
            values, warnings = service.validate(user_input["panel_config"])
            service.ensure_acknowledged(warnings, user_input.get("acknowledged", []))
            await self.async_set_unique_id(values["area_id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=values["name"], data=values)
        if not self.hass.config_entries.async_entries(DOMAIN) and not (user_input and "area_id" in user_input):
            if user_input is not None:
                await self.async_set_unique_id("niak_home")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Mon logement", data={"home": True})
            return self.async_show_form(step_id="home", data_schema=vol.Schema({}), last_step=True)
        areas = ar.async_get(self.hass)
        if user_input is not None:
            area = areas.async_get_area(user_input["area_id"])
            if not area:
                return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required("area_id"): selector({"area": {}})}), errors={"area_id": "invalid_area"})
            self.values = {"area_id": area.id, "name": user_input.get("name", "").strip() or area.name, "sources": {}}
            await self.async_set_unique_id(area.id)
            self._abort_if_unique_id_configured()
            self._apply_proposals()
            # Reuse only unanimous exterior measurements as editable proposals.
            # Rain exposure belongs to each room and is never inherited.
            entries = self.hass.config_entries.async_entries(DOMAIN)
            for key in ("outdoor_temperature", "outdoor_humidity", "pollution"):
                values = {{**entry.data, **entry.options}.get("sources", {}).get(key) for entry in entries}
                if len(values) == 1 and (value := next(iter(values))):
                    self.values["sources"][key] = value
            return await self.async_step_indoor()
        configured = {entry.unique_id for entry in self.hass.config_entries.async_entries(DOMAIN)}
        salon = next((a.id for a in areas.areas.values() if a.id not in configured and a.name.casefold() in ("salon", "living room")), None)
        schema = vol.Schema({vol.Required("area_id"): selector({"area": {}}), vol.Optional("name"): selector({"text": {}})})
        return self.async_show_form(step_id="user", last_step=False,
            data_schema=self.add_suggested_values_to_schema(schema, {"area_id": salon} if salon else {}))

    async def async_step_home(self, user_input=None):
        return await self.async_step_user(user_input)

    def _finish(self):
        self.values.setdefault("settings", asdict(Settings()))
        return self.async_create_entry(title=self.values["name"], data=self.values)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ComfortOptionsFlow()


class ComfortOptionsFlow(SourceSteps, OptionsFlow):
    editing = True

    async def async_step_init(self, user_input=None):
        if self.config_entry.data.get("home"):
            if user_input is not None:
                return self.async_create_entry(data=dict(self.config_entry.options))
            return self.async_show_form(step_id="init", data_schema=vol.Schema({}),
                description_placeholders={"workspace": "Niak Confort → Mon logement"})
        if not hasattr(self, "values"):
            self.values = deepcopy({**self.config_entry.data, **self.config_entry.options})
        return self.async_show_menu(step_id="init", menu_options=[*CATEGORIES, "preferences", "advanced", "discover", "finish"])

    async def async_step_discover(self, user_input=None):
        if user_input is not None:
            selected = self._selected()
            for key, value in proposals(self.hass, self.values["area_id"]).items():
                # A cleared source stays cleared. Re-search only fills explicitly chosen fields.
                if user_input.get(key) and not selected.get(key):
                    if key == "windows":
                        self.values[key] = value
                    else:
                        self.values.setdefault("sources", {})[key] = value
            return await self.async_step_indoor()
        proposed = proposals(self.hass, self.values["area_id"])
        keys = [key for key in proposed if not self._selected().get(key)]
        return self.async_show_form(step_id="discover", data_schema=vol.Schema({vol.Optional(key, default=False): selector({"boolean": {}}) for key in keys}),
            description_placeholders={"detected": "\n".join(self._text(e) for key in keys for e in (proposed[key] if isinstance(proposed[key], list) else [proposed[key]])) or "—"})

    def _finish(self):
        return self.async_create_entry(data=self.values)
