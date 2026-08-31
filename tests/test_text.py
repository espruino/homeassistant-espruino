"""Test the Espruino text platform."""

from unittest.mock import AsyncMock

import pytest

from homeassistant.components.espruino.const import (
    DOMAIN,
    NORDIC_UART_RX_CHARACTERISTIC_UUID,
)
from homeassistant.components.text import DOMAIN as TEXT_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from .conftest import MOCK_ADDRESS, MOCK_DISCOVERY_INFO, MockBleakClient

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info

pytestmark = pytest.mark.usefixtures("enable_bluetooth")


async def test_text_entity_set_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_bleak_client: MockBleakClient,
    mock_establish_connection: AsyncMock,
) -> None:
    """Test text entity connects, writes to Nordic UART RX, and disconnects."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("text.puck_js_1234")
    assert state is not None
    assert state.state == ""

    # Call text.set_value service
    await hass.services.async_call(
        TEXT_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "text.puck_js_1234",
            "value": "LED1.set()\n",
        },
        blocking=True,
    )

    # Verify state was updated
    state = hass.states.get("text.puck_js_1234")
    assert state is not None
    assert state.state == "LED1.set()\n"

    # Verify connection was established and then disconnected
    assert mock_establish_connection.call_count == 1
    assert hass.data[DOMAIN].manager.is_connected(MOCK_ADDRESS) is False

    # Verify data written to NORDIC_UART_RX_CHARACTERISTIC_UUID
    assert len(mock_bleak_client.written_data) == 1
    char_uuid, data, response = mock_bleak_client.written_data[0]
    assert char_uuid == NORDIC_UART_RX_CHARACTERISTIC_UUID
    assert data == b"LED1.set()\n"
    assert response is False

