"""BLE Connection manager for Espruino devices over Nordic UART Service."""

from collections.abc import Callable
import contextlib
import logging
from typing import Any

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakError,
    close_stale_connections_by_address,
    establish_connection,
    get_device,
)

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    MANUFACTURER_ID,
    NORDIC_UART_RX_CHARACTERISTIC_UUID,
    NORDIC_UART_TX_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)


class EspruinoConnectionManager:
    """Manages BLE connections and Nordic UART communication for Espruino devices."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the connection manager."""
        self.hass = hass
        self._clients: dict[str, BleakClientWithServiceCache] = {}
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    def is_connected(self, address: str) -> bool:
        """Check if device is currently connected."""
        addr = address.upper()
        client = self._clients.get(addr)
        return client is not None and client.is_connected

    def get_discovered_devices(self) -> list[dict[str, Any]]:
        """Get list of discovered and configured Espruino devices."""
        devices: dict[str, dict[str, Any]] = {}

        # Add configured entries
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            address = entry.data[CONF_ADDRESS]
            devices[address.upper()] = {
                "address": address,
                "name": entry.title,
                "rssi": None,
                "connected": self.is_connected(address),
            }

        # Add discovered devices matching manufacturer ID, and update RSSI for all discovered devices
        for service_info in async_discovered_service_info(self.hass):
            addr = service_info.address.upper()
            if addr in devices:
                devices[addr]["rssi"] = service_info.rssi
            elif MANUFACTURER_ID in service_info.manufacturer_data:
                name = service_info.name or f"Espruino {service_info.address}"
                devices[addr] = {
                    "address": service_info.address,
                    "name": name,
                    "rssi": service_info.rssi,
                    "connected": self.is_connected(service_info.address),
                }

        return list(devices.values())

    @callback
    def register_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Register a listener for events (incoming data and connection changes)."""
        self._listeners.append(listener)

        @callback
        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    @callback
    def _notify_listeners(self, event: dict[str, Any]) -> None:
        """Dispatch event to all registered listeners."""
        for listener in list(self._listeners):
            listener(event)

    def _make_disconnect_cb(
        self, address: str
    ) -> Callable[[BleakClientWithServiceCache], None]:
        """Create a disconnection callback for a client."""

        def _on_disconnect(_client: BleakClientWithServiceCache) -> None:
            _LOGGER.info("Espruino device disconnected: %s", address)
            self._clients.pop(address, None)
            self._notify_listeners(
                {"type": "connection", "address": address, "connected": False}
            )

        return _on_disconnect

    def _make_notify_cb(
        self, address: str
    ) -> Callable[[BleakGATTCharacteristic, bytearray], None]:
        """Create a notification callback for incoming UART data."""

        def _on_notify(
            _characteristic: BleakGATTCharacteristic, data: bytearray
        ) -> None:
            # Transmit as binary-transparent string (latin1 representation)
            data_str = bytes(data).decode("latin1")
            self._notify_listeners(
                {"type": "data", "address": address, "data": data_str}
            )

        return _on_notify

    async def async_connect(self, address: str) -> None:
        """Connect to an Espruino device and start Nordic UART notifications."""
        addr = address.upper()

        if self.is_connected(addr):
            _LOGGER.debug("Already connected to %s", addr)
            return

        await close_stale_connections_by_address(addr)

        ble_device: BLEDevice | None = bluetooth.async_ble_device_from_address(
            self.hass, addr, True
        ) or await get_device(addr)

        if not ble_device:
            raise HomeAssistantError(f"Espruino device not found at address {address}")

        try:
            client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=ble_device,
                name=ble_device.name or addr,
                disconnected_callback=self._make_disconnect_cb(addr),
                use_services_cache=True,
                ble_device_callback=lambda: bluetooth.async_ble_device_from_address(
                    self.hass, addr, True
                ),
            )
        except BleakError as err:
            _LOGGER.exception("Failed to connect to Espruino device %s", addr)
            raise HomeAssistantError(
                f"Failed to connect to Espruino device {address}: {err}"
            ) from err

        try:
            await client.start_notify(
                NORDIC_UART_TX_CHARACTERISTIC_UUID, self._make_notify_cb(addr)
            )
        except BleakError as err:
            _LOGGER.exception(
                "Failed to start UART notifications on Espruino device %s", addr
            )
            await client.disconnect()
            raise HomeAssistantError(
                f"Failed to enable UART notifications for {address}: {err}"
            ) from err

        self._clients[addr] = client
        self._notify_listeners(
            {"type": "connection", "address": addr, "connected": True}
        )

    async def async_disconnect(self, address: str) -> None:
        """Disconnect from an Espruino device."""
        addr = address.upper()
        client = self._clients.pop(addr, None)

        if client is not None and client.is_connected:
            with contextlib.suppress(BleakError):
                await client.stop_notify(NORDIC_UART_TX_CHARACTERISTIC_UUID)
            with contextlib.suppress(BleakError):
                await client.disconnect()

        self._notify_listeners(
            {"type": "connection", "address": addr, "connected": False}
        )

    async def async_write(self, address: str, data: bytes) -> None:
        """Write data to the Espruino device over Nordic UART RX characteristic."""
        addr = address.upper()
        client = self._clients.get(addr)

        if client is None or not client.is_connected:
            raise HomeAssistantError(f"Espruino device {address} is not connected")

        # Chunk writes (default BLE NUS chunk size is 20 bytes)
        mtu = getattr(client, "mtu_size", 23)
        chunk_size = max(20, min(mtu - 3, 100))

        try:
            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                await client.write_gatt_char(
                    NORDIC_UART_RX_CHARACTERISTIC_UUID, chunk, response=False
                )
        except BleakError as err:
            _LOGGER.exception("Failed to write data to Espruino device %s", addr)
            raise HomeAssistantError(
                f"Failed to write to Espruino device {address}: {err}"
            ) from err

    async def async_send_uart(self, address: str, data: bytes) -> None:
        """Connect, write data to Nordic UART RX, and disconnect."""
        await self.async_connect(address)
        try:
            await self.async_write(address, data)
        finally:
            await self.async_disconnect(address)

