<!--
SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>

SPDX-License-Identifier: AGPL-3.0-or-later
-->

# hegemony-inventory-sdk

Public, dependency-light SDK for building **Hegemony inventory plugins** —
out-of-tree provider and object-type wheels that the core platform loads at
runtime.

A plugin depends only on this package (which depends only on `pydantic`) and
exposes a `register(registry)` callable under the `hegemony.inventory_plugins`
entry-point group:

```toml
# In your plugin's pyproject.toml
[project.entry-points."hegemony.inventory_plugins"]
my_plugin = "my_plugin:register"

[project.dependencies]
hegemony-inventory-sdk = ">=0.1,<0.2"
```

```python
# my_plugin/__init__.py
from hegemony_inventory_sdk import InventoryPluginRegistry, InventoryProvider


def register(registry: InventoryPluginRegistry) -> None:
    registry.register_provider_type(
        provider_type="acme",
        display_name="Acme",
        description="Acme inventory",
        capabilities=["read", "query"],
        supported_resources=["device"],
        factory=build_acme_provider,
        config_model=AcmeConfig,
    )
```

The public contract — provider base class, value objects, enums, error
envelopes, the object-type declaration API, and the registry/secret/transport
protocols — is re-exported from the top-level `hegemony_inventory_sdk` package.
`SDK_ABI_VERSION` identifies the registration ABI; the core platform pins a
compatible range.
