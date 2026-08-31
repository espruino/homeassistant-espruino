"""Test Espruino websocket API."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.espruino.const import (
    DOMAIN,
    NORDIC_UART_TX_CHARACTERISTIC_UUID,
)
from homeassistant.core import HomeAssistant

from .conftest import MOCK_ADDRESS, MOCK_DISCOVERY_INFO, MOCK_NAME, MockBleakClient

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info
from tests.typing import WebSocketGenerator

pytestmark = pytest.mark.usefixtures("enable_bluetooth")


async def test_ws_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test espruino/devices websocket command."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "espruino/devices",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["success"]
    devices = response["result"]
    assert len(devices) == 1
    assert devices[0]["address"] == MOCK_ADDRESS
    assert devices[0]["name"] == MOCK_NAME
    assert devices[0]["connected"] is False


async def test_ws_connect_and_disconnect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_bleak_client: MockBleakClient,
    mock_establish_connection: AsyncMock,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test espruino/connect and espruino/disconnect websocket commands."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    client = await hass_ws_client(hass)

    # Connect
    await client.send_json(
        {
            "id": 2,
            "type": "espruino/connect",
            "address": MOCK_ADDRESS,
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"connected": True}
    assert hass.data[DOMAIN].manager.is_connected(MOCK_ADDRESS) is True

    # Disconnect
    await client.send_json(
        {
            "id": 3,
            "type": "espruino/disconnect",
            "address": MOCK_ADDRESS,
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"disconnected": True}
    assert hass.data[DOMAIN].manager.is_connected(MOCK_ADDRESS) is False


async def test_ws_connect_device_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test espruino/connect with non-existent device."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 4,
            "type": "espruino/connect",
            "address": "00:11:22:33:44:55",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert not response["success"]
    assert response["error"]["code"] == "home_assistant_error"


async def test_ws_write(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_bleak_client: MockBleakClient,
    mock_establish_connection: AsyncMock,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test espruino/write command."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    client = await hass_ws_client(hass)

    # Write before connecting -> fails
    await client.send_json(
        {
            "id": 5,
            "type": "espruino/write",
            "address": MOCK_ADDRESS,
            "data": "LED1.set()\n",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert not response["success"]
    assert response["error"]["code"] == "home_assistant_error"

    # Connect
    await client.send_json(
        {
            "id": 6,
            "type": "espruino/connect",
            "address": MOCK_ADDRESS,
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()
    assert response["success"]

    # Write after connecting -> succeeds
    await client.send_json(
        {
            "id": 7,
            "type": "espruino/write",
            "address": MOCK_ADDRESS,
            "data": "LED1.set()\n",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()

    assert response["success"]
    assert response["result"] == {"written": True}
    assert len(mock_bleak_client.written_data) == 1
    assert mock_bleak_client.written_data[0][1] == b"LED1.set()\n"


async def test_ws_subscribe_and_events(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_bleak_client: MockBleakClient,
    mock_establish_connection: AsyncMock,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test espruino/subscribe and event dispatching."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    client = await hass_ws_client(hass)

    # Subscribe
    await client.send_json(
        {
            "id": 8,
            "type": "espruino/subscribe",
        }
    )
    async with asyncio.timeout(1):
        response = await client.receive_json()
    assert response["success"]

    # Connect to device -> should trigger connection event
    await client.send_json(
        {
            "id": 9,
            "type": "espruino/connect",
            "address": MOCK_ADDRESS,
        }
    )
    async with asyncio.timeout(1):
        # We might receive the event or the command response in order
        msg1 = await client.receive_json()
        msg2 = await client.receive_json()

    messages = [msg1, msg2]
    event_msg = next((m for m in messages if m.get("type") == "event"), None)
    result_msg = next((m for m in messages if "result" in m), None)

    assert result_msg is not None and result_msg["success"]
    assert event_msg is not None
    assert event_msg["event"] == {
        "type": "connection",
        "address": MOCK_ADDRESS,
        "connected": True,
    }

    # Simulate notify from device
    notify_cb = mock_bleak_client.notify_callbacks[NORDIC_UART_TX_CHARACTERISTIC_UUID]
    notify_cb(None, bytearray(b"Hello from Espruino!"))

    async with asyncio.timeout(1):
        data_event = await client.receive_json()

    assert data_event["type"] == "event"
    assert data_event["event"] == {
        "type": "data",
        "address": MOCK_ADDRESS,
        "data": "Hello from Espruino!",
    }

    # Disconnect -> should trigger disconnection event
    await client.send_json(
        {
            "id": 10,
            "type": "espruino/disconnect",
            "address": MOCK_ADDRESS,
        }
    )
    async with asyncio.timeout(1):
        msg1 = await client.receive_json()
        msg2 = await client.receive_json()

    messages = [msg1, msg2]
    disconnect_event = next((m for m in messages if m.get("type") == "event"), None)
    disconnect_result = next((m for m in messages if "result" in m), None)

    assert disconnect_result is not None and disconnect_result["success"]
    assert disconnect_event is not None
    assert disconnect_event["event"] == {
        "type": "connection",
        "address": MOCK_ADDRESS,
        "connected": False,
    }
