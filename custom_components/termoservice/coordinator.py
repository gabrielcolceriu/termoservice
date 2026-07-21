
import logging
from datetime import timedelta
from typing import List
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DEFAULT_SCAN_INTERVAL
from .termoservice_client import TermoServiceClient, AccountSummary

_LOGGER = logging.getLogger(__name__)

class TermoServiceCoordinator(DataUpdateCoordinator[List[AccountSummary]]):
    def __init__(self, hass: HomeAssistant, client: TermoServiceClient, interval_minutes: int = DEFAULT_SCAN_INTERVAL):
        super().__init__(hass, _LOGGER, name="termoservice", update_interval=timedelta(minutes=interval_minutes))
        self.client = client

    async def _async_update_data(self):
        return await self.hass.async_add_executor_job(self._fetch)

    def _fetch(self):
        try:
            self.client.login()
        except Exception:
            pass
        return self.client.fetch_all()
