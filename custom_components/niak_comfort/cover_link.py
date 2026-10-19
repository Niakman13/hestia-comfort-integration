"""Adaptive Cover Pro, recognised by itself: the integration that drives a cover with the sun.

When a connected cover is driven by Adaptive Cover Pro, Niak reads its signals (automatic control,
manual override, sun in front of the window, target position, sun hours) without asking the person
to find them. Entities are recognised by their platform and their stable key, never by their name.
Niak still commands nothing.
"""
from homeassistant.helpers import entity_registry as er

PLATFORMS = ("adaptive_cover_pro", "adaptive_cover")
NAME = "Adaptive Cover Pro"
# Role → (domain, key at the end of the unique id, translation key or entity id).
ROLES = {"auto": ("switch", "automatic_control"), "enabled": ("switch", "integration_enabled"),
         "override": ("binary_sensor", "manual_override"), "sun": ("binary_sensor", "sun_infront"),
         "target": ("sensor", "target_position"), "sun_start": ("sensor", "start_sun"), "sun_end": ("sensor", "end_sun")}


def _role(entry):
    domain = entry.entity_id.split(".", 1)[0]
    for role, (want, key) in ROLES.items():
        if domain == want and (entry.translation_key == key or (entry.unique_id or "").endswith(key) or entry.entity_id.endswith("_" + key)):
            return role
    return None


def _covers(hass, config_entry_id, roles):
    """The covers one Adaptive Cover Pro entry drives: from its settings, else from what it reports."""
    found = set()
    config = hass.config_entries.async_get_entry(config_entry_id) if config_entry_id else None
    if config:
        for source in (config.options, config.data):
            group = source.get("group") or source.get("entities")
            if isinstance(group, str):
                group = [group]
            if isinstance(group, list):
                found.update(g for g in group if isinstance(g, str))
    target = hass.states.get(roles["target"]) if roles.get("target") else None
    for attr in ("actual_positions", "linear_actual_positions"):
        value = target.attributes.get(attr) if target else None
        if isinstance(value, dict):
            found.update(k for k in value if isinstance(k, str))
    return found


def find_all(hass):
    """{cover entity: {role: entity id}} for every cover Adaptive Cover Pro drives."""
    entries = {}
    for entry in er.async_get(hass).entities.values():
        if entry.platform in PLATFORMS and not entry.disabled_by and (role := _role(entry)):
            entries.setdefault(entry.config_entry_id, {})[role] = entry.entity_id
    result = {}
    for config_entry_id, roles in entries.items():
        for cover in _covers(hass, config_entry_id, roles):
            result[cover] = {**roles, "name": NAME}
    return result


def find(hass, cover_entity):
    return find_all(hass).get(cover_entity) if cover_entity else None
