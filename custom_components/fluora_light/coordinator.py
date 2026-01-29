from __future__ import annotations

import asyncio
import socket
from enum import StrEnum
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AUTO_HEX,
    BRIGHTNESS_HEX_FIRST,
    BRIGHTNESS_HEX_LAST,
    COLOR_EFFECTS,
    EFFECT_AUTO,
    EFFECT_WHITE,
    LOGGER,
    MANUAL_HEX,
    MAX_SATURATION_HEX,
    MIN_SATURATION_HEX,
    POWER_OFF_HEX,
    POWER_ON_HEX,
    SCENE_EFFECTS,
    SCENE_HEX,
    SCENE_HEX_DICT,
)


def scale_number(value: float, old_min: float, old_max: float, new_min: float, new_max: float) -> float:
    return ((value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min


def calculate_brightness_hex(desired_brightness: int) -> float:
    # Device brightness curve approximation.
    return scale_number((desired_brightness**0.1) - 1, 0, (100**0.1) - 1, 3932160, 4160442)


class LightState(StrEnum):
    """Coordinator state keys."""

    BRIGHTNESS = ATTR_BRIGHTNESS
    POWER = "power"
    EFFECT = ATTR_EFFECT


class LightCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Maintain local state and send UDP commands to the light."""

    def __init__(self, hass, device_id: str, conf: dict[str, Any]):
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"Fluora Light: {conf.get('name', '')}",
            update_method=self._async_update,
            update_interval=None,  # optimistic/local state only
        )

        self.device_id = device_id
        self.name: str = conf["name"]
        self.hostname: str = conf["hostname"]
        self.port: int = conf["port"]

        self._initialized = False
        self._ip_address: str | None = None
        self._sock: socket.socket | None = None
        self._send_lock = asyncio.Lock()

        # Default optimistic state (HA uses 0-255 brightness)
        self.data = {
            LightState.BRIGHTNESS: 255,
            LightState.POWER: True,
            LightState.EFFECT: EFFECT_AUTO,
        }

    @property
    def state(self) -> dict[str, Any]:
        return self.data

    async def _async_update(self) -> dict[str, Any]:
        if not self._initialized:
            await self._async_initialize()
        return self.data

    async def _async_initialize(self) -> None:
        try:
            self._ip_address = await self.hass.async_add_executor_job(
                socket.gethostbyname, self.hostname
            )

            def _make_socket() -> socket.socket:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5)
                sock.connect((self._ip_address, self.port))
                sock.settimeout(None)
                return sock

            self._sock = await self.hass.async_add_executor_job(_make_socket)
            self._initialized = True

            await self._async_send_hex(AUTO_HEX)
            self.data[LightState.EFFECT] = EFFECT_AUTO
            self.async_set_updated_data(self.data)
        except OSError as err:
            raise UpdateFailed(f"Failed to initialize Fluora Light at {self.hostname}:{self.port}") from err

    async def async_close(self) -> None:
        sock = self._sock
        self._sock = None
        self._initialized = False
        if sock is not None:
            await self.hass.async_add_executor_job(sock.close)

    async def _async_send_hex(self, hex_payload: str) -> None:
        if not self._initialized:
            await self._async_initialize()
        if self._sock is None:
            raise UpdateFailed("Socket not initialized")

        payload = bytearray.fromhex(hex_payload)
        async with self._send_lock:
            await self.hass.async_add_executor_job(self._sock.send, payload)

    async def async_update_state(self, key: LightState, value: Any) -> bool:
        if not self._initialized:
            await self._async_initialize()

        if key == LightState.BRIGHTNESS:
            desired_brightness = round(int(value) * 100 / 255)
            brightness_hex_value = int(calculate_brightness_hex(desired_brightness))
            brightness_hex = f"{brightness_hex_value:06x}"
            await self._async_send_hex(BRIGHTNESS_HEX_FIRST + brightness_hex + BRIGHTNESS_HEX_LAST)

        elif key == LightState.EFFECT:
            if value in SCENE_EFFECTS:
                await self._async_send_hex(SCENE_HEX)
                await asyncio.sleep(0.1)
                await self._async_send_hex(SCENE_HEX_DICT[value])
            elif value == EFFECT_AUTO:
                await self._async_send_hex(AUTO_HEX)
            elif value == EFFECT_WHITE:
                await self._async_send_hex(MANUAL_HEX)
                await asyncio.sleep(0.1)
                await self._async_send_hex(MIN_SATURATION_HEX)
            elif value in COLOR_EFFECTS:
                await self._async_send_hex(MANUAL_HEX)
                await asyncio.sleep(0.1)
                await self._async_send_hex(MAX_SATURATION_HEX)
                await asyncio.sleep(0.1)
                await self._async_send_hex(SCENE_HEX_DICT[value])
            else:
                return False

        elif key == LightState.POWER:
            await self._async_send_hex(POWER_ON_HEX if value else POWER_OFF_HEX)

        else:
            return False

        self.data[key] = value
        self.async_set_updated_data(self.data)
        return True

