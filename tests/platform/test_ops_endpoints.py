"""INV-OPS-001: standard liveness/readiness probes must respond."""

from __future__ import annotations

from http import HTTPStatus

import allure
import httpx
import pytest

from framework.response import expect_response
from framework.step import step


@allure.title("Ops: стандартные k8s-пробы /healthz и /readyz отвечают 200")
@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_standard_probe_paths_return_200(base_url: str, path: str) -> None:
    """k8s/reverse-proxy liveness probes — 200 OK."""
    with step(f"действие: запросить {path}"):
        r = httpx.get(f"{base_url}{path}")

    with step(f"проверка: {path} отвечает 200"):
        expect_response(r, label=f"probe {path}").status(HTTPStatus.OK)
