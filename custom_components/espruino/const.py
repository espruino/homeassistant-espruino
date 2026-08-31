"""Constants for the Espruino integration."""

from typing import Final

DOMAIN: Final = "espruino"

MANUFACTURER_ID: Final = 0x0590  # 1424 in decimal

# Nordic UART Service (NUS) UUIDs
NORDIC_UART_SERVICE_UUID: Final = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NORDIC_UART_RX_CHARACTERISTIC_UUID: Final = (
    "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Host Write -> Device
)
NORDIC_UART_TX_CHARACTERISTIC_UUID: Final = (
    "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Device Notify -> Host
)

DEFAULT_WEB_IDE_URL: Final = "https://www.espruino.com/ide/"
URL_BASE: Final = "/espruino_static"
