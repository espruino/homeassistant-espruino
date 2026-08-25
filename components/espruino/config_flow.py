"""Config flow for Espruino integration."""

import logging
from typing import Any, override

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, MANUFACTURER_ID

_LOGGER = logging.getLogger(__name__)


class EspruinoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Espruino."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a discovered Bluetooth device."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()

        self._discovered_address = discovery_info.address
        self._discovered_name = (
            discovery_info.name or f"Espruino {format_mac(discovery_info.address)}"
        )

        self.context["title_placeholders"] = {CONF_NAME: self._discovered_name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle confirmation of Bluetooth discovery."""
        if user_input is not None:
            assert self._discovered_address is not None
            assert self._discovered_name is not None
            return self.async_create_entry(
                title=self._discovered_name,
                data={
                    CONF_ADDRESS: self._discovered_address,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={CONF_NAME: self._discovered_name},
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(format_mac(address), raise_on_progress=False)
            self._abort_if_unique_id_configured()

            name = f"Espruino {format_mac(address)}"
            for service_info in async_discovered_service_info(self.hass):
                if service_info.address.upper() == address.upper():
                    name = service_info.name or name
                    break

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                },
            )

        discovered_devices: dict[str, str] = {}
        for service_info in async_discovered_service_info(self.hass):
            if MANUFACTURER_ID in service_info.manufacturer_data:
                name = (
                    service_info.name or f"Espruino {format_mac(service_info.address)}"
                )
                discovered_devices[service_info.address] = (
                    f"{name} ({service_info.address})"
                )

        current_addresses = self._async_current_ids()
        discovered_devices = {
            address: name
            for address, name in discovered_devices.items()
            if format_mac(address) not in current_addresses
        }

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        options = [
            SelectOptionDict(value=address, label=label)
            for address, label in discovered_devices.items()
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )
