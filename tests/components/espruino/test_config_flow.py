"""Test the Espruino config flow."""

import pytest

from homeassistant.components.espruino.const import DOMAIN
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.device_registry import format_mac

from .conftest import (
    MOCK_ADDRESS,
    MOCK_DISCOVERY_INFO,
    MOCK_NAME,
    MOCK_OTHER_DISCOVERY_INFO,
)

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info

pytestmark = pytest.mark.usefixtures("enable_bluetooth")


async def test_bluetooth_discovery(hass: HomeAssistant) -> None:
    """Test Bluetooth discovery step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=MOCK_DISCOVERY_INFO,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    assert result["description_placeholders"] == {"name": MOCK_NAME}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_NAME
    assert result2["data"] == {
        CONF_ADDRESS: MOCK_ADDRESS,
    }
    assert result2["result"].unique_id == format_mac(MOCK_ADDRESS)


async def test_bluetooth_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test Bluetooth discovery aborts when device is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=MOCK_DISCOVERY_INFO,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test user initialized flow."""
    inject_bluetooth_service_info(hass, MOCK_OTHER_DISCOVERY_INFO)
    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_ADDRESS: MOCK_ADDRESS},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_NAME
    assert result2["data"] == {
        CONF_ADDRESS: MOCK_ADDRESS,
    }
    assert result2["result"].unique_id == format_mac(MOCK_ADDRESS)


async def test_user_flow_no_devices(hass: HomeAssistant) -> None:
    """Test user flow when no Espruino devices are discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_flow_all_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test user flow when all discovered devices are already configured."""
    mock_config_entry.add_to_hass(hass)
    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
