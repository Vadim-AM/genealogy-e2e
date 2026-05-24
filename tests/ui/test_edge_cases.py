"""Edge cases per docs/test-plan.md TC-EDGE-001..005.

`test_minimap_hidden_on_mobile_viewport` removed during 28.04 sanitize:
the original used a runtime `pytest.xfail` that masked any regression.
Reinstate as `@pytest.mark.xfail(strict=False)` only after BUG status
is confirmed open.
"""

from __future__ import annotations

from http import HTTPStatus

import allure
import httpx
from playwright.sync_api import Page, expect

from tests._core import api_paths as routes
from tests._core.err_msg import ErrMsg
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS


@allure.title("Edge: переход по несуществующему профилю не ломает UI")
def test_f5_on_nonexistent_profile_id_does_not_crash(owner_page: Page):
    """TC-EDGE-004: F5 on /#/p/<unknown> shows tree, no JS crash."""
    owner_page.goto("/#/p/nonexistent_xyz_123")
    owner_page.wait_for_load_state("domcontentloaded")
    expect(owner_page.locator('[data-tab="tree"]'), ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Edge: персона с единственным полем name корректно читается")
def test_old_person_with_only_name_field_renders(owner_user, tenant_client):
    """TC-EDGE-001: a person record with only `name` (no surname/given) — accessible.

    If POST /api/people stops accepting the legacy single-name payload, that's
    a backwards-compatibility regression and the test must fail loud.
    """
    api = tenant_client(owner_user)

    with step("действие: создать персону с единственным полем name"):
        payload = {
            "id": "edge-old-name",
            "name": "Иванов Иван Петрович",
            "branch": "subject",
            "gender": "m",
        }
        r = api.post(routes.PEOPLE, json=payload)
        assert r.status_code in (HTTPStatus.OK, HTTPStatus.CREATED), \
            f"POST {routes.PEOPLE} legacy payload rejected: {r.status_code} {r.text[:200]}"

    with step("проверка: имя сохранилось при чтении"):
        r = api.get(routes.person("edge-old-name"))
        r.raise_for_status()
        name = r.json().get("name") or ""
        assert "Иван" in name, f"name not preserved: {name!r}"


@allure.title("Edge: /api/health доступен без авторизации и отдаёт ok")
def test_health_endpoint_does_not_require_auth(base_url: str):
    """Smoke: /api/health is public (no auth), reports status ok.

    Behaviour, not exact shape (Rule 13): post-PR-B7 the body also carries
    diagnostic keys (`dialect`, `active_tenants`). Pinning the whole dict
    made the test fail on an additive, non-functional change. The contract
    is: reachable without credentials + `status == "ok"`.
    """
    with step("действие: запросить /api/health без авторизации"):
        r = httpx.get(f"{base_url}{routes.HEALTH}", timeout=TIMEOUTS.api_request)
        r.raise_for_status()

    with step("проверка: статус ok"):
        assert r.json().get("status") == "ok", \
            f"unexpected /api/health status: {r.json()!r}"
