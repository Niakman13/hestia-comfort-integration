"""Explain candidates using registry metadata and explicit sensor provenance."""
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .const import SOURCES

INDOOR = ("indoor_temperature", "indoor_humidity", "co2", "windows", "heating")
OUTDOOR = ("outdoor_temperature", "outdoor_humidity", "rain", "pollution")
CLASSES = {"temperature": "temperature", "humidity": "humidity", "co2": "carbon_dioxide"}


def effective_area(hass, entry):
    device = dr.async_get(hass).async_get(entry.device_id) if entry.device_id else None
    return entry.area_id or (device.area_id if device else None)


def provenance(hass, entity_id):
    """Follow explicitly declared aliases; never guess a room from entity names."""
    seen, chain = set(), []
    current = entity_id
    while current and current not in seen and len(chain) < 16:
        seen.add(current)
        state = hass.states.get(current)
        registry = er.async_get(hass).async_get(current)
        chain.append({"entity_id": current, "name": state.name if state else current,
                      "area_id": effective_area(hass, registry) if registry else None})
        external = state.attributes.get("external_sensor") if state else None
        current = external if isinstance(external, str) else None
    return chain


def atmo_daily(hass, entry, state):
    # This adapter explicitly supports the Atmo France integration's daily index.
    # AQI classes alone are insufficient: pollutant subindices and tomorrow differ.
    attrs = state.attributes
    return (entry.platform == "atmofrance" and attrs.get("device_class") is None and attrs.get("Libellé") in
            ("Bon", "Moyen", "Dégradé", "Mauvais", "Très mauvais", "Extrêmement mauvais")
            and "pollen" not in state.entity_id and "_j_" not in state.entity_id
            and "J+" not in state.name and "Date de mise à jour" in attrs)


def candidate(hass, entity_id, key, area_id=None, *, include_legacy=False):
    entry = er.async_get(hass).async_get(entity_id)
    state = hass.states.get(entity_id)
    if not entry or entry.disabled_by or entry.entity_category is not None or not state:
        return None
    attrs = state.attributes
    domain = state.domain
    device_class = attrs.get("device_class") or entry.device_class or entry.original_device_class
    kind = SOURCES.get(key)
    adapter = "direct"
    if key == "windows":
        if domain != "binary_sensor" or device_class not in ("window", "door", "opening"):
            return None
    elif key == "heating":
        if domain != "climate" or not any(m in attrs.get("hvac_modes", []) for m in ("heat", "heat_cool")):
            if not include_legacy or domain != "climate":
                return None
    elif key == "rain":
        if domain == "sensor" and device_class == "precipitation_intensity" and attrs.get("unit_of_measurement") in ("mm/h", "in/h"):
            adapter = "rain_rate"
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif key == "pollution":
        if atmo_daily(hass, entry, state):
            adapter = "atmo_daily"
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif domain != "sensor" or device_class != CLASSES.get(kind):
        return None
    if kind in CLASSES:
        if attrs.get("unit_of_measurement") not in {"temperature": ("°C", "°F", "K"), "humidity": ("%",), "co2": ("ppm",)}[kind]:
            return None
    own_area = effective_area(hass, entry)
    chain = provenance(hass, entity_id)
    warnings = []
    if len(chain) > 1:
        warnings.append("alias")
    if area_id and any(p["area_id"] and p["area_id"] != area_id for p in chain):
        warnings.append("other_area")
    if key == "windows" and device_class != "window":
        warnings.append("contact_role")
    if entry.platform in ("template", "plant", "versatile_thermostat"):
        warnings.append("derived")
    if key == "heating" and not attrs.get("hvac_action"):
        warnings.append("no_hvac_action")
    if key in ("outdoor_temperature", "outdoor_humidity"):
        warnings.append("outdoor_role")
    if adapter == "binary":
        warnings.append("binary_meaning")
    if adapter == "atmo_daily":
        warnings.append("daily_forecast")
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    reference = area and ((key == "indoor_temperature" and area.temperature_entity_id == entity_id)
                           or (key == "indoor_humidity" and area.humidity_entity_id == entity_id))
    if reference and len(chain) == 1 and "other_area" not in warnings:
        warnings = [warning for warning in warnings if warning != "derived"]
    local = bool(area_id and own_area == area_id)
    available = state.state not in ("unknown", "unavailable", "none", "")
    return {"entity_id": entity_id, "name": state.name, "value": state.state,
            "unit": attrs.get("unit_of_measurement"), "area_id": own_area,
            "local": local, "reference": bool(reference), "available": available,
            "adapter": adapter, "warnings": list(dict.fromkeys(warnings)), "provenance": chain,
            "device_class": device_class, "atmo_label": attrs.get("Libellé") if adapter == "atmo_daily" else None}


def catalog(hass, area_id=None, selected=None):
    selected = selected or {}
    result = {}
    for key in (*INDOOR, *OUTDOOR):
        ids = selected.get(key, [])
        ids = ids if isinstance(ids, list) else [ids] if ids else []
        items = []
        for entry in er.async_get(hass).entities.values():
            c = candidate(hass, entry.entity_id, key, area_id, include_legacy=entry.entity_id in ids)
            if c:
                items.append(c)
        result[key] = sorted(items, key=lambda c: (not c["reference"], not c["local"], bool(c["warnings"]), c["name"].casefold()))
    return result


def suggestions(candidates, area_id):
    result = {}
    for key in INDOOR:
        items = candidates[key]
        local = [c for c in items if c["local"] and c["available"] and not c["warnings"]]
        references = [c for c in local if c["reference"]]
        if key == "windows":
            if local:
                result[key] = [c["entity_id"] for c in local]
        elif references:
            result[key] = references[0]["entity_id"]
        elif len(local) == 1:
            result[key] = local[0]["entity_id"]
    return result
