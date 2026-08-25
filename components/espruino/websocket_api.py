"""Websocket API for the Espruino integration."""

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register Espruino websocket commands."""
    websocket_api.async_register_command(hass, ws_devices)
    websocket_api.async_register_command(hass, ws_connect)
    websocket_api.async_register_command(hass, ws_disconnect)
    websocket_api.async_register_command(hass, ws_write)
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "espruino/devices",
    }
)
@callback
def ws_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get Espruino devices."""
    manager = hass.data[DOMAIN].manager
    devices = manager.get_discovered_devices()
    connection.send_result(msg["id"], devices)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "espruino/connect",
        vol.Required("address"): str,
    }
)
@websocket_api.async_response
async def ws_connect(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle connect to Espruino device."""
    manager = hass.data[DOMAIN].manager
    try:
        await manager.async_connect(msg["address"])
        connection.send_result(msg["id"], {"connected": True})
    except HomeAssistantError as err:
        connection.send_error(
            msg["id"],
            websocket_api.const.ERR_HOME_ASSISTANT_ERROR,
            str(err),
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "espruino/disconnect",
        vol.Required("address"): str,
    }
)
@websocket_api.async_response
async def ws_disconnect(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle disconnect from Espruino device."""
    manager = hass.data[DOMAIN].manager
    try:
        await manager.async_disconnect(msg["address"])
        connection.send_result(msg["id"], {"disconnected": True})
    except HomeAssistantError as err:
        connection.send_error(
            msg["id"],
            websocket_api.const.ERR_HOME_ASSISTANT_ERROR,
            str(err),
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "espruino/write",
        vol.Required("address"): str,
        vol.Required("data"): str,
    }
)
@websocket_api.async_response
async def ws_write(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle write data to Espruino device."""
    manager = hass.data[DOMAIN].manager
    raw_data = msg["data"].encode("latin1", errors="replace")
    try:
        await manager.async_write(msg["address"], raw_data)
        connection.send_result(msg["id"], {"written": True})
    except HomeAssistantError as err:
        connection.send_error(
            msg["id"],
            websocket_api.const.ERR_HOME_ASSISTANT_ERROR,
            str(err),
        )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "espruino/subscribe",
    }
)
@callback
def ws_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Subscribe to Espruino data and connection events."""
    manager = hass.data[DOMAIN].manager

    @callback
    def forward_event(event: dict[str, Any]) -> None:
        connection.send_event(msg["id"], event)

    unsubscribe = manager.register_listener(forward_event)
    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
