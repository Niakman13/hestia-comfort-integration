"""Explain candidates using registry metadata and explicit sensor provenance."""
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .const import OUTDOOR_AREAS, SOURCES

INDOOR = ("indoor_temperature", "indoor_humidity", "co2", "windows", "heating", "illuminance", "pm25", "voc", "purifier", "presence")
OPENING_SOURCES = ("covers", "shutter_auto", "shutter_override")
OUTDOOR = ("outdoor_temperature", "outdoor_humidity", "rain", "wind_gust", "wind_bearing", "solar", "pollution")
CLASSES = {"temperature": "temperature", "humidity": "humidity", "co2": "carbon_dioxide",
           "wind": "wind_speed", "irradiance": "irradiance", "bearing": "wind_direction"}
UNITS = {"temperature": ("°C", "°F", "K"), "humidity": ("%",), "co2": ("ppm",),
         "wind": ("km/h", "m/s", "mph", "kn", "ft/s"), "irradiance": ("W/m²",), "bearing": ("°",)}


def outdoor_area(hass, area_id):
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return bool(area and area.name.strip().casefold() in OUTDOOR_AREAS)


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


def niak_weather(entry, key):
    """A Niak Weather entity, recognised by its stable unique id, never by its name."""
    return entry.platform == "niak_weather" and (entry.unique_id or "").endswith("_" + key)


def atmo_daily(hass, entry, state):
    # This adapter explicitly supports the Atmo France integration's daily index.
    # AQI classes alone are insufficient: pollutant subindices and tomorrow differ.
    attrs = state.attributes
    return (entry.platform == "atmofrance" and attrs.get("device_class") is None and attrs.get("Libellé") in
            ("Bon", "Moyen", "Dégradé", "Mauvais", "Très mauvais", "Extrêmement mauvais")
            and "pollen" not in state.entity_id and "_j_" not in state.entity_id
            and "J+" not in state.name and "Date de mise à jour" in attrs)


def candidate(hass, entity_id, key, area_id=None, *, include_legacy=False, indoor_ids=()):
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
    elif key == "presence":
        if domain != "binary_sensor" or device_class not in ("occupancy", "presence", "motion"):
            return None
    elif key == "covers":
        if domain != "cover":
            return None
    elif key in ("shutter_auto", "shutter_override"):
        if domain not in ("switch", "binary_sensor") or device_class in ("problem", "battery", "connectivity"):
            return None
    elif key == "purifier":
        if domain != "fan":
            return None
    elif key == "illuminance":
        if domain != "sensor" or device_class != "illuminance" or attrs.get("unit_of_measurement") not in ("lx", "lux"):
            return None
    elif key == "pm25":
        if domain != "sensor" or device_class != "pm25" or attrs.get("unit_of_measurement") not in ("µg/m³", "μg/m³", "mg/m³"):
            return None
    elif key == "voc":
        if domain != "sensor" or device_class not in ("volatile_organic_compounds", "volatile_organic_compounds_parts", "volatile_organic_compounds_index"):
            return None
        if attrs.get("unit_of_measurement") not in ("µg/m³", "μg/m³", "mg/m³", "ppb", "ppm", "index", "indice", "VOC index", None):
            return None
        if attrs.get("unit_of_measurement") is None and device_class != "volatile_organic_compounds_index":
            return None
    elif key == "heating":
        if domain != "climate" or not any(m in attrs.get("hvac_modes", []) for m in ("heat", "heat_cool")):
            if not include_legacy or domain != "climate":
                return None
    elif key == "rain":
        if domain == "sensor" and device_class == "precipitation_intensity" and attrs.get("unit_of_measurement") in ("mm/h", "in/h"):
            adapter = "rain_rate"
        elif domain == "binary_sensor" and niak_weather(entry, "pluie_en_cours"):
            adapter = "binary"  # Niak Weather's own « it is raining now »
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif key == "pollution":
        if atmo_daily(hass, entry, state):
            adapter = "atmo_daily"
        elif domain == "sensor" and niak_weather(entry, "qualite_air"):
            adapter = "niak_index"  # Niak Weather's Atmo index of the day, 1 to 6
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif domain != "sensor" or device_class != CLASSES.get(kind):
        return None
    if kind in CLASSES:
        if attrs.get("unit_of_measurement") not in UNITS[kind]:
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
    # Niak Weather describes the outside by design; outdoor areas are the user's own statement.
    outside = outdoor_area(hass, own_area) or entry.platform == "niak_weather"
    if key in ("outdoor_temperature", "outdoor_humidity"):
        # A mixed station sits outside but also measures indoors: its use in a room decides.
        if entity_id in indoor_ids:
            warnings.append("used_indoor")
        elif not outside:
            warnings.append("outdoor_role")
    if adapter == "binary":
        warnings.append("binary_meaning")
    if adapter in ("atmo_daily", "niak_index"):
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
            "local": local, "outside": outside, "reference": bool(reference), "available": available,
            "adapter": adapter, "warnings": list(dict.fromkeys(warnings)), "provenance": chain,
            "device_class": device_class, "atmo_label": attrs.get("Libellé") if adapter == "atmo_daily" else None}


def catalog(hass, area_id=None, selected=None, indoor_ids=()):
    selected = selected or {}
    result = {}
    for key in (*INDOOR, *OUTDOOR, *OPENING_SOURCES):
        ids = selected.get(key, [])
        ids = ids if isinstance(ids, list) else [ids] if ids else []
        items = []
        for entry in er.async_get(hass).entities.values():
            c = candidate(hass, entry.entity_id, key, area_id, include_legacy=entry.entity_id in ids, indoor_ids=indoor_ids)
            if c:
                items.append(c)
        # Outside: sensors of outdoor areas first. Inside: the room's own reference first.
        first = (lambda c: not c["outside"]) if key in OUTDOOR else (lambda c: not c["reference"])
        result[key] = sorted(items, key=lambda c: (first(c), not c["local"], bool(c["warnings"]), c["name"].casefold()))
    return result


def suggestions(candidates, area_id):
    result = {}
    for key in INDOOR:
        items = candidates[key]
        local = [c for c in items if c["local"] and c["available"] and not c["warnings"]]
        references = [c for c in local if c["reference"]]
        if key in ("windows", "presence"):
            if local:
                result[key] = [c["entity_id"] for c in local]
        elif references:
            result[key] = references[0]["entity_id"]
        elif len(local) == 1:
            result[key] = local[0]["entity_id"]
    return result


def overview(hass, exclude=()):
    """Proposals for every indoor area at once, in a single pass over the entities."""
    areas = {a.id: a for a in ar.async_get(hass).areas.values()
             if a.id not in exclude and a.name.strip().casefold() not in OUTDOOR_AREAS}
    grouped = {area_id: {key: [] for key in INDOOR} for area_id in areas}
    for entry in er.async_get(hass).entities.values():
        own = effective_area(hass, entry)
        if own not in grouped:
            continue
        for key in INDOOR:
            c = candidate(hass, entry.entity_id, key, own)
            if c:
                grouped[own][key].append(c)
    result = []
    for area_id, found in grouped.items():
        proposed = suggestions(found, area_id)
        result.append({"area_id": area_id, "name": areas[area_id].name, "suggestions": proposed,
                       "temperatures": len(found["indoor_temperature"])})
    return sorted(result, key=lambda r: (not bool(r["suggestions"].get("indoor_temperature")), r["name"].casefold()))
