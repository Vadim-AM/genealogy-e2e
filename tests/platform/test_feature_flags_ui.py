"""Feature Flags UI — TC-N6, TC-A8 (Phase C rollout, май 2026)."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
from playwright.sync_api import expect

from api import platform_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser
    from pages.feature_flags_page import FeatureFlagsPage


@allure.title("Флаги: секция Feature Flags видна на дашборде")
def test_dashboard_has_feature_flags_section(
    feature_flags: FeatureFlagsPage,
) -> None:
    """TC-N6: на /platform/dashboard есть секция Feature Flags."""
    with step("подготовка: открываем дашборд суперадмина"):
        ff = feature_flags
        r = ff.goto_with_response()
        should.be_equal(r.status, HTTPStatus.OK, ErrMsg.platform_navigation_failed)

    with step("проверка: секция Feature Flags видна"):
        ff.expect_section_visible()


@allure.title("Флаги: секция содержит ровно 5 групп с заголовками")
def test_feature_flags_has_five_groups(
    feature_flags: FeatureFlagsPage,
) -> None:
    """TC-N6: секция содержит 5 групп с заголовками."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ff = feature_flags
        ff.expect_section_visible()

    with step("проверка: ровно 5 групп с ожидаемыми заголовками"):
        should.be_equal(ff.groups.count(), 5, ErrMsg.ff_group_count_wrong)

        expected_titles = {
            "Поиск / AI",
            "Регистрация",
            "Контент-фичи",
            "Обслуживание",  # Wave-9 локализовал "Maintenance" → RU
            "Безопасность / алерты",
        }
        found_titles = ff.group_title_texts()
        missing = expected_titles - found_titles
        should.be_empty(missing, ErrMsg.ff_group_missing)


@allure.title("Флаги: каждый переключатель имеет tooltip с описанием")
def test_feature_flags_have_tooltips(
    feature_flags: FeatureFlagsPage,
) -> None:
    """TC-N6: каждый флаг имеет tooltip с описанием (атрибут title)."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ff = feature_flags
        ff.expect_section_visible()

    with step("проверка: минимум 8 tooltip-элементов с описаниями"):
        should.greater_or_equal(ff.help_icons.count(), 8, ErrMsg.ff_tooltip_empty)

        tooltips = ff.help_tooltip_texts()
        empty_tooltips = [i for i, text in enumerate(tooltips) if len(text) < 20]
        should.be_empty(empty_tooltips, ErrMsg.ff_tooltip_empty)


@allure.title("Флаги: toggle AI-поиска виден с атрибутом data-flag")
def test_ai_search_toggle_visible(
    feature_flags: FeatureFlagsPage,
) -> None:
    """TC-N6: toggle #ff_enable_ai_search присутствует в группе AI."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ff = feature_flags
        ff.expect_section_visible()

    with step("проверка: toggle AI-поиска виден и имеет верный data-flag"):
        expect(ff.ai_search_toggle, ErrMsg.element_not_visible).to_be_visible()
        should.be_equal(ff.ai_search_data_flag(), "enable_ai_search", ErrMsg.ff_data_flag_wrong)


@allure.title("Флаги: toggle AI-поиска отражает значение False из БД")
def test_ai_search_toggle_reflects_db_value_when_off(
    feature_flags: FeatureFlagsPage, uvicorn_server: str
) -> None:
    """TC-N6: UI toggle отражает значение PlatformSettings.enable_ai_search."""
    with step("подготовка: устанавливаем enable_ai_search=False в БД"):
        httpx.post(
            f"{uvicorn_server}{routes.TEST_SET_PLATFORM_SETTING}",
            json={"enable_ai_search": False},
        ).raise_for_status()

    with step("действие: открываем дашборд и ждём загрузку настроек"):
        ff = feature_flags
        expect(ff.ai_search_toggle, ErrMsg.element_not_visible).to_be_visible()
        ff.wait_for_settings_loaded()

    with step("проверка: toggle AI-поиска не отмечен"):
        should.be_false(ff.is_ai_search_checked(), ErrMsg.ff_toggle_state_wrong)


@allure.title("Флаги: клик по toggle добавляет класс .dirty на строку")
def test_dirty_class_appears_on_toggle_change(
    feature_flags: FeatureFlagsPage,
) -> None:
    """TC-N6: при клике на toggle строка получает класс .dirty."""
    with step("подготовка: открываем дашборд и ждём загрузку настроек"):
        ff = feature_flags
        expect(ff.ai_search_toggle, ErrMsg.element_not_visible).to_be_visible()
        ff.wait_for_settings_loaded()

        row = ff.ai_search_row()

    with step("проверка: до клика .dirty отсутствует"):
        expect(row, ErrMsg.feature_flag_state_wrong).not_to_have_class(re.compile(r"\bdirty\b"))

    with step("действие: кликаем toggle AI-поиска"):
        ff.click_ai_search_toggle()

    with step("проверка: после клика строка получает класс .dirty"):
        expect(row, ErrMsg.feature_flag_state_wrong).to_have_class(re.compile(r"\bdirty\b"))


@allure.title("Флаги: PATCH настроек сохраняет значение в БД")
def test_patch_settings_writes_to_platformsettings_db(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-N6 + A8: PATCH /api/platform/settings меняет значение в БД."""
    with step("подготовка: читаем текущее значение enable_ai_search из БД"):
        api = tenant_client(superadmin_user)
        initial = platform_api.get_platform_settings(api)
        initial_db = initial.enable_ai_search

    with step("действие: PATCH с инвертированным значением"):
        new_value = not initial_db
        patch_r = api.patch(routes.PLATFORM_SETTINGS, json={"enable_ai_search": new_value})
        expect_response(patch_r, label="PATCH platform settings").status_ok()

    with step("проверка: GET возвращает новое значение"):
        after = platform_api.get_platform_settings(api)
        should.be_equal(after.enable_ai_search, new_value, ErrMsg.ff_db_not_updated)

    with step("подготовка: откат значения для последующих тестов"):
        rollback = api.patch(routes.PLATFORM_SETTINGS, json={"enable_ai_search": initial_db})
        expect_response(rollback, label="rollback platform settings").status_ok()


@allure.title("Флаги: некорректный llm_provider отклоняется с 400")
def test_patch_settings_validates_llm_provider_enum(
    superadmin_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """TC-A8: некорректное llm_provider (не из enum) должно вернуть 400 с."""
    with step("действие: PATCH с невалидным llm_provider"):
        api = tenant_client(superadmin_user)
        r = api.patch(routes.PLATFORM_SETTINGS, json={"llm_provider": "openai"})

    with step("проверка: 400 и упоминание канонических provider'ов"):
        expect_response(
            r,
            label="llm_provider='openai' (not in enum)",
        ).status(HTTPStatus.BAD_REQUEST)
        body = r.text.lower()
        canonical_providers = {"anthropic", "yandex", "gigachat"}
        mentioned = {p for p in canonical_providers if p in body}
        should.be_true(mentioned, ErrMsg.ff_provider_not_mentioned)
