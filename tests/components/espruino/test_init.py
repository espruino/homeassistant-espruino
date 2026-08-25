"""Test Espruino component setup."""

import pytest

from homeassistant.components.espruino.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import MOCK_ADDRESS, MOCK_NAME

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_bluetooth")


async def test_async_setup_entry_and_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful setup and unload of config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert DOMAIN in hass.data

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, MOCK_ADDRESS), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.name == MOCK_NAME
    assert device.manufacturer == "Espruino"

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
