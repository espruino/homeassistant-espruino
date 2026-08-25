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


async def test_user_flow_other_device(hass: HomeAssistant) -> None:
    """Test user initialized flow selecting a non-Espruino Bluetooth device."""
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
        user_input={CONF_ADDRESS: MOCK_OTHER_DISCOVERY_INFO.address},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_OTHER_DISCOVERY_INFO.name
    assert result2["data"] == {
        CONF_ADDRESS: MOCK_OTHER_DISCOVERY_INFO.address,
    }
    assert result2["result"].unique_id == format_mac(MOCK_OTHER_DISCOVERY_INFO.address)


async def test_user_flow_manual_entry(hass: HomeAssistant) -> None:
    """Test user initialized flow entering MAC address manually from dropdown."""
    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select "manual" option
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_ADDRESS: "manual"},
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "manual"

    # Enter invalid address first
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_ADDRESS: "invalid-mac"},
    )

    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == "manual"
    assert result3["errors"] == {CONF_ADDRESS: "invalid_address"}

    # Enter valid address
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"],
        user_input={CONF_ADDRESS: "12:34:56:78:9A:BC"},
    )

    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert result4["title"] == "Espruino 12:34:56:78:9a:bc"
    assert result4["data"] == {
        CONF_ADDRESS: "12:34:56:78:9A:BC",
    }
    assert result4["result"].unique_id == "12:34:56:78:9a:bc"


async def test_user_flow_no_devices(hass: HomeAssistant) -> None:
    """Test user flow when no devices are discovered falls back to manual entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_ADDRESS: "12:34:56:78:9A:BC"},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Espruino 12:34:56:78:9a:bc"


async def test_user_flow_all_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test user flow when all discovered devices are already configured falls back to manual."""
    mock_config_entry.add_to_hass(hass)
    inject_bluetooth_service_info(hass, MOCK_DISCOVERY_INFO)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

