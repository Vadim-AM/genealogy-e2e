"""Hardcoded suite constants — credentials, tokens, email patterns.

`tests/messages.py::TestData` хранит UI-strings (для assertions/locators).
Этот файл — test-infrastructure: пароли, токены, email domain, etc.
"""

from __future__ import annotations

import uuid


class TestConfig:
    """Single source of truth for suite-wide hardcoded values."""

    # ── Credentials ──────────────────────────────────────────────
    DEFAULT_PASSWORD = "test_password_8plus"
    ADMIN_PASSWORD = "test_admin_password"

    # ── Test infra ───────────────────────────────────────────────
    # Shared secret для `/api/_test/*` endpoints (X-Test-Token header).
    # Backend at boot должен иметь GENEALOGY_TEST_TOKEN с тем же значением.
    TEST_TOKEN_DEFAULT = "e2e-test-token-default-2026"

    # ── Email ────────────────────────────────────────────────────
    # `*.example.com` — RFC 2606 reserved для тестов, никогда не route'ится.
    EMAIL_DOMAIN = "e2e.example.com"

    DEFAULT_OWNER_EMAIL = f"owner@{EMAIL_DOMAIN}"
    SUPERADMIN_EMAIL = f"super@{EMAIL_DOMAIN}"


def make_email(label: str) -> str:
    """Build a deterministic test email like `<label>@e2e.example.com`."""
    return f"{label}@{TestConfig.EMAIL_DOMAIN}"


def unique_email(label: str) -> str:
    """Build a unique-per-call test email like `<label>-abc12345@…`.

    Use when a test seeds data that backend doesn't reset between
    runs (e.g. `WaitlistSubscriber` lives in legacy genealogy.db,
    not platform.db, so `_test/reset` doesn't wipe it).
    """
    return f"{label}-{uuid.uuid4().hex[:8]}@{TestConfig.EMAIL_DOMAIN}"
