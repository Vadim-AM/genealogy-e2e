"""Pydantic models for MFA API contracts."""

from __future__ import annotations

from pydantic import BaseModel


class MfaSetupResponse(BaseModel, extra="allow"):
    """Response from POST /api/platform/mfa/setup."""

    secret: str
    otpauth_url: str
    issuer: str


class MfaVerifyResponse(BaseModel, extra="allow"):
    """Response from POST /api/platform/mfa/verify."""

    status: str
    valid_until: str | None = None


class MfaStatusResponse(BaseModel, extra="allow"):
    """Response from GET /api/platform/mfa/status."""

    configured: bool
    fresh: bool


class RecoveryCodesResponse(BaseModel, extra="allow"):
    """Response from POST /api/platform/mfa/recovery-codes/regenerate."""

    codes: list[str]


class RecoveryCountResponse(BaseModel, extra="allow"):
    """Response from GET /api/platform/mfa/recovery-codes/count."""

    unused: int
