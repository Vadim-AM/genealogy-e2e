"""Step-level logging for multi-step test flows.

Wraps logical phases of a test or fixture with structured log output.
On failure, the log shows which step was reached before the crash.

    with step("signup owner"):
        ...
    with step("verify email"):
        ...
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

_log = logging.getLogger("e2e.step")


@contextmanager
def step(title: str) -> Iterator[None]:
    _log.info(">>> %s", title)
    try:
        yield
    except Exception:
        _log.error("!!! FAILED: %s", title, exc_info=True)
        raise
    else:
        _log.info("<<< %s", title)
