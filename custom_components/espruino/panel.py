"""Espruino frontend panel registration."""

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, URL_BASE


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the Espruino frontend panel."""
    frontend_path = Path(__file__).parent / "frontend"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(frontend_path), cache_headers=False)]
    )

    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=DOMAIN,
        webcomponent_name="espruino-panel",
        sidebar_title="Espruino",
        sidebar_icon="mdi:code-braces",
        module_url=f"{URL_BASE}/espruino-panel.js",
        embed_iframe=False,
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
