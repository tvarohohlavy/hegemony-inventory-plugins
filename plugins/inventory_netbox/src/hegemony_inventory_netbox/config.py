# SPDX-FileCopyrightText: 2025-2026 Jakub Trávník <jakub.travnik@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""NetBox inventory provider config schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

DEFAULT_CUSTOM_FIELD_MAP = {
    "ssh.username_ref": "hegemony_ssh_username_ref",
    "ssh.password_ref": "hegemony_ssh_password_ref",
    "enable.password_ref": "hegemony_enable_password_ref",
    "ssh.private_key_ref": "hegemony_ssh_private_key_ref",
}


class NetBoxProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    token_ref: str = Field(
        ...,
        description=(
            "Reference to a stored secret holding the NetBox API token, "
            "e.g. {{ secret('vault://netbox/token') }}."
        ),
        json_schema_extra={"x_secret_ref": True},
    )
    auth_scheme: str = Field(
        "Bearer",
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]*$",
        description="Primary HTTP Authorization scheme prepended to resolved token values.",
    )
    auth_fallback_schemes: list[str] = Field(
        default_factory=lambda: ["Token"],
        max_length=4,
        description="Fallback Authorization schemes retried after auth failures when the token is unprefixed.",
    )
    verify_tls: bool = True
    custom_field_map: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_CUSTOM_FIELD_MAP))
    default_access_config: dict[str, Any] = Field(default_factory=dict)
    query_cache_ttl_seconds: int | None = Field(None, ge=0, le=86400)
    timeout_seconds: float = Field(10.0, gt=0, le=120)

    @field_validator("token_ref")
    @classmethod
    def token_ref_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("token_ref is required")
        return value.strip()

    @field_validator("auth_scheme", mode="before")
    @classmethod
    def auth_scheme_required(cls, value: Any) -> str:
        if value is None:
            return "Bearer"
        stripped = str(value).strip()
        if not stripped:
            raise ValueError("auth_scheme is required")
        return stripped

    @field_validator("auth_fallback_schemes", mode="before")
    @classmethod
    def normalize_auth_fallback_schemes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            candidates = [item.strip() for item in value.split(",")]
        elif isinstance(value, list):
            candidates = [str(item).strip() for item in value]
        else:
            raise ValueError("auth_fallback_schemes must be a list or comma-separated string")
        return [item for item in candidates if item]

    def safe_config(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
