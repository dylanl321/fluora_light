from __future__ import annotations

import asyncio
import socket
import struct
from enum import StrEnum
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_HS_COLOR
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AUTO_HEX,
    BRIGHTNESS_HEX_FIRST,
    BRIGHTNESS_HEX_LAST,
    COLOR_EFFECTS,
    EFFECT_AUTO,
    EFFECT_CUSTOM,
    EFFECT_WHITE,
    HUE_OFFSET,
    HUE_ROUTE,
    LOGGER,
    MANUAL_HEX,
    MANUAL_SIZE_ROUTE,
    MANUAL_SPEED_ROUTE,
    MAX_SATURATION_HEX,
    SATURATION_MAX,
    SATURATION_MIN,
    SATURATION_ROUTE,
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
    HS_COLOR = ATTR_HS_COLOR
    SPEED = "speed"
    SIZE = "size"


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
            LightState.HS_COLOR: (0.0, 100.0),
            LightState.SPEED: 0.5,
            LightState.SIZE: 0.5,
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

    def _osc_payload(self, route: str, typetags: str, args: list[Any]) -> bytes:
        """Create an OSC-like payload.

        The Fluora device speaks an OSC-style protocol: address string, type tags, then big-endian args.
        """

        def _pad4(b: bytes) -> bytes:
            return b + (b"\x00" * ((4 - (len(b) % 4)) % 4))

        if not typetags.startswith(","):
            raise ValueError("typetags must start with ',' (e.g. ',fi')")

        addr = _pad4(route.encode("ascii") + b"\x00")
        tags = _pad4(typetags.encode("ascii") + b"\x00")

        out = bytearray()
        out += addr
        out += tags

        tag_list = typetags[1:]
        if len(tag_list) != len(args):
            raise ValueError("typetags and args length mismatch")

        for tag, arg in zip(tag_list, args, strict=True):
            if tag == "f":
                out += struct.pack(">f", float(arg))
            elif tag == "i":
                out += struct.pack(">i", int(arg))
            else:
                raise ValueError(f"Unsupported OSC tag: {tag!r}")

        return bytes(out)

    async def _async_send_osc(self, route: str, typetags: str, args: list[Any]) -> None:
        payload = self._osc_payload(route, typetags, args)
        async with self._send_lock:
            if not self._initialized:
                await self._async_initialize()
            if self._sock is None:
                raise UpdateFailed("Socket not initialized")
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
            elif value == EFFECT_CUSTOM:
                # "Custom" is set by HS color control; selecting it directly is a no-op.
                return False
            else:
                return False

        elif key == LightState.POWER:
            await self._async_send_hex(POWER_ON_HEX if value else POWER_OFF_HEX)

        elif key == LightState.HS_COLOR:
            # HA gives (hue_deg 0-360, sat_pct 0-100)
            hue_deg, sat_pct = value

            # Convert to the device's 0..1 float space (with a hue wheel offset).
            hue = (float(hue_deg) / 360.0 + HUE_OFFSET) % 1.0

            sat_pct = max(0.0, min(100.0, float(sat_pct)))
            sat = SATURATION_MIN + (sat_pct / 100.0) * (SATURATION_MAX - SATURATION_MIN)

            # Switch to manual mode then update palette.
            await self._async_send_hex(MANUAL_HEX)
            await asyncio.sleep(0.05)
            await self._async_send_osc(SATURATION_ROUTE, ",fi", [sat, 0])
            await asyncio.sleep(0.05)
            await self._async_send_osc(HUE_ROUTE, ",fi", [hue, 0])

            # reflect state in HA
            self.data[LightState.EFFECT] = EFFECT_CUSTOM

        elif key == LightState.SPEED:
            speed = max(0.0, min(1.0, float(value)))
            await self._async_send_osc(MANUAL_SPEED_ROUTE, ",fi", [speed, 0])

        elif key == LightState.SIZE:
            size = max(0.0, min(1.0, float(value)))
            await self._async_send_osc(MANUAL_SIZE_ROUTE, ",fi", [size, 0])

        else:
            return False

        self.data[key] = value
        self.async_set_updated_data(self.data)
        return True

