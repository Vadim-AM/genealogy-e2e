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

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────────
# Markup smoke — структура секции рендерится
# ─────────────────────────────────────────────────────────────────────────


def test_dashboard_has_feature_flags_section(auth_context_factory, superadmin_user):
    """TC-N6: на /platform/dashboard есть секция Feature Flags."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    r = page.goto("/platform/dashboard")
    assert r is not None and r.status == 200

    # Дашборд может быть тяжёлым — ждём что секция вообще появилась
    section = page.locator("#feature_flags_section")
    expect(section).to_be_visible()


def test_feature_flags_has_five_groups(auth_context_factory, superadmin_user):
    """TC-N6: секция содержит 5 групп с заголовками."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    expect(page.locator("#feature_flags_section")).to_be_visible()

    groups = page.locator(".ff-group")
    assert groups.count() == 5, \
        f"Ожидали 5 групп Feature Flags, нашли {groups.count()}"

    expected_titles = {
        "Поиск / AI",
        "Регистрация",
        "Контент-фичи",
        "Обслуживание",  # Wave-9 локализовал "Maintenance" → RU
        "Безопасность / алерты",
    }
    found_titles = {h.inner_text().strip() for h in page.locator(".ff-group-title").all()}
    missing = expected_titles - found_titles
    assert not missing, \
        f"Не найдены группы: {missing}. Все: {found_titles}"


def test_feature_flags_have_tooltips(auth_context_factory, superadmin_user):
    """TC-N6: каждый флаг имеет ⓘ tooltip с описанием (атрибут title)."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    expect(page.locator("#feature_flags_section")).to_be_visible()

    helps = page.locator("#feature_flags_section .ff-help")
    assert helps.count() >= 8, \
        f"Ожидали ≥8 tooltip элементов (по числу флагов), нашли {helps.count()}"

    # У каждого ⓘ должен быть `title` (через который браузер показывает тултип)
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


def test_ai_search_toggle_visible(auth_context_factory, superadmin_user):
    """TC-N6: toggle #ff_enable_ai_search присутствует в группе AI."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    expect(page.locator("#feature_flags_section")).to_be_visible()

    toggle = page.locator("#ff_enable_ai_search")
    expect(toggle).to_be_visible()
    # checkbox имеет правильный data-flag атрибут (используется JS-слоем)
    assert toggle.get_attribute("data-flag") == "enable_ai_search"


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
    # Конфликтуем с conftest.py:_default_ai_search_on (который ставит True)
    # — set False специально для этого теста.
    httpx.post(
        f"{uvicorn_server}{API.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": False},
        timeout=TIMEOUTS.api_short,
    ).raise_for_status()

    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    expect(page.locator("#ff_enable_ai_search")).to_be_visible()
    page.wait_for_function(
        "document.getElementById('set_beta_cap') && "
        "parseInt(document.getElementById('set_beta_cap').value, 10) > 0",
        timeout=TIMEOUTS.pw_expect_ms,
    )

    is_checked = page.locator("#ff_enable_ai_search").is_checked()
    assert is_checked is False, (
        "При enable_ai_search=False в БД toggle должен быть UNCHECKED. "
        "Если checked — UI читает не из /api/platform/settings, либо "
        "loadSettings не отработал."
    )


def test_dirty_class_appears_on_toggle_change(auth_context_factory, superadmin_user):
    """TC-N6: при клике на toggle строка получает класс .dirty."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    expect(page.locator("#ff_enable_ai_search")).to_be_visible()

    # Дожидаемся завершения loadSettings() — иначе click может прилететь до
    # того, как JS подпишется на change. Маркер тот же, что и в тесте выше:
    # set_beta_cap получает значение из БД (>0) только после bootstrap.
    page.wait_for_function(
        "document.getElementById('set_beta_cap') && "
        "parseInt(document.getElementById('set_beta_cap').value, 10) > 0",
        timeout=TIMEOUTS.pw_expect_ms,
    )

    # Локатор должен использовать `contains` — на строке в .dirty состоянии
    # `class='ff-row dirty'`, exact match по ='ff-row' не сработает.
    row = page.locator(
        "#ff_enable_ai_search >> xpath=ancestor::div[contains(@class, 'ff-row')]"
    ).first

    # Свежий init — diff с сервером ещё нулевой, .dirty отсутствует.
    expect(row).not_to_have_class(re.compile(r"\bdirty\b"))

    page.locator("#ff_enable_ai_search").click()

    # После клика — auto-wait на появление .dirty.
    expect(row).to_have_class(re.compile(r"\bdirty\b"))


# ─────────────────────────────────────────────────────────────────────────
# PATCH endpoint — runtime изменение
# ─────────────────────────────────────────────────────────────────────────


def test_patch_settings_writes_to_platformsettings_db(superadmin_user, tenant_client):
    """TC-N6 + A8: PATCH /api/platform/settings меняет значение в БД
    (`PlatformSettings.enable_ai_search`).

    Round-trip: PATCH → GET той же сущности → значение совпадает.
    НЕ проверяет /api/config/features — там может быть env override
    (см. test_features_endpoint_returns_false_when_env_disabled в
    test_ai_disabled_flow.py — отдельный сценарий).
    """
    api = tenant_client(superadmin_user)

    r = api.get(API.PLATFORM_SETTINGS)
    r.raise_for_status()
    initial_db = r.json()["enable_ai_search"]

    new_value = not initial_db
    patch_r = api.patch(API.PLATFORM_SETTINGS, json={"enable_ai_search": new_value})
    assert patch_r.status_code == 200, \
        f"PATCH должен вернуть 200, получили {patch_r.status_code}: {patch_r.text[:200]}"

    r2 = api.get(API.PLATFORM_SETTINGS)
    r2.raise_for_status()
    actual_db = r2.json()["enable_ai_search"]
    assert actual_db == new_value, (
        f"БД не обновилась после PATCH: было {initial_db}, "
        f"PATCHили на {new_value}, получили {actual_db}"
    )

    # Откат — гарантируем чистоту state для последующих тестов
    api.patch(API.PLATFORM_SETTINGS, json={"enable_ai_search": initial_db}).raise_for_status()


def test_patch_settings_validates_llm_provider_enum(superadmin_user, tenant_client):
    """TC-A8: некорректное llm_provider (не из enum) должно вернуть 400 с
    detail, упоминающим один из канонических provider'ов."""
    api = tenant_client(superadmin_user)
    r = api.patch(API.PLATFORM_SETTINGS, json={"llm_provider": "openai"})
    assert r.status_code == 400, \
        f"Ожидали 400 для llm_provider='openai' (не в enum), получили {r.status_code}"
    body = r.text.lower()
    canonical_providers = {"anthropic", "yandex", "gigachat"}
    mentioned = {p for p in canonical_providers if p in body}
    assert mentioned, (
        f"Error message не упоминает ни одного из enum-значений "
        f"{canonical_providers}: {r.text}"
    )
