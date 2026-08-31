"""Text platform for Espruino integration."""

from typing import override

from homeassistant.components.text import TextEntity
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EspruinoConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspruinoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Espruino text entities."""
    address = entry.data[CONF_ADDRESS]
    async_add_entities([EspruinoTextEntity(entry, address)])


class EspruinoTextEntity(TextEntity):
    """Representation of an Espruino text entity to send UART commands."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: EspruinoConfigEntry, address: str) -> None:
        """Initialize the text entity."""
        self._entry = entry
        self._address = address
        self._attr_unique_id = f"{format_mac(address)}_text"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(dr.CONNECTION_NETWORK_MAC, address)},
            name=entry.title,
            manufacturer="Espruino",
        )
        self._attr_native_value: str | None = ""

    @override
    async def async_set_value(self, value: str) -> None:
        """Set the text value by connecting, writing to the device, and disconnecting."""
        self._attr_native_value = value
        self.async_write_ha_state()
        manager = self._entry.runtime_data.manager
        value = value + "\n"
        await manager.async_send_uart(
            self._address, value.encode("latin1", errors="replace")
        )

