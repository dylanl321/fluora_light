"""Base entity class for Fluora Light integration."""

from __future__ import annotations

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LightCoordinator


class FluoraLightBaseEntity(CoordinatorEntity[LightCoordinator]):
    """Fluora Light base entity class."""

    def __init__(self, coordinator: LightCoordinator, description: EntityDescription):
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_unique_id = f"{coordinator.hostname}-{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.hostname)},
            "name": coordinator.name,
            "manufacturer": "Fluora",
        }
