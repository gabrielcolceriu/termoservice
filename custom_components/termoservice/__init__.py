from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .coordinator import TermoServiceCoordinator
from .termoservice_client import TermoServiceClient

PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    client = TermoServiceClient(email, password)
    coordinator = TermoServiceCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
