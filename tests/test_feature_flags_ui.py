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

import httpx
import pytest
from playwright.sync_api import Page, expect


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
    expect(section).to_be_visible(timeout=10_000)


def test_feature_flags_has_five_groups(auth_context_factory, superadmin_user):
    """TC-N6: секция содержит 5 групп с заголовками."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_selector("#feature_flags_section", timeout=10_000)

    groups = page.locator(".ff-group")
    assert groups.count() == 5, \
        f"Ожидали 5 групп Feature Flags, нашли {groups.count()}"

    expected_titles = {
        "Поиск / AI",
        "Регистрация",
        "Контент-фичи",
        "Maintenance",
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
    page.wait_for_selector("#feature_flags_section", timeout=10_000)

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
    page.wait_for_selector("#feature_flags_section", timeout=10_000)

    toggle = page.locator("#ff_enable_ai_search")
    expect(toggle).to_be_visible()
    # checkbox имеет правильный data-flag атрибут (используется JS-слоем)
    assert toggle.get_attribute("data-flag") == "enable_ai_search"


def test_ai_search_toggle_initially_unchecked_after_seed(
    auth_context_factory, superadmin_user
):
    """TC-N6: после фрешного seed PlatformSettings (миграция
    `r6s7t8u9v0w1` ставит enable_ai_search=False по умолчанию) UI
    отображает toggle снятым.

    NB: UI показывает значение из БД (через `GET /api/platform/settings`),
    а НЕ env-resolved is_ai_search_enabled(). Это намеренно — чтобы
    суперадмин видел что записано в БД, и переключал именно DB-уровень.
    Env override (ENABLE_AI_SEARCH=1) — отдельный аварийный механизм
    видимый только в /api/config/features (для frontend).
    """
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_selector("#ff_enable_ai_search", timeout=10_000)
    # Async loadSettings() — ждём пока fetch /api/platform/settings завершится
    # и checkbox получит реальное значение (а не пустое default).
    # Маркер готовности — наличие данных в любом другом известном поле,
    # например settings.beta_user_cap > 0 (default seed = 30).
    page.wait_for_function(
        "document.getElementById('set_beta_cap') && "
        "parseInt(document.getElementById('set_beta_cap').value, 10) > 0",
        timeout=5_000,
    )

    # Теперь действительно проверяем — не должен быть checked
    is_checked = page.locator("#ff_enable_ai_search").is_checked()
    assert is_checked is False, (
        "После fresh seed (миграция r6s7t8u9v0w1, default enable_ai_search=False) "
        "toggle должен быть UNCHECKED. Если checked — значит дефолт "
        "сменился без отражения в фикстуре, либо сидер сломан."
    )


def test_dirty_class_appears_on_toggle_change(auth_context_factory, superadmin_user):
    """TC-N6: при клике на toggle строка получает класс .dirty."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    page = ctx.new_page()
    page.goto("/platform/dashboard")
    page.wait_for_selector("#ff_enable_ai_search", timeout=10_000)

    # Подождём пока loadSettings() инициализирует флаги
    page.wait_for_timeout(500)  # чуть-чуть на промис

    # Локатор должен использовать `contains` — на строке в .dirty состоянии
    # `class='ff-row dirty'`, exact match по ='ff-row' не сработает.
    row = page.locator(
        "#ff_enable_ai_search >> xpath=ancestor::div[contains(@class, 'ff-row')]"
    ).first
    has_dirty_before = "dirty" in (row.get_attribute("class") or "")

    # Клик
    page.locator("#ff_enable_ai_search").click()

    # После клика — должна быть .dirty (если toggle реально изменил состояние)
    page.wait_for_timeout(300)
    has_dirty_after = "dirty" in (row.get_attribute("class") or "")
    assert has_dirty_after != has_dirty_before, \
        "Класс .dirty не появился после клика на toggle — dirty-detection сломан"


# ─────────────────────────────────────────────────────────────────────────
# PATCH endpoint — runtime изменение
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.skip(
    reason="BUG-012: superadmin_user fixture использует фиксированный email, "
    "несколько подряд signup → 429. /api/_test/reset-signup-rate не сбрасывает "
    "per-email anti-bombing rate-limit. Нужен helper /api/_test/reset-email-rate "
    "либо пере-структурировать superadmin фикстуру как session-scoped с DB-cleanup."
)
def test_patch_settings_writes_to_platformsettings_db(
    superadmin_user, uvicorn_server: str
):
    """TC-N6 + A8: PATCH /api/platform/settings меняет значение в БД
    (`PlatformSettings.enable_ai_search`).

    Round-trip: PATCH → GET той же сущности → значение совпадает.
    НЕ проверяет /api/config/features — там может быть env override
    (см. test_features_endpoint_returns_false_when_env_disabled в
    test_ai_disabled_flow.py — отдельный сценарий).
    """
    cookies = httpx.Cookies()
    for name, value in superadmin_user.cookies.items():
        cookies.set(name, value)

    with httpx.Client(base_url=uvicorn_server, cookies=cookies, timeout=10) as c:
        # Текущее значение в БД (через admin API, НЕ через /api/config/features)
        r = c.get("/api/platform/settings")
        r.raise_for_status()
        initial_db = r.json()["enable_ai_search"]

        # Меняем
        new_value = not initial_db
        patch_r = c.patch("/api/platform/settings", json={"enable_ai_search": new_value})
        assert patch_r.status_code == 200, \
            f"PATCH должен вернуть 200, получили {patch_r.status_code}: {patch_r.text[:200]}"

        # Reread тот же endpoint — БД-значение должно поменяться
        r2 = c.get("/api/platform/settings")
        r2.raise_for_status()
        actual_db = r2.json()["enable_ai_search"]
        assert actual_db == new_value, (
            f"БД не обновилась после PATCH: было {initial_db}, "
            f"PATCHили на {new_value}, получили {actual_db}"
        )

        # Откат — гарантируем чистоту state для последующих тестов
        c.patch("/api/platform/settings", json={"enable_ai_search": initial_db}).raise_for_status()


@pytest.mark.skip(
    reason="BUG-012: см. test_patch_settings_changes_features_endpoint выше"
)
def test_patch_settings_validates_llm_provider_enum(
    superadmin_user, uvicorn_server: str
):
    """TC-A8: некорректное llm_provider (не из enum) должно вернуть 400."""
    cookies = httpx.Cookies()
    for name, value in superadmin_user.cookies.items():
        cookies.set(name, value)

    with httpx.Client(base_url=uvicorn_server, cookies=cookies, timeout=10) as c:
        r = c.patch("/api/platform/settings", json={"llm_provider": "openai"})
        assert r.status_code == 400, \
            f"Ожидали 400 для llm_provider='openai' (не в enum), получили {r.status_code}"
        # Сообщение об ошибке должно упоминать ожидаемые значения
        body = r.text.lower()
        assert "anthropic" in body or "yandex" in body or "gigachat" in body, \
            f"Error message не упоминает enum-значения: {r.text}"
