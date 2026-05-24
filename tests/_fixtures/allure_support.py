"""Allure report metadata: writes environment.properties once per session."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests._core.settings import settings


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(tmp_path_factory: pytest.TempPathFactory) -> None:
    results_dir = Path("allure-results")
    results_dir.mkdir(exist_ok=True)
    props_path = results_dir / "environment.properties"

    if os.environ.get("PYTEST_XDIST_WORKER") is not None:
        from filelock import FileLock
        root = tmp_path_factory.getbasetemp().parent
        with FileLock(str(root / "allure_env.lock")):
            if props_path.exists():
                return
            _write_props(props_path)
    else:
        _write_props(props_path)


def _write_props(path: Path) -> None:
    lines = [
        f"Backend URL={settings.backend_url}",
        f"Timeout multiplier={settings.timeout_multiplier}",
        f"Locale={settings.locale}",
    ]
    path.write_text("\n".join(lines) + "\n")
