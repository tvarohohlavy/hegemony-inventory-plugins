# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Git YAML inventory provider plugin."""

from typing import Any

from hegemony_inventory_sdk import (
    Capability,
    InventoryPluginRegistry,
    PlatformServices,
    ResourceType,
)

from .config import GitInventoryProviderConfig
from .provider import GitInventoryProvider


def build_git_provider(
    *, provider_id: str, config: dict[str, Any], services: PlatformServices
) -> GitInventoryProvider:
    return GitInventoryProvider(provider_id=provider_id, config=config, services=services)


def register(registry: InventoryPluginRegistry) -> None:
    """Entry point for the ``hegemony.inventory_plugins`` group."""
    registry.register_provider_type(
        provider_type="git",
        display_name="Git inventory",
        description="Read/query YAML inventory from a configured Git repository",
        capabilities=[Capability.READ.value, Capability.QUERY.value],
        supported_resources=[ResourceType.DEVICE.value, ResourceType.SITE.value],
        factory=build_git_provider,
        config_model=GitInventoryProviderConfig,
        default_config={"branch": "main", "refresh_strategy": "cache_ttl"},
    )


__all__ = ["GitInventoryProvider", "register"]
