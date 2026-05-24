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

from tests._core import api_paths as routes
from tests._core.err_msg import ErrMsg
from tests._core.messages import Enrichment, t
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS
from tests.pages.tree_page import TreePage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@pytest.fixture(autouse=True)
def ai_search_disabled(uvicorn_server: str):
    """Force `enable_ai_search=False` в БД перед каждым тестом этого
    файла. После теста — следующий autouse `reset_state` чистит state.

    `X-Test-Token` инжектируется автоматически через httpx monkey-patch
    в `tests/_fixtures/patch.py`.
    """
    httpx.post(
        f"{uvicorn_server}{routes.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": False},
        timeout=TIMEOUTS.api_short,
    ).raise_for_status()
    yield


# ─────────────────────────────────────────────────────────────────────────
# UI: TC-N5 — disabled button + no network leak
# ─────────────────────────────────────────────────────────────────────────


@allure.title("AI выключен: кнопка обогащения disabled с подсказкой «скоро»")
def test_owner_opens_profile_and_ai_button_is_disabled_with_tooltip(
    owner_page: Page, owner_user, pages: PageFactory,
):
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
    with step("подготовка: открыть профиль demo-self и подписаться на POST /api/enrich/"):
        page = owner_page
        enrich_post_calls: list[str] = []
        page.on(
            "request",
            lambda req: enrich_post_calls.append(req.url)
            if req.method == "POST" and routes.ENRICH_PREFIX in req.url
            else None,
        )

        _ = pages.navigate_to(TreePage)

        # User clicks по центральной orbit-card → opens demo-self profile.
        center = page.locator('[data-testid="orbit-center-card"]')
        expect(center, ErrMsg.orbit_card_not_visible).to_be_visible()
        center.click()
        profile = page.locator('[data-testid="profile-page"]')
        expect(profile, ErrMsg.profile_not_visible).to_be_visible()

    with step("проверка: disabled-кнопка с маркером 'скоро' и tooltip"):
        # 1. Disabled-кнопка с маркером «скоро».
        skoro_btn = profile.locator(f'button:has-text("{t(Enrichment.COMING_SOON)}")')
        expect(skoro_btn, ErrMsg.wrong_count).to_have_count(1)
        expect(skoro_btn.first, ErrMsg.ai_button_should_be_disabled).to_be_disabled()

        # 2. Tooltip — substring (locale-aware, без full-string fit).
        title = skoro_btn.first.get_attribute("title") or ""
        assert t(Enrichment.BETA_KEYWORD) in title, (
            f"title attribute should contain {t(Enrichment.BETA_KEYWORD)!r}, got {title!r}"
        )

        # 3. Активной enrich-кнопки нет.
        active_enrich = profile.locator('button[data-action="enrich"]:not([disabled])')
        expect(active_enrich, ErrMsg.wrong_count).to_have_count(0)

    with step("проверка: клик по disabled-кнопке не вызывает POST /api/enrich/"):
        # 4. Попытка клика по disabled-button. Native browser block'нет
        # click-event (disabled HTMLButtonElement не fires onclick). Pre-click
        # снимаем snapshot — если же что-то улетит после click, значит
        # disabled был обойдён JS-ом, что и есть регрессия.
        posts_before_click = list(enrich_post_calls)
        skoro_btn.first.click(force=True)
        page.wait_for_load_state("networkidle")
        new_posts = [u for u in enrich_post_calls if u not in posts_before_click]
        assert not new_posts, (
            f"disabled AI button triggered POST /api/enrich/* after click: {new_posts!r}"
        )


# ─────────────────────────────────────────────────────────────────────────
# API: backend invariants (no UI surface)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("AI выключен: /api/config/features возвращает ai_search_enabled=false")
def test_features_endpoint_public_returns_ai_disabled_flag(uvicorn_server: str):
    """TC-N3: /api/config/features public (no auth) и при ENABLE_AI_SEARCH=0
    возвращает `ai_search_enabled=false`. Frontend читает это на bootstrap.

    Combined assertion — public access + value — два аспекта одного
    contract'а, и оба регрессионно важны (auth-gate потерян = leak;
    flag перевернулся = UI кнопку случайно разблокировали).
    """
    with step("действие: запрос /api/config/features"):
        r = httpx.get(
            f"{uvicorn_server}{routes.CONFIG_FEATURES}", timeout=TIMEOUTS.api_request
        )

    with step("проверка: public доступ и ai_search_enabled=false"):
        assert r.status_code == HTTPStatus.OK, (
            f"endpoint должен быть public, получили {r.status_code}"
        )
        body = r.json()
        assert body.get("ai_search_enabled") is False, (
            f"при ENABLE_AI_SEARCH=0 ожидали false, получили {body!r}"
        )


@pytest.mark.parametrize(
    "method,path",
    [
        # Реально зарегистрированные endpoints в `enrichment/router.py`.
        # Каждый должен ровно 503 — router-guard срабатывает раньше всех
        # остальных зависимостей. Нет UI surface для каждого endpoint —
        # API-инвентаризация остаётся как backend contract.
        ("POST", "/api/enrich/p_test_id"),                         # noqa: drift
        ("GET",  "/api/enrich/p_test_id"),                         # noqa: drift
        ("GET",  "/api/enrich/p_test_id/history"),                 # noqa: drift
        ("GET",  "/api/enrich/p_test_id/acceptances"),             # noqa: drift
        ("POST", "/api/enrich/p_test_id/feedback"),                # noqa: drift
        ("POST", "/api/enrich/p_test_id/accept"),                  # noqa: drift
        ("POST", "/api/enrich/letters/sent"),                      # noqa: drift
        ("GET",  "/api/enrich/jobs"),                              # noqa: drift
        ("GET",  "/api/enrich/jobs/some_job_id"),                  # noqa: drift
        ("GET",  "/api/enrich/cache/some_cache_id"),               # noqa: drift
        ("POST", "/api/enrich/acceptances/some_id/revert"),        # noqa: drift
        ("GET",  "/api/enrich/health/api-key"),                    # noqa: drift
    ],
)
@allure.title("AI выключен: все /api/enrich/* эндпоинты возвращают 503")
def test_enrich_endpoint_returns_503_when_ai_disabled(
    uvicorn_server: str, method: str, path: str
):
    """TC-N4: каждый зарегистрированный /api/enrich/* endpoint при
    ENABLE_AI_SEARCH=0 → 503 (router-level Depends). 404 = route потерян,
    401/403 = auth-проверка обогнала router-guard, 200/500 = AI-кодпуть
    выполнился.
    """
    r = httpx.request(method, f"{uvicorn_server}{path}", json={}, timeout=TIMEOUTS.api_request)
    assert r.status_code == HTTPStatus.SERVICE_UNAVAILABLE, (
        f"{method} {path}: ожидали 503, получили {r.status_code}. "
        f"Detail: {r.text[:200]}"
    )


@allure.title("AI выключен: главная страница запрашивает /api/config/features")
def test_features_endpoint_fires_on_main_page_bootstrap(page: Page, base_url: str, anon_pages: PageFactory):
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
