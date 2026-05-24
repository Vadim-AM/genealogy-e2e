"""Pydantic models for auth API contracts."""

from __future__ import annotations

from pydantic import BaseModel


class SignupRequest(BaseModel):
    """Request body for POST /api/account/signup."""

    email: str
    password: str
    full_name: str
    terms_accepted: bool = True
    privacy_consent: bool = True
    cross_border_consent: bool = True


class LoginResponse(BaseModel, extra="allow"):
    """Response from POST /api/account/login."""

    tenant_slug: str


class VerifyEmailResponse(BaseModel, extra="allow"):
    """Response from POST /api/account/verify-email."""

    auto_login: bool | None = None
    tenant_slug: str | None = None


class TenantInfo(BaseModel, extra="allow"):
    """Nested tenant object in AccountMe."""

    slug: str


class AccountMe(BaseModel, extra="allow"):
    """Response from GET /api/account/me."""

    tenant: TenantInfo


class InviteResponse(BaseModel, extra="allow"):
    """Response from POST /api/account/tenant/invites."""

    token: str
    status: str | None = None


class EmailResponse(BaseModel, extra="allow"):
    """Response from GET /api/_test/last-email."""

    text_body: str | None = None
