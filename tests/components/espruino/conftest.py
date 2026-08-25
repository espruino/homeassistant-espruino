"""Fixtures for Espruino integration tests."""

from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, patch

from bleak.backends.characteristic import BleakGATTCharacteristic
from home_assistant_bluetooth import BluetoothServiceInfoBleak
import pytest

from homeassistant.components.espruino.const import DOMAIN, MANUFACTURER_ID
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.device_registry import format_mac

from tests.common import MockConfigEntry
from tests.components.bluetooth import generate_advertisement_data, generate_ble_device

MOCK_ADDRESS = "AA:BB:CC:DD:EE:FF"
MOCK_NAME = "Puck.js 1234"

MOCK_DISCOVERY_INFO = BluetoothServiceInfoBleak(
    name=MOCK_NAME,
    address=MOCK_ADDRESS,
    device=generate_ble_device(
        address=MOCK_ADDRESS,
        name=MOCK_NAME,
    ),
    rssi=-60,
    manufacturer_data={MANUFACTURER_ID: b"\x01\x02"},
    service_data={},
    service_uuids=["6e400001-b5a3-f393-e0a9-e50e24dcca9e"],
    source="local",
    advertisement=generate_advertisement_data(
        manufacturer_data={MANUFACTURER_ID: b"\x01\x02"},
        service_uuids=["6e400001-b5a3-f393-e0a9-e50e24dcca9e"],
    ),
    connectable=True,
    time=0,
    tx_power=None,
)

MOCK_OTHER_DISCOVERY_INFO = BluetoothServiceInfoBleak(
    name="Other Device",
    address="11:22:33:44:55:66",
    device=generate_ble_device(
        address="11:22:33:44:55:66",
        name="Other Device",
    ),
    rssi=-70,
    manufacturer_data={9999: b"\x00"},
    service_data={},
    service_uuids=[],
    source="local",
    advertisement=generate_advertisement_data(
        manufacturer_data={9999: b"\x00"},
        service_uuids=[],
    ),
    connectable=True,
    time=0,
    tx_power=None,
)


class MockBleakClient:
    """Mock BleakClient for testing."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize mock BleakClient."""
        self._is_connected = True
        self.mtu_size = 23
        self.notify_callbacks: dict[
            str, Callable[[BleakGATTCharacteristic, bytearray], None]
        ] = {}
        self.written_data: list[tuple[str, bytes, bool]] = []
        self.disconnected_callback = kwargs.get("disconnected_callback")

    @property
    def is_connected(self) -> bool:
        """Return connection state."""
        return self._is_connected

    async def connect(self, *args: object, **kwargs: object) -> bool:
        """Connect to device."""
        self._is_connected = True
        return True

    async def disconnect(self, *args: object, **kwargs: object) -> bool:
        """Disconnect from device."""
        self._is_connected = False
        if self.disconnected_callback:
            self.disconnected_callback(self)
        return True

    async def start_notify(
        self,
        char_uuid: str,
        callback: Callable[[BleakGATTCharacteristic, bytearray], None],
    ) -> None:
        """Start notifications."""
        self.notify_callbacks[char_uuid] = callback

    async def stop_notify(self, char_uuid: str) -> None:
        """Stop notifications."""
        self.notify_callbacks.pop(char_uuid, None)

    async def write_gatt_char(
        self, char_uuid: str, data: bytes, response: bool = False
    ) -> None:
        """Write to characteristic."""
        self.written_data.append((char_uuid, data, response))


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=format_mac(MOCK_ADDRESS),
        title=MOCK_NAME,
        data={
            CONF_ADDRESS: MOCK_ADDRESS,
        },
    )


@pytest.fixture
def mock_bleak_client() -> MockBleakClient:
    """Return a mock Bleak client instance."""
    return MockBleakClient()


@pytest.fixture
def mock_establish_connection(
    mock_bleak_client: MockBleakClient,
) -> Generator[AsyncMock]:
    """Mock establish_connection."""
    with patch(
        "homeassistant.components.espruino.connection.establish_connection",
        AsyncMock(return_value=mock_bleak_client),
    ) as mock_conn:
        yield mock_conn
