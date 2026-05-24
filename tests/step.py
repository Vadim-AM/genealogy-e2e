"""Step-level logging + Allure reporting for multi-step test flows.

Wraps logical phases of a test or fixture with structured log output
and ``allure.step()`` blocks — steps render as collapsible items in the
Allure report with pass/fail status and timing.

    with step("signup owner"):
        ...
    with step("verify email"):
        ...
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING

import allure

if TYPE_CHECKING:
    from collections.abc import Iterator

_log = logging.getLogger("e2e.step")


@contextmanager
def step(title: str) -> Iterator[None]:
    """Context manager that logs and reports a named test phase via Allure."""
    _log.info("STEP → %s", title)
    try:
        with allure.step(title):
            yield
    except Exception:
        _log.info("STEP ✗ %s", title)
        raise
    else:
        _log.info("STEP ✓ %s", title)
