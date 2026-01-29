from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LightCoordinator, LightState
from .entity import FluoraLightBaseEntity


@dataclass(frozen=True, kw_only=True)
class FluoraNumberEntityDescription(NumberEntityDescription):
    state_key: LightState


NUMBER_DESCRIPTIONS: tuple[FluoraNumberEntityDescription, ...] = (
    FluoraNumberEntityDescription(
        key="speed",
        name="Speed",
        state_key=LightState.SPEED,
        native_min_value=0.0,
        native_max_value=1.0,
        native_step=0.01,
    ),
    FluoraNumberEntityDescription(
        key="size",
        name="Size",
        state_key=LightState.SIZE,
        native_min_value=0.0,
        native_max_value=1.0,
        native_step=0.01,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LightCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [FluoraNumberEntity(coordinator, description) for description in NUMBER_DESCRIPTIONS],
        update_before_add=True,
    )


class FluoraNumberEntity(FluoraLightBaseEntity, NumberEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LightCoordinator, description: FluoraNumberEntityDescription) -> None:
        super().__init__(coordinator, description)
        self.entity_description: FluoraNumberEntityDescription = description

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.state.get(self.entity_description.state_key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_state(self.entity_description.state_key, value)

