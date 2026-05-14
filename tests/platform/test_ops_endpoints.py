"""INV-OPS-001: standard liveness/readiness probes must respond.

Reverse proxies (nginx, Traefik), Kubernetes liveness/readiness
checks обращаются к стандартным путям `/healthz`, `/readyz`. Backend
сейчас отвечает на оба + аутентичный `/api/health` остаётся.

Was xfail until upstream commit `77bc643` ("fix(ops/auth): /healthz
/readyz aliases"). Now plain regression-trail.

`/health` (без `z`) намеренно не aliased — kubernetes/traefik convention
именно `/healthz`, `/health` slot оставляем за продуктовыми endpoints.
"""

from __future__ import annotations

import httpx
import pytest

from tests.timeouts import TIMEOUTS


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_standard_probe_paths_return_200(base_url: str, path: str):
    """k8s/reverse-proxy liveness probes — 200 OK."""
    r = httpx.get(f"{base_url}{path}", timeout=TIMEOUTS.api_short)
    assert r.status_code == 200, (
        f"{path} returned {r.status_code} — k8s/reverse-proxy probe "
        f"will fail. Body: {r.text[:200]}"
    )
