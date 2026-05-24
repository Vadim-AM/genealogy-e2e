"""AI search disabled flow — TC-N3, TC-N4, TC-N5 (user-flow E2E).

В тестовом setup uvicorn стартует с `ENABLE_AI_SEARCH=0` env →
гарантированно AI выключен независимо от значения в БД.

UI часть (TC-N5) — главная пользовательская гарантия: на profile-странице
AI-кнопка disabled с маркером «скоро» и tooltip, и **не** улетает в
`/api/enrich/*` при попытке клика. UI ловит регрессии, которые
API-инспекция не видит:
- `disabled` снят, click sends request → compliance leak;
- aiSearchOn разрулен неправильно — обе кнопки рендерятся одновременно;
- tooltip потерян после copy-edit.

API часть (TC-N3, TC-N4) — backend invariant без UI surface: router-level
503 на 11 enrichment-endpoint'ах. UI отрисовывает только UI-кнопку, не
все endpoints — API-проверка обязательна как смежный контракт.

Источник истины: `app/config.py:is_ai_search_enabled()`.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
import pytest
from playwright.sync_api import Page, expect

from api import routes
from framework.response import expect_response
from framework.step import step
from pages.profile_panel import ProfilePanel
from pages.tree_page import TreePage
from src.texts import Enrichment, ErrMsg, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@pytest.fixture(autouse=True)
def ai_search_disabled(uvicorn_server: str):
    """Force `enable_ai_search=False` в БД перед каждым тестом этого
    файла. После теста — следующий autouse `reset_state` чистит state.

    `X-Test-Token` инжектируется автоматически через httpx monkey-patch
    в `fixtures/patch.py`.
    """
    httpx.post(
        f"{uvicorn_server}{routes.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": False},
    ).raise_for_status()
    yield


# ─────────────────────────────────────────────────────────────────────────
# UI: TC-N5 — disabled button + no network leak
# ─────────────────────────────────────────────────────────────────────────


@allure.title("AI выключен: кнопка обогащения disabled с подсказкой «скоро»")
def test_owner_opens_profile_and_ai_button_is_disabled_with_tooltip(
    owner_page: Page, owner_user, pages: PageFactory,
) -> None:
    """TC-N5: настоящий user journey — owner открывает / → клик по центру
    orbit → profile → AI-кнопка disabled c «скоро» и tooltip.

    Главная compliance-проверка: **POST `/api/enrich/{pid}` (запуск
    enrichment job)** не должен улететь при попытке клика по disabled.
    HTML `disabled` мог быть удалён, а click-handler — нет.

    Note: profile.js на open всё равно fires GET-ы на `/history` и
    `/acceptances` для existing данных — это **graceful degradation**
    (backend 503'ит, UI скрывает блок). Не путаем с POST на запуск нового
    enrichment, который — реальный compliance leak если случится.
    """
    with step("подготовка: подписаться на POST enrich и открыть профиль"):
        enrich_post_calls: list[str] = []
        owner_page.on(
            "request",
            lambda req: enrich_post_calls.append(req.url)
            if req.method == "POST" and routes.ENRICH_PREFIX in req.url
            else None,
        )
        tree = pages.navigate_to(TreePage)
        tree.open_center_profile()
        panel = ProfilePanel(owner_page)

    with step("проверка: disabled-кнопка с маркером «скоро» и tooltip"):
        expect(panel.btn_enrich_disabled, ErrMsg.wrong_count).to_have_count(1)
        expect(
            panel.btn_enrich_disabled.first,
            ErrMsg.ai_button_should_be_disabled,
        ).to_be_disabled()

        title = panel.btn_enrich_disabled.first.get_attribute("title") or ""
        assert t(Enrichment.BETA_KEYWORD) in title, (
            f"title должен содержать {t(Enrichment.BETA_KEYWORD)!r}, получили {title!r}"
        )

        expect(panel.btn_enrich_active, ErrMsg.wrong_count).to_have_count(0)

    with step("проверка: клик по disabled-кнопке не вызывает POST enrich"):
        posts_before = list(enrich_post_calls)
        panel.btn_enrich_disabled.first.click(force=True)
        owner_page.wait_for_load_state("networkidle")
        new_posts = [u for u in enrich_post_calls if u not in posts_before]
        assert not new_posts, (
            f"disabled AI кнопка вызвала POST /api/enrich/* после клика: {new_posts!r}"
        )


# ─────────────────────────────────────────────────────────────────────────
# API: backend invariants (no UI surface)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("AI выключен: /api/config/features возвращает ai_search_enabled=false")
def test_features_endpoint_public_returns_ai_disabled_flag(uvicorn_server: str) -> None:
    """TC-N3: /api/config/features public (no auth) и при ENABLE_AI_SEARCH=0
    возвращает `ai_search_enabled=false`. Frontend читает это на bootstrap.

    Combined assertion — public access + value — два аспекта одного
    contract'а, и оба регрессионно важны (auth-gate потерян = leak;
    flag перевернулся = UI кнопку случайно разблокировали).
    """
    with step("действие: запрос /api/config/features"):
        r = httpx.get(f"{uvicorn_server}{routes.CONFIG_FEATURES}")

    with step("проверка: public доступ и ai_search_enabled=false"):
        expect_response(r, label="config/features public").status(HTTPStatus.OK).json_eq(
            "ai_search_enabled", False,
        )


_TEST_PID = "p_test_id"
_TEST_JOB = "some_job_id"

_ENRICH_ENDPOINTS = [
    ("POST", routes.enrich(_TEST_PID)),
    ("GET",  routes.enrich(_TEST_PID)),
    ("GET",  routes.enrich_history(_TEST_PID)),
    ("GET",  routes.enrich_acceptances(_TEST_PID)),
    ("POST", routes.enrich_feedback(_TEST_PID)),
    ("POST", routes.enrich_accept(_TEST_PID)),
    ("POST", routes.ENRICH_LETTERS_SENT),
    ("GET",  routes.enrich_jobs(_TEST_JOB)),
    ("GET",  routes.enrich_cache(0)),
    ("POST", routes.enrich_revert(0)),
    ("GET",  routes.ENRICH_HEALTH_API_KEY),
]


@pytest.mark.parametrize("method,path", _ENRICH_ENDPOINTS)
@allure.title("AI выключен: все /api/enrich/* эндпоинты возвращают 503")
def test_enrich_endpoint_returns_503_when_ai_disabled(
    uvicorn_server: str, method: str, path: str,
) -> None:
    """TC-N4: каждый зарегистрированный /api/enrich/* endpoint при
    ENABLE_AI_SEARCH=0 → 503 (router-level Depends)."""
    r = httpx.request(method, f"{uvicorn_server}{path}", json={})
    expect_response(r, label=f"{method} {path}").status(HTTPStatus.SERVICE_UNAVAILABLE)


@allure.title("AI выключен: главная страница запрашивает /api/config/features")
def test_features_endpoint_fires_on_main_page_bootstrap(page: Page, anon_pages: PageFactory) -> None:
    """TC-N3: при загрузке `/` frontend дёргает /api/config/features
    (bootstrap `window.__features`). Без этого UI не знает про disabled
    state и default-рендерит active кнопки.
    """
    with step("действие: загрузка / и ожидание /api/config/features"), \
         page.expect_response(f"**{routes.CONFIG_FEATURES}") as resp_ctx:
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: /api/config/features ответил 200"):
        assert resp_ctx.value.ok, (
            f"bootstrap fetch /api/config/features failed: {resp_ctx.value.status}"
        )
