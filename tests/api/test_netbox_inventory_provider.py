# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""NetBox inventory provider HTTP semantics."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from hegemony_inventory_netbox import provider as netbox_provider_module
from hegemony_inventory_netbox.provider import NetBoxInventoryProvider
from hegemony_inventory_sdk import InventoryProviderError, ProviderCallContext, ProviderErrorCode
from tests.inventory_fakes import FakePlatformServices


def _provider(
    config: dict[str, Any] | None = None, *, token: str | None = None
) -> NetBoxInventoryProvider:
    provider_config = {
        "url": "https://netbox.example",
        "token_ref": "{{ secret('vault://inventory/netbox/token') }}",
        **(config or {}),
    }
    return NetBoxInventoryProvider(
        provider_id="netbox:primary",
        config=provider_config,
        services=FakePlatformServices(
            token=token, provider_id="netbox:primary", provider_type="netbox"
        ),
    )


def _install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: httpx.MockTransport,
) -> None:
    real_async_client = httpx.AsyncClient

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(transport=handler, **kwargs)

    monkeypatch.setattr(netbox_provider_module.httpx, "AsyncClient", client_factory)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "resolved_token", "expected_header"),
    [
        ({}, "netbox-token", "Bearer netbox-token"),
        ({"auth_scheme": "Token"}, "netbox-token", "Token netbox-token"),
        ({}, "Bearer netbox-token", "Bearer netbox-token"),
        ({"auth_scheme": "Bearer"}, "Token netbox-token", "Token netbox-token"),
    ],
)
async def test_netbox_authorization_header_is_configurable_without_duplicate_prefix(
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, Any],
    resolved_token: str,
    expected_header: str,
) -> None:
    captured: dict[str, str | None] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"results": [], "next": None})

    _install_transport(monkeypatch, httpx.MockTransport(handler))

    provider = _provider(config, token=resolved_token)
    await provider.query_devices(
        "",
        limit=10,
        context=ProviderCallContext(
            provider_id="netbox:primary",
            operation="query_devices",
            query_hash="auth-test",
            config_version=1,
        ),
    )

    assert captured["authorization"] == expected_header


@pytest.mark.asyncio
async def test_netbox_unprefixed_token_retries_token_after_bearer_auth_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str | None] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        authorization = request.headers.get("authorization")
        captured.append(authorization)
        if authorization == "Bearer netbox-token":
            return httpx.Response(403, json={"detail": "forbidden"})
        return httpx.Response(200, json={"results": [], "next": None})

    _install_transport(monkeypatch, httpx.MockTransport(handler))

    provider = _provider(token="netbox-token")
    await provider.query_devices(
        "",
        limit=10,
        context=ProviderCallContext(
            provider_id="netbox:primary",
            operation="query_devices",
            query_hash="auth-fallback-test",
            config_version=1,
        ),
    )

    assert captured == ["Bearer netbox-token", "Token netbox-token"]


@pytest.mark.asyncio
async def test_netbox_client_400_returns_safe_malformed_query_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "provider payload stays private"})

    _install_transport(monkeypatch, httpx.MockTransport(handler))

    provider = _provider(token="netbox-token")
    with pytest.raises(InventoryProviderError) as exc_info:
        await provider.query_devices(
            "bad=query",
            limit=10,
            context=ProviderCallContext(
                provider_id="netbox:primary",
                operation="query_devices",
                query_hash="bad-query",
                config_version=1,
            ),
        )

    envelope = exc_info.value.envelope
    assert envelope.code == ProviderErrorCode.MALFORMED_QUERY
    assert envelope.message == "NetBox rejected the query or request"
    assert envelope.safe_details == {"status_code": 400}
    assert envelope.retryable is False
    assert "provider payload" not in envelope.message


@pytest.mark.asyncio
async def test_netbox_transient_failures_retry_four_times_with_one_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []
    client_creations = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url.path)
        if len(captured) < 4:
            return httpx.Response(500, json={"detail": "temporary"})
        return httpx.Response(200, json={"results": [], "next": None})

    async def no_sleep(_seconds: float) -> None:
        return None

    real_async_client = httpx.AsyncClient

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        nonlocal client_creations
        client_creations += 1
        return real_async_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(netbox_provider_module.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(netbox_provider_module.asyncio, "sleep", no_sleep)

    provider = _provider(token="netbox-token")
    await provider.query_devices(
        "",
        limit=10,
        context=ProviderCallContext(
            provider_id="netbox:primary",
            operation="query_devices",
            query_hash="retry-test",
            config_version=1,
        ),
    )

    assert len(captured) == 4
    assert client_creations == 1


@pytest.mark.asyncio
async def test_netbox_rejects_off_origin_pagination_before_sending_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.url.host or "", request.headers.get("authorization")))
        return httpx.Response(
            200,
            json={"results": [], "next": "https://evil.example/api/dcim/devices/?limit=10"},
        )

    _install_transport(monkeypatch, httpx.MockTransport(handler))

    provider = _provider(token="netbox-token")
    with pytest.raises(InventoryProviderError) as exc_info:
        await provider.query_devices(
            "",
            limit=10,
            context=ProviderCallContext(
                provider_id="netbox:primary",
                operation="query_devices",
                query_hash="pagination-origin-test",
                config_version=1,
            ),
        )

    assert exc_info.value.envelope.code == ProviderErrorCode.SCHEMA_VALIDATION_FAILED
    assert captured == [("netbox.example", "Bearer netbox-token")]


def test_netbox_mapping_does_not_stringify_none_values() -> None:
    provider = _provider()

    descriptor = provider._map_device(
        {
            "id": 123,
            "name": "router-no-platform",
            "primary_ip4": {"address": "192.0.2.10/32"},
            "platform": {"slug": None},
            "device_type": {"model": None},
        }
    )

    assert descriptor.platform is None
    assert descriptor.model is None


def test_netbox_supports_ipam_object_types() -> None:
    supported = {resource.value for resource in _provider().supported_resources}
    assert {"device", "site", "ip_prefix", "ip_address", "vlan"} <= supported


@pytest.mark.asyncio
async def test_netbox_list_objects_maps_ip_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 1,
                        "prefix": "10.0.0.0/24",
                        "status": {"value": "active"},
                        "vlan": {"vid": 10},
                        "role": {"slug": "lan"},
                        "site": {"slug": "ams01"},
                        "is_pool": False,
                        "description": "core",
                    },
                    {
                        "id": 2,
                        "prefix": "10.0.1.0/24",
                        "status": {"value": "reserved"},
                        "vlan": None,
                        "role": None,
                        "site": None,
                        "is_pool": True,
                        "description": "",
                    },
                ],
                "next": None,
            },
        )

    provider = _provider(token="netbox-token")
    _install_transport(monkeypatch, httpx.MockTransport(handler))

    objects = await provider.list_objects(
        "ip_prefix",
        context=ProviderCallContext(
            provider_id="netbox:primary",
            operation="list_objects:ip_prefix",
            query_hash="",
            config_version=1,
        ),
    )

    assert captured_paths == ["/api/ipam/prefixes/"]
    assert [o.object_type for o in objects] == ["ip_prefix", "ip_prefix"]
    assert [o.external_id for o in objects] == ["1", "2"]
    assert [o.name for o in objects] == ["10.0.0.0/24", "10.0.1.0/24"]
    assert objects[0].attributes == {
        "prefix": "10.0.0.0/24",
        "status": "active",
        "vlan": 10,
        "role": "lan",
        "site": "ams01",
        "tenant": None,
        "is_pool": False,
        "description": "core",
    }
    # Absent nested values map to None rather than raising or being stringified.
    assert objects[1].attributes["vlan"] is None
    assert objects[1].attributes["site"] is None


@pytest.mark.asyncio
async def test_netbox_list_objects_maps_vlans(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ipam/vlans/"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 7,
                        "vid": 100,
                        "name": "prod-web",
                        "status": {"value": "active"},
                        "site": {"slug": "ams01"},
                        "group": {"name": "campus"},
                        "role": {"slug": "server"},
                        "description": "web tier",
                    }
                ],
                "next": None,
            },
        )

    provider = _provider(token="netbox-token")
    _install_transport(monkeypatch, httpx.MockTransport(handler))

    objects = await provider.list_objects(
        "vlan",
        context=ProviderCallContext(
            provider_id="netbox:primary",
            operation="list_objects:vlan",
            query_hash="",
            config_version=1,
        ),
    )

    assert len(objects) == 1
    vlan = objects[0]
    assert (vlan.object_type, vlan.external_id, vlan.name) == ("vlan", "7", "prod-web")
    assert vlan.attributes == {
        "vid": 100,
        "name": "prod-web",
        "status": "active",
        "site": "ams01",
        "group": "campus",
        "role": "server",
        "tenant": None,
        "description": "web tier",
    }
