# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""NetBox inventory provider plugin."""

from typing import Any

from hegemony_inventory_sdk import (
    Capability,
    InventoryPluginRegistry,
    ObjectTypeSpec,
    ObjectTypeUIHints,
    PlatformServices,
    ResourceType,
)

from .config import NetBoxProviderConfig
from .provider import NetBoxInventoryProvider

# Net-new object types served by NetBox beyond device/site. Each has a matching source
# mapping in provider.py (``_IPAM_OBJECT_SOURCES``); together they make these appear in
# the schema-driven inventory UI with no per-type frontend code.
_OBJECT_TYPES: list[ObjectTypeSpec] = [
    ObjectTypeSpec(
        id=ResourceType.IP_PREFIX.value,
        display_name="IP Prefix",
        plural="IP Prefixes",
        description="IP prefixes / subnets from NetBox IPAM.",
        field_schema={
            "type": "object",
            "properties": {
                "prefix": {"type": "string"},
                "status": {"type": ["string", "null"]},
                "vlan": {"type": ["integer", "null"]},
                "role": {"type": ["string", "null"]},
                "site": {"type": ["string", "null"]},
                "tenant": {"type": ["string", "null"]},
                "is_pool": {"type": ["boolean", "null"]},
                "description": {"type": ["string", "null"]},
            },
        },
        identity_keys=("prefix",),
        ui=ObjectTypeUIHints(
            icon="network",
            columns=("name", "status", "vlan", "role", "site"),
            search_fields=("name", "description"),
        ),
    ),
    ObjectTypeSpec(
        id=ResourceType.IP_ADDRESS.value,
        display_name="IP Address",
        plural="IP Addresses",
        description="IP addresses from NetBox IPAM.",
        field_schema={
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "status": {"type": ["string", "null"]},
                "role": {"type": ["string", "null"]},
                "dns_name": {"type": ["string", "null"]},
                "vrf": {"type": ["string", "null"]},
                "tenant": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
            },
        },
        identity_keys=("address",),
        ui=ObjectTypeUIHints(
            icon="network",
            columns=("name", "status", "dns_name", "description"),
            search_fields=("name", "dns_name"),
        ),
    ),
    ObjectTypeSpec(
        id=ResourceType.VLAN.value,
        display_name="VLAN",
        plural="VLANs",
        description="VLANs from NetBox IPAM.",
        field_schema={
            "type": "object",
            "properties": {
                "vid": {"type": ["integer", "null"]},
                "name": {"type": "string"},
                "status": {"type": ["string", "null"]},
                "site": {"type": ["string", "null"]},
                "group": {"type": ["string", "null"]},
                "role": {"type": ["string", "null"]},
                "tenant": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
            },
        },
        identity_keys=("vid", "site"),
        ui=ObjectTypeUIHints(
            icon="layers",
            columns=("name", "vid", "status", "site", "role"),
            search_fields=("name",),
        ),
    ),
]


def build_netbox_provider(
    *, provider_id: str, config: dict[str, Any], services: PlatformServices
) -> NetBoxInventoryProvider:
    return NetBoxInventoryProvider(provider_id=provider_id, config=config, services=services)


def register(registry: InventoryPluginRegistry) -> None:
    """Entry point for the ``hegemony.inventory_plugins`` group."""
    for spec in _OBJECT_TYPES:
        registry.register_object_type(spec)
    registry.register_provider_type(
        provider_type="netbox",
        display_name="NetBox",
        description="Read/query devices, sites, and IPAM/VLAN objects from NetBox",
        capabilities=[Capability.READ.value, Capability.QUERY.value],
        supported_resources=[
            ResourceType.DEVICE.value,
            ResourceType.SITE.value,
            ResourceType.IP_PREFIX.value,
            ResourceType.IP_ADDRESS.value,
            ResourceType.VLAN.value,
        ],
        factory=build_netbox_provider,
        config_model=NetBoxProviderConfig,
        default_config={
            "verify_tls": True,
            "query_cache_ttl_seconds": None,
            "timeout_seconds": 10.0,
        },
    )


__all__ = ["NetBoxInventoryProvider", "register"]
