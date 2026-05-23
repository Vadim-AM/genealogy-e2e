"""Validated environment configuration — single source of truth.

All suite-wide env vars resolve through this module. Pydantic validates
at import time: typos, missing values, wrong types produce a clear
error instead of a silent runtime surprise.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="E2E_")

    backend_url: str = Field(
        description="URL of the test-instrumented backend (GENEALOGY_TESTING=1)",
    )
    test_token: str = Field(
        default="e2e-test-token-default-2026",
        description="Shared secret for /api/_test/* endpoints (X-Test-Token header)",
    )
    timeout_multiplier: float = Field(
        default=1.0,
        gt=0,
        description="Scale factor for all timeouts (>1 for slow CI)",
    )
    locale: Literal["ru", "en"] = Field(
        default="ru",
        description="UI locale for the messages catalogue",
    )


settings = Settings()
