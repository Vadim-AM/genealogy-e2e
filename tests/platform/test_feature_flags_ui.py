"""Feature Flags UI — TC-N6, TC-A8 (Phase C rollout, май 2026).

Платформенный admin может переключать runtime feature flags через UI
без редеплоя. Изменения мгновенно применяются ко всем последующим
запросам, пишутся в SuperadminAuditEntry.

Покрываемые сценарии:
- /platform/dashboard содержит секцию `#feature_flags_section`
- 5 групп: AI/Search, Регистрация, Контент-фичи, Maintenance, Безопасность
- Каждый флаг имеет свой control с `data-flag` атрибутом и tooltip (.ff-help)
- Toggle меняет состояние строки на .dirty (визуальный indicator unsaved)
- Click «Применить» → PATCH /api/platform/settings → toast «Сохранено»
- /api/config/features сразу отражает новое значение (без рестарта)

Backend uri:
- GET /platform/dashboard (auth required, superadmin only)
- GET /api/platform/settings (auth required)
- PATCH /api/platform/settings (auth required, audit-logged)
- GET /api/config/features (public, без auth)
"""

from __future__ import annotations

import re

import allure
import httpx
from playwright.sync_api import expect

from tests._core.api_paths import API
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS

# ─────────────────────────────────────────────────────────────────────────
# Markup smoke — структура секции рендерится
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Флаги: секция Feature Flags видна на дашборде")
def test_dashboard_has_feature_flags_section(auth_context_factory, superadmin_user):
    """TC-N6: на /platform/dashboard есть секция Feature Flags."""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        r = page.goto("/platform/dashboard")
        assert r is not None and r.status == 200, (
            f"/platform/dashboard navigation failed: response={r and r.status}"
        )

    with step("проверка: секция Feature Flags видна"):
        section = page.locator("#feature_flags_section")
        expect(section).to_be_visible()


@allure.title("Флаги: секция содержит ровно 5 групп с заголовками")
def test_feature_flags_has_five_groups(auth_context_factory, superadmin_user):
    """TC-N6: секция содержит 5 групп с заголовками."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        expect(page.locator("#feature_flags_section")).to_be_visible()

    with step("проверка: ровно 5 групп с ожидаемыми заголовками"):
        groups = page.locator('[data-testid="ff-group"]')
        assert groups.count() == 5, \
            f"Ожидали 5 групп Feature Flags, нашли {groups.count()}"

        expected_titles = {
            "Поиск / AI",
            "Регистрация",
            "Контент-фичи",
            "Обслуживание",  # Wave-9 локализовал "Maintenance" → RU
            "Безопасность / алерты",
        }
        found_titles = {h.inner_text().strip() for h in page.locator('[data-testid="ff-group-title"]').all()}
        missing = expected_titles - found_titles
        assert not missing, \
            f"Не найдены группы: {missing}. Все: {found_titles}"


@allure.title("Флаги: каждый переключатель имеет tooltip с описанием")
def test_feature_flags_have_tooltips(auth_context_factory, superadmin_user):
    """TC-N6: каждый флаг имеет ⓘ tooltip с описанием (атрибут title)."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        expect(page.locator("#feature_flags_section")).to_be_visible()

    with step("проверка: минимум 8 tooltip-элементов с описаниями"):
        helps = page.locator('#feature_flags_section [data-testid="ff-help"]')
        assert helps.count() >= 8, \
            f"Ожидали ≥8 tooltip элементов (по числу флагов), нашли {helps.count()}"

        empty_tooltips = []
        for i in range(helps.count()):
            title = helps.nth(i).get_attribute("title") or ""
            if len(title.strip()) < 20:
                empty_tooltips.append(i)
        assert not empty_tooltips, \
            f"Tooltip'ы #{empty_tooltips} пустые или слишком короткие — нет описания"


# ─────────────────────────────────────────────────────────────────────────
# AI search toggle — главный флаг текущего релиза
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Флаги: toggle AI-поиска виден с атрибутом data-flag")
def test_ai_search_toggle_visible(auth_context_factory, superadmin_user):
    """TC-N6: toggle #ff_enable_ai_search присутствует в группе AI."""
    with step("подготовка: открываем дашборд и ждём секцию"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        expect(page.locator("#feature_flags_section")).to_be_visible()

    with step("проверка: toggle AI-поиска виден и имеет верный data-flag"):
        toggle = page.locator("#ff_enable_ai_search")
        expect(toggle).to_be_visible()
        assert toggle.get_attribute("data-flag") == "enable_ai_search", (
            f"toggle data-flag mismatch: expected 'enable_ai_search', "
            f"got {toggle.get_attribute('data-flag')!r}"
        )


@allure.title("Флаги: toggle AI-поиска отражает значение False из БД")
def test_ai_search_toggle_reflects_db_value_when_off(
    auth_context_factory, superadmin_user, uvicorn_server: str
):
    """TC-N6: UI toggle отражает значение PlatformSettings.enable_ai_search
    из БД (НЕ env-resolved is_ai_search_enabled()).

    Bета-режим: записываем False в БД (через test-only set-platform-setting,
    минуя superadmin step-up MFA — это допустимо в IS_TESTING). UI должен
    показать toggle UNCHECKED.

    Это намеренный design: суперадмин видит что записано в БД, и переключает
    именно DB-уровень. Env override (ENABLE_AI_SEARCH=1) — отдельный
    аварийный механизм видимый только в /api/config/features (для frontend).
    """
    with step("подготовка: устанавливаем enable_ai_search=False в БД"):
        httpx.post(
            f"{uvicorn_server}{API.TEST_SET_PLATFORM_SETTING}",
            json={"enable_ai_search": False},
            timeout=TIMEOUTS.api_short,
        ).raise_for_status()

    with step("действие: открываем дашборд и ждём загрузку настроек"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        expect(page.locator("#ff_enable_ai_search")).to_be_visible()
        # loadSettings() done-sentinel, CSP-safe. tenants.js:121 assigns
        # `set_beta_cap.value = s.beta_user_cap`; the input has no value
        # attribute so it reads "" until loadSettings hydrates it. Two reasons
        # the old `wait_for_function("…>0")` broke post-cutover: (1) the
        # platform dashboard now serves `script-src 'self'` with no
        # 'unsafe-eval', so Playwright's string-predicate eval is CSP-blocked;
        # (2) the PR-B7 seed default for beta_user_cap is 0 — a valid loaded
        # value, so `>0` never held anyway. A locator assertion runs at the
        # driver level (no page eval) and `not_to_have_value("")` is
        # value-agnostic: only "" means not-yet-hydrated.
        expect(page.locator("#set_beta_cap")).not_to_have_value("")

    with step("проверка: toggle AI-поиска не отмечен"):
        is_checked = page.locator("#ff_enable_ai_search").is_checked()
        assert is_checked is False, (
            "При enable_ai_search=False в БД toggle должен быть UNCHECKED. "
            "Если checked — UI читает не из /api/platform/settings, либо "
            "loadSettings не отработал."
        )


@allure.title("Флаги: клик по toggle добавляет класс .dirty на строку")
def test_dirty_class_appears_on_toggle_change(auth_context_factory, superadmin_user):
    """TC-N6: при клике на toggle строка получает класс .dirty."""
    with step("подготовка: открываем дашборд и ждём загрузку настроек"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        expect(page.locator("#ff_enable_ai_search")).to_be_visible()

        # Wait for loadSettings() so the click lands after the change-listener
        # is wired. CSP-safe locator assertion (not wait_for_function — the
        # dashboard's `script-src 'self'` blocks string-predicate eval); see
        # the matching note in test_ai_search_toggle_reflects_db_value_when_off.
        expect(page.locator("#set_beta_cap")).not_to_have_value("")

        # Локатор должен использовать `contains` — на строке в .dirty состоянии
        # `class='ff-row dirty'`, exact match по ='ff-row' не сработает.
        row = page.locator(
            "#ff_enable_ai_search >> xpath=ancestor::div[contains(@class, 'ff-row')]"
        ).first

    with step("проверка: до клика .dirty отсутствует"):
        expect(row).not_to_have_class(re.compile(r"\bdirty\b"))

    with step("действие: кликаем toggle AI-поиска"):
        page.locator("#ff_enable_ai_search").click()

    with step("проверка: после клика строка получает класс .dirty"):
        expect(row).to_have_class(re.compile(r"\bdirty\b"))


# ─────────────────────────────────────────────────────────────────────────
# PATCH endpoint — runtime изменение
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Флаги: PATCH настроек сохраняет значение в БД")
def test_patch_settings_writes_to_platformsettings_db(superadmin_user, tenant_client):
    """TC-N6 + A8: PATCH /api/platform/settings меняет значение в БД
    (`PlatformSettings.enable_ai_search`).

    Round-trip: PATCH → GET той же сущности → значение совпадает.
    НЕ проверяет /api/config/features — там может быть env override
    (см. test_features_endpoint_returns_false_when_env_disabled в
    test_ai_disabled_flow.py — отдельный сценарий).
    """
    with step("подготовка: читаем текущее значение enable_ai_search из БД"):
        api = tenant_client(superadmin_user)
        r = api.get(API.PLATFORM_SETTINGS)
        r.raise_for_status()
        initial_db = r.json()["enable_ai_search"]

    with step("действие: PATCH с инвертированным значением"):
        new_value = not initial_db
        patch_r = api.patch(API.PLATFORM_SETTINGS, json={"enable_ai_search": new_value})
        assert patch_r.status_code == 200, \
            f"PATCH должен вернуть 200, получили {patch_r.status_code}: {patch_r.text[:200]}"

    with step("проверка: GET возвращает новое значение"):
        r2 = api.get(API.PLATFORM_SETTINGS)
        r2.raise_for_status()
        actual_db = r2.json()["enable_ai_search"]
        assert actual_db == new_value, (
            f"БД не обновилась после PATCH: было {initial_db}, "
            f"PATCHили на {new_value}, получили {actual_db}"
        )

    with step("подготовка: откат значения для последующих тестов"):
        api.patch(API.PLATFORM_SETTINGS, json={"enable_ai_search": initial_db}).raise_for_status()


@allure.title("Флаги: некорректный llm_provider отклоняется с 400")
def test_patch_settings_validates_llm_provider_enum(superadmin_user, tenant_client):
    """TC-A8: некорректное llm_provider (не из enum) должно вернуть 400 с
    detail, упоминающим один из канонических provider'ов."""
    with step("действие: PATCH с невалидным llm_provider"):
        api = tenant_client(superadmin_user)
        r = api.patch(API.PLATFORM_SETTINGS, json={"llm_provider": "openai"})

    with step("проверка: 400 и упоминание канонических provider'ов"):
        assert r.status_code == 400, \
            f"Ожидали 400 для llm_provider='openai' (не в enum), получили {r.status_code}"
        body = r.text.lower()
        canonical_providers = {"anthropic", "yandex", "gigachat"}
        mentioned = {p for p in canonical_providers if p in body}
        assert mentioned, (
            f"Error message не упоминает ни одного из enum-значений "
            f"{canonical_providers}: {r.text}"
        )
