"""The Espruino integration."""

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .connection import EspruinoConnectionManager
from .const import DOMAIN
from .panel import async_register_panel
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.TEXT]

type EspruinoConfigEntry = ConfigEntry[EspruinoData]


@dataclass
class EspruinoData:
    """Data for the Espruino integration."""

    manager: EspruinoConnectionManager


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Espruino component."""
    if DOMAIN not in hass.data:
        manager = EspruinoConnectionManager(hass)
        hass.data[DOMAIN] = EspruinoData(manager=manager)
        async_register_websocket_api(hass)
        await async_register_panel(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: EspruinoConfigEntry) -> bool:
    """Set up Espruino from a config entry."""
    await async_setup(hass, {})

    address: str = entry.data[CONF_ADDRESS]

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, address)},
        connections={(dr.CONNECTION_NETWORK_MAC, address)},
        name=entry.title,
        manufacturer="Espruino",
    )

    entry.runtime_data = hass.data[DOMAIN]
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EspruinoConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    address: str = entry.data[CONF_ADDRESS]
    manager = entry.runtime_data.manager
    await manager.async_disconnect(address)
    return unload_ok

