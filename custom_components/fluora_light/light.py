from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityDescription,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, EFFECT_LIST
from .coordinator import LightCoordinator, LightState
from .entity import FluoraLightBaseEntity


LIGHT_DESCRIPTION = LightEntityDescription(
    key="light",
    name="Light",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LightCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([FluoraLightEntity(coordinator, LIGHT_DESCRIPTION)], update_before_add=True)


class FluoraLightEntity(FluoraLightBaseEntity, LightEntity):
    """Representation of a Fluora Light."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_assumed_state = True

    def __init__(self, coordinator: LightCoordinator, description: LightEntityDescription) -> None:
        super().__init__(coordinator, description)
        self._attr_effect_list = EFFECT_LIST

    @property
    def color_mode(self) -> ColorMode:
        return ColorMode.BRIGHTNESS

    @property
    def brightness(self) -> int | None:
        return self.coordinator.state[LightState.BRIGHTNESS]

    @property
    def effect(self) -> str | None:
        return self.coordinator.state[LightState.EFFECT]

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.state[LightState.POWER])

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self.coordinator.async_update_state(LightState.POWER, True)

        if ATTR_BRIGHTNESS in kwargs:
            await self.coordinator.async_update_state(LightState.BRIGHTNESS, kwargs[ATTR_BRIGHTNESS])

        if ATTR_EFFECT in kwargs:
            await self.coordinator.async_update_state(LightState.EFFECT, kwargs[ATTR_EFFECT])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_update_state(LightState.POWER, False)

