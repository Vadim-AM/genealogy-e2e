"""Typed wrappers for MFA API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests._core import api_paths as routes
from tests._core.response import expect_response
from tests._models.mfa import (
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyResponse,
    RecoveryCodesResponse,
    RecoveryCountResponse,
)

if TYPE_CHECKING:
    import httpx


def setup_mfa(api: httpx.Client) -> MfaSetupResponse:
    """POST /api/platform/mfa/setup → validated MfaSetupResponse."""
    r = api.post(routes.MFA_SETUP)
    return expect_response(r, label="MFA setup").status_ok().schema(MfaSetupResponse)


def verify_mfa(api: httpx.Client, code: str) -> MfaVerifyResponse:
    """POST /api/platform/mfa/verify → validated MfaVerifyResponse."""
    r = api.post(routes.MFA_VERIFY, json={"code": code})
    return expect_response(r, label="MFA verify").status_ok().schema(MfaVerifyResponse)


def get_mfa_status(api: httpx.Client) -> MfaStatusResponse:
    """GET /api/platform/mfa/status → validated MfaStatusResponse."""
    r = api.get(routes.MFA_STATUS)
    return expect_response(r, label="MFA status").status_ok().schema(MfaStatusResponse)


def regenerate_recovery_codes(api: httpx.Client) -> RecoveryCodesResponse:
    """POST /api/platform/mfa/recovery-codes/regenerate → RecoveryCodesResponse."""
    r = api.post(routes.MFA_RECOVERY_REGENERATE)
    return expect_response(r, label="recovery regenerate").status_ok().schema(RecoveryCodesResponse)


def get_recovery_count(api: httpx.Client) -> RecoveryCountResponse:
    """GET /api/platform/mfa/recovery-codes/count → RecoveryCountResponse."""
    r = api.get(routes.MFA_RECOVERY_COUNT)
    return expect_response(r, label="recovery count").status_ok().schema(RecoveryCountResponse)
