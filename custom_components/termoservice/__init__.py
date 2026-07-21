from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .coordinator import TermoServiceCoordinator
from .termoservice_client import TermoServiceClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

SERVICE_TRIMITE_INDEX = "trimite_index"
SERVICE_SCHEMA = vol.Schema({
    vol.Required("index_baie"): vol.Coerce(float),
    vol.Required("index_bucatarie"): vol.Coerce(float),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    client = TermoServiceClient(email, password)
    coordinator = TermoServiceCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_trimite_index(call: ServiceCall) -> None:
        index_baie = call.data["index_baie"]
        index_bucatarie = call.data["index_bucatarie"]
        _LOGGER.info("Trimitere index apă: Baie=%s, Bucatarie=%s", index_baie, index_bucatarie)
        await hass.async_add_executor_job(
            client.submit_water_index, index_baie, index_bucatarie
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_TRIMITE_INDEX, handle_trimite_index, schema=SERVICE_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.services.async_remove(DOMAIN, SERVICE_TRIMITE_INDEX)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
