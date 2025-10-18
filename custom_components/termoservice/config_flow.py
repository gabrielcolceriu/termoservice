
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .termoservice_client import TermoServiceClient

class TermoServiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            ok = await self._async_try_login(email, password)
            if ok:
                return self.async_create_entry(title=f"TermoService - {email}", data=user_input)
            errors["base"] = "cannot_connect"
        schema = vol.Schema({
            vol.Required(CONF_EMAIL): str,
            vol.Required(CONF_PASSWORD): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_try_login(self, email: str, password: str) -> bool:
        client = TermoServiceClient(email, password)
        try:
            await self.hass.async_add_executor_job(client.login)
            return True
        except Exception:
            return False
