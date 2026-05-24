"""AI search disabled flow — TC-N3, TC-N4, TC-N5."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
import pytest
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.tree_page import TreePage
from src.texts import Enrichment, ErrMsg, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@pytest.fixture(autouse=True)
def ai_search_disabled(uvicorn_server: str):
    """Выключает AI search перед каждым тестом файла."""
    httpx.post(
        f"{uvicorn_server}{routes.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": False},
    ).raise_for_status()
    yield


@allure.title("AI выключен: кнопка disabled с подсказкой «скоро», POST не улетает")
def test_owner_opens_profile_and_ai_button_is_disabled_with_tooltip(
    owner_page: Page, owner_user, pages: PageFactory, enrich_post_spy: list[str],
) -> None:
    """TC-N5: owner → tree → orbit-center → profile → AI-кнопка disabled."""
    with step("подготовка: открыть профиль demo-self"):
        tree = pages.navigate_to(TreePage)
        panel = tree.open_center_profile()

    with step("проверка: disabled-кнопка с маркером «скоро» и tooltip"):
        expect(panel.btn_enrich_disabled, ErrMsg.wrong_count).to_have_count(1)
        expect(
            panel.btn_enrich_disabled.first,
            ErrMsg.ai_button_should_be_disabled,
        ).to_be_disabled()

        should.contain(panel.enrich_disabled_tooltip, t(Enrichment.BETA_KEYWORD), ErrMsg.ai_tooltip_wrong)

        expect(panel.btn_enrich_active, ErrMsg.wrong_count).to_have_count(0)

    with step("проверка: клик по disabled-кнопке не вызывает POST enrich"):
        posts_before = len(enrich_post_spy)
        panel.btn_enrich_disabled.first.click(force=True)
        panel.wait_for_network_idle()
        should.be_equal(len(enrich_post_spy), posts_before, ErrMsg.enrich_post_leaked)


@allure.title("AI выключен: /api/config/features → ai_search_enabled=false")
def test_features_endpoint_public_returns_ai_disabled_flag(uvicorn_server: str) -> None:
    """TC-N3: public endpoint возвращает ai_search_enabled=false."""
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
@allure.title("AI выключен: /api/enrich/* → 503")
def test_enrich_endpoint_returns_503_when_ai_disabled(
    uvicorn_server: str, method: str, path: str,
) -> None:
    """TC-N4: каждый /api/enrich/* endpoint → 503 при ENABLE_AI_SEARCH=0."""
    r = httpx.request(method, f"{uvicorn_server}{path}", json={})
    expect_response(r, label=f"{method} {path}").status(HTTPStatus.SERVICE_UNAVAILABLE)


@allure.title("AI выключен: bootstrap загружает /api/config/features")
def test_features_endpoint_fires_on_main_page_bootstrap(
    page: Page, anon_pages: PageFactory,
) -> None:
    """TC-N3b: при загрузке / frontend дёргает /api/config/features."""
    with step("действие: загрузка / и ожидание /api/config/features"), \
         page.expect_response(f"**{routes.CONFIG_FEATURES}") as resp_ctx:
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: /api/config/features ответил 200"):
        should.playwright_status(resp_ctx.value, HTTPStatus.OK, ErrMsg.bootstrap_fetch_failed)
