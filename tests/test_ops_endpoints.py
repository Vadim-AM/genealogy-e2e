"""INV-OPS-001: standard liveness/readiness probes must respond.

Reverse proxies (nginx, Traefik), Kubernetes liveness/readiness
checks, и health-monitoring сервисы (UptimeRobot, Pingdom, etc.)
обращаются к стандартным путям:

- `/healthz` — k8s convention для liveness
- `/readyz` — k8s convention для readiness
- `/health` — generic probe path

Backend сейчас реагирует только на `/api/health` (нестандартный
путь). Run security 28.04 night confirmed: `/healthz`, `/readyz`,
`/health` все 404. Это ломает нормальные deployment flows и
заставляет custom-настраивать каждый probe.

Fix: добавить liveness/readiness handlers на стандартных путях
(могут просто redirect или alias на `/api/health`).
"""

from __future__ import annotations

import httpx
import pytest

from tests.timeouts import TIMEOUTS


_STANDARD_PROBE_PATHS = ("/healthz", "/readyz", "/health")


@pytest.mark.xfail(
    reason="INV-OPS-001: standard liveness/readiness paths /healthz, "
           "/readyz, /health all 404 (Run security 28.04 night). "
           "Только /api/health 200 — reverse-proxy и k8s probes ломаются. "
           "Fix: добавить @app.get для каждого пути (alias на existing "
           "/api/health handler — 200 + минимальный JSON).",
    strict=False,
)
@pytest.mark.parametrize("path", _STANDARD_PROBE_PATHS)
def test_standard_probe_paths_return_200(base_url: str, path: str):
    """Liveness/readiness probes должны возвращать 200 на стандартных путях."""
    r = httpx.get(f"{base_url}{path}", timeout=TIMEOUTS.api_short)
    assert r.status_code == 200, (
        f"{path} returned {r.status_code} — k8s/reverse-proxy probe "
        f"will fail. Body: {r.text[:200]}"
    )
