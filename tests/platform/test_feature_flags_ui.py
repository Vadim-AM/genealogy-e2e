"""Feature Flags UI — TC-N6, TC-A8 (Phase C rollout, май 2026)."""

from __future__ import annotations

import re
from http import HTTPStatus

import allure
import httpx
from playwright.sync_api import expect

from api import platform_api, routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg


@allure.title("Флаги: секция Feature Flags видна на дашборде")
def test_dashboard_has_feature_flags_section(auth_context_factory, superadmin_user) -> None:
    """TC-N6: на /platform/dashboard есть секция Feature Flags."""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        r = page.goto("/platform/dashboard")
        should.be_true(r is not None and r.status == HTTPStatus.OK, ErrMsg.platform_navigation_failed)

    with step("проверка: секция Feature Flags видна"):
        section = page.locator("#feature_flags_section")  # no semantic: layout container
        expect(section, ErrMsg.element_not_visible).to_be_visible()


@allure.title("Флаги: секция содержит ровно 5 групп с заголовками")
def test_feature_flags_has_five_groups(auth_context_factory, superadmin_user) -> None:
    """TC-N6: секция содержит 5 групп с заголовками."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        # no semantic: layout container
        expect(page.locator("#feature_flags_section"), ErrMsg.element_not_visible).to_be_visible()

    with step("проверка: ровно 5 групп с ожидаемыми заголовками"):
        # no semantic: data-testid element, no role
        groups = page.locator('[data-testid="ff-group"]')
        should.be_equal(groups.count(), 5, ErrMsg.ff_group_count_wrong)

        expected_titles = {
            "Поиск / AI",
            "Регистрация",
            "Контент-фичи",
            "Обслуживание",  # Wave-9 локализовал "Maintenance" → RU
            "Безопасность / алерты",
        }
        # no semantic: data-testid element, no role
        found_titles = {h.inner_text().strip() for h in page.locator('[data-testid="ff-group-title"]').all()}
        missing = expected_titles - found_titles
        should.be_empty(missing, ErrMsg.ff_group_missing)


@allure.title("Флаги: каждый переключатель имеет tooltip с описанием")
def test_feature_flags_have_tooltips(auth_context_factory, superadmin_user) -> None:
    """TC-N6: каждый флаг имеет ⓘ tooltip с описанием (атрибут title)."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        # no semantic: layout container
        expect(page.locator("#feature_flags_section"), ErrMsg.element_not_visible).to_be_visible()

    with step("проверка: минимум 8 tooltip-элементов с описаниями"):
        # no semantic: data-testid element, no role
        helps = page.locator('#feature_flags_section [data-testid="ff-help"]')
        should.greater_or_equal(helps.count(), 8, ErrMsg.ff_tooltip_empty)

        empty_tooltips = []
        for i in range(helps.count()):
            title = helps.nth(i).get_attribute("title") or ""
            if len(title.strip()) < 20:
                empty_tooltips.append(i)
        should.be_empty(empty_tooltips, ErrMsg.ff_tooltip_empty)


@allure.title("Флаги: toggle AI-поиска виден с атрибутом data-flag")
def test_ai_search_toggle_visible(auth_context_factory, superadmin_user) -> None:
    """TC-N6: toggle #ff_enable_ai_search присутствует в группе AI."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        # no semantic: layout container
        expect(page.locator("#feature_flags_section"), ErrMsg.element_not_visible).to_be_visible()

    with step("проверка: toggle AI-поиска виден и имеет верный data-flag"):
        # no semantic: form input without label
        toggle = page.locator("#ff_enable_ai_search")
        expect(toggle, ErrMsg.element_not_visible).to_be_visible()
        should.be_equal(toggle.get_attribute("data-flag"), "enable_ai_search", ErrMsg.ff_data_flag_wrong)


@allure.title("Флаги: toggle AI-поиска отражает значение False из БД")
def test_ai_search_toggle_reflects_db_value_when_off(
    auth_context_factory, superadmin_user, uvicorn_server: str
) -> None:
    """TC-N6: UI toggle отражает значение PlatformSettings.enable_ai_search."""
    with step("подготовка: устанавливаем enable_ai_search=False в БД"):
        httpx.post(
            f"{uvicorn_server}{routes.TEST_SET_PLATFORM_SETTING}",
            json={"enable_ai_search": False},
        ).raise_for_status()

    with step("действие: открываем дашборд и ждём загрузку настроек"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        # no semantic: form input without label
        expect(page.locator("#ff_enable_ai_search"), ErrMsg.element_not_visible).to_be_visible()
        # Сигнал завершения loadSettings(), CSP-безопасный. tenants.js:121
        # присваивает `set_beta_cap.value = s.beta_user_cap`; input не имеет
        # атрибута value, поэтому читает "" пока loadSettings не заполнит.
        # Две причины, почему старый `wait_for_function("…>0")` сломался
        # после перехода: (1) dashboard теперь отдаёт `script-src 'self'`
        # без 'unsafe-eval', Playwright'овский string-predicate eval
        # блокируется CSP; (2) seed-дефолт PR-B7 для beta_user_cap = 0 —
        # валидное загруженное значение, `>0` никогда не выполнялось.
        # Locator assertion работает на уровне драйвера (без page eval),
        # и `not_to_have_value("")` агностичен к значению: только ""
        # означает «ещё не загружено».
        # no semantic: form input without label
        expect(page.locator("#set_beta_cap"), ErrMsg.feature_flag_state_wrong).not_to_have_value("")

    with step("проверка: toggle AI-поиска не отмечен"):
        # no semantic: form input without label
        is_checked = page.locator("#ff_enable_ai_search").is_checked()
        should.be_false(is_checked, ErrMsg.ff_toggle_state_wrong)


@allure.title("Флаги: клик по toggle добавляет класс .dirty на строку")
def test_dirty_class_appears_on_toggle_change(auth_context_factory, superadmin_user) -> None:
    """TC-N6: при клике на toggle строка получает класс .dirty."""
    with step("подготовка: открываем дашборд и ждём загрузку настроек"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        # no semantic: form input without label
        expect(page.locator("#ff_enable_ai_search"), ErrMsg.element_not_visible).to_be_visible()

        # Ждём loadSettings(), чтобы клик произошёл после привязки
        # change-listener. CSP-безопасный locator assertion (не
        # wait_for_function — `script-src 'self'` на dashboard блокирует
        # string-predicate eval); см. аналогичный комментарий в
        # test_ai_search_toggle_reflects_db_value_when_off.
        # no semantic: form input without label
        expect(page.locator("#set_beta_cap"), ErrMsg.feature_flag_state_wrong).not_to_have_value("")

        # Локатор должен использовать `contains` — на строке в .dirty состоянии
        # `class='ff-row dirty'`, exact match по ='ff-row' не сработает.
        row = page.locator(
            "#ff_enable_ai_search >> xpath=ancestor::div[contains(@class, 'ff-row')]"
        ).first

    with step("проверка: до клика .dirty отсутствует"):
        expect(row, ErrMsg.feature_flag_state_wrong).not_to_have_class(re.compile(r"\bdirty\b"))

    with step("действие: кликаем toggle AI-поиска"):
        page.locator("#ff_enable_ai_search").click()  # no semantic: form input without label

    with step("проверка: после клика строка получает класс .dirty"):
        expect(row, ErrMsg.feature_flag_state_wrong).to_have_class(re.compile(r"\bdirty\b"))


@allure.title("Флаги: PATCH настроек сохраняет значение в БД")
def test_patch_settings_writes_to_platformsettings_db(superadmin_user, tenant_client) -> None:
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
def test_patch_settings_validates_llm_provider_enum(superadmin_user, tenant_client) -> None:
    """TC-A8: некорректное llm_provider (не из enum) должно вернуть 400 с."""
    with step("действие: PATCH с невалидным llm_provider"):
        api = tenant_client(superadmin_user)
        r = api.patch(routes.PLATFORM_SETTINGS, json={"llm_provider": "openai"})

    with step("проверка: 400 и упоминание канонических provider'ов"):
        expect_response(
            r, label="llm_provider='openai' (not in enum)",
        ).status(HTTPStatus.BAD_REQUEST)
        body = r.text.lower()
        canonical_providers = {"anthropic", "yandex", "gigachat"}
        mentioned = {p for p in canonical_providers if p in body}
        should.be_true(mentioned, ErrMsg.ff_provider_not_mentioned)
