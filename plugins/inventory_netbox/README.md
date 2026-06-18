<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-inventory-netbox

NetBox inventory provider for **Hegemony**. Reads and queries **devices** and **sites**
from a NetBox instance over its REST API and feeds them into the core inventory.

It is an out-of-tree plugin: it depends only on
[`hegemony-inventory-sdk`](../../packages/inventory_sdk) and is discovered at runtime via
the `hegemony.inventory_plugins` entry-point group
(`netbox = "hegemony_inventory_netbox:register"`).

## Install

Provider wheels are **opt-in** — they are not bundled in the default images.

```bash
pip install hegemony-inventory-netbox
# restart the API/worker so the plugin is registered
```

For Docker, add the wheel to the image that runs the API and the inventory worker.

## Configure

Create a `netbox` inventory provider (Settings → Inventory Providers, or
`POST /inventory/providers`). The provider form is schema-driven, so each field below is
rendered automatically and `token_ref` gets a secret picker.

| Field | Required | Default | Notes |
|---|---|---|---|
| `url` | yes | — | NetBox base URL, e.g. `https://netbox.example.com` |
| `token_ref` | yes | — | Secret **reference** to the API token, e.g. `{{ secret('vault://netbox/token') }}` — never the raw token |
| `auth_scheme` | no | `Bearer` | Authorization scheme prefixed to the resolved token |
| `auth_fallback_schemes` | no | `["Token"]` | Schemes retried on auth failure |
| `verify_tls` | no | `true` | Verify the TLS certificate |
| `custom_field_map` | no | ssh/enable refs | Maps `access_config` paths → NetBox custom fields |
| `default_access_config` | no | `{}` | Access-config defaults applied to every device |
| `query_cache_ttl_seconds` | no | `null` | Optional query cache TTL (0–86400 s) |
| `timeout_seconds` | no | `10` | Per-request timeout |

Minimal config:

```json
{
  "url": "https://netbox.example.com",
  "token_ref": "{{ secret('vault://netbox/token') }}"
}
```

### Platform

The device `platform` is mapped from NetBox's native `platform.slug`. When a device has
no platform in NetBox, the provider emits no value and the **core inventory service**
applies its default platform during materialization — there is no per-provider platform
setting.

## Supported object types

- `device`, `site` — core device/site inventory.
- `ip_prefix`, `ip_address`, `vlan` — NetBox IPAM prefixes/addresses and VLANs. They appear
  under the **Inventory** menu with schema-driven list/detail pages and sync alongside
  devices/sites whenever the provider syncs.

## Adding an object type

The IPAM/VLAN types are wired through two small tables, so adding another NetBox object type
(for example VRFs) is two edits plus a wheel release — no `list_objects` changes:

1. Add an endpoint → mapping entry to `_IPAM_OBJECT_SOURCES` in
   `src/hegemony_inventory_netbox/provider.py`:

   ```python
   "vrf": (
       "/api/ipam/vrfs/",
       ObjectFieldMapping(
           object_type="vrf",
           identity="id",
           name_field="name",
           field_map={"name": "name", "rd": "rd", "description": "description"},
       ),
   ),
   ```

2. Add a matching `ObjectTypeSpec` to `_OBJECT_TYPES` in
   `src/hegemony_inventory_netbox/__init__.py`, and add its id to `supported_resources`:

   ```python
   ObjectTypeSpec(
       id="vrf",
       display_name="VRF",
       plural="VRFs",
       field_schema={
           "type": "object",
           "properties": {"name": {"type": "string"}, "rd": {"type": ["string", "null"]}},
       },
       ui=ObjectTypeUIHints(columns=("name", "rd", "description")),
   ),
   ```

The provider's `list_objects` already dispatches any registered source through `map_records`,
so nothing else changes. After installing the new wheel version and restarting, the type
appears in the inventory submenu — no core change and no database migration.
