"""AI search disabled flow — TC-N3, TC-N4, TC-N7 (Phase B+C, май 2026).

Бета-режим работает с `ENABLE_AI_SEARCH=0` глобально:
- /api/enrich/* — 503 (router-level Depends в `enrichment/router.py`)
- /api/config/features — `{ai_search_enabled: false}`
- Owner UI кнопка «Найти больше» — disabled с текстом «(скоро)» и
  tooltip «Поиск откроется в публичной бете»

Источник истины — `app/config.py:is_ai_search_enabled()`:
1. ENV `ENABLE_AI_SEARCH` (если задан явно) — emergency override
2. PlatformSettings.enable_ai_search в БД
3. Default `True` для dev/CI

В тестовом setup uvicorn стартует с `ENABLE_AI_SEARCH=0` env →
гарантированно AI выключен независимо от значения в БД.
"""

from __future__ import annotations

import os

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API


_TEST_TOKEN = os.environ.get("E2E_TEST_TOKEN", "e2e-test-token-default-2026")


@pytest.fixture(autouse=True)
def ai_search_disabled(uvicorn_server: str):
    """Force `enable_ai_search=False` в БД перед каждым тестом этого
    файла (router-guard, owner UI кнопка disabled, etc. покрываются ТОЛЬКО
    при OFF).

    Использует `/api/_test/set-platform-setting` — test-only endpoint,
    дёрнуть в test mode без superadmin auth. После теста состояние не
    трогаем — следующий autouse `reset_state` из conftest полностью
    DELETE'нет таблицу и migration_seed восстановит дефолт (False).
    """
    httpx.post(
        f"{uvicorn_server}/api/_test/set-platform-setting",
        json={"enable_ai_search": False},
        headers={"X-Test-Token": _TEST_TOKEN},
        timeout=5,
    ).raise_for_status()
    yield


# ─────────────────────────────────────────────────────────────────────────
# /api/config/features — public endpoint
# ─────────────────────────────────────────────────────────────────────────


def test_features_endpoint_public_no_auth_required(uvicorn_server: str):
    """TC-N3: /api/config/features доступен без auth (frontend bootstrap)."""
    r = httpx.get(f"{uvicorn_server}/api/config/features", timeout=10)
    assert r.status_code == 200, \
        f"Endpoint должен быть public, получили {r.status_code}"
    body = r.json()
    assert "ai_search_enabled" in body, \
        f"Response должен содержать ai_search_enabled: {body}"


def test_features_endpoint_returns_false_when_env_disabled(uvicorn_server: str):
    """TC-N3: при `ENABLE_AI_SEARCH=0` env (test setup) → false."""
    body = httpx.get(f"{uvicorn_server}/api/config/features", timeout=10).json()
    assert body["ai_search_enabled"] is False, \
        f"При ENABLE_AI_SEARCH=0 ожидали false, получили {body['ai_search_enabled']}"


# ─────────────────────────────────────────────────────────────────────────
# /api/enrich/* — router-level guard (503)
# ─────────────────────────────────────────────────────────────────────────


def test_enrich_jobs_returns_503_when_ai_disabled(uvicorn_server: str):
    """TC-N4: GET /api/enrich/jobs → 503 при выключенном AI search.

    503 должен прийти ДО auth-проверки (router-level Depends срабатывает
    раньше per-endpoint dependencies). Если бы был сначала auth — был бы 401/403.
    """
    r = httpx.get(f"{uvicorn_server}/api/enrich/jobs", timeout=10)
    assert r.status_code == 503, \
        f"Ожидали 503, получили {r.status_code}: {r.text[:200]}"
    assert "AI search is temporarily disabled" in r.text or "ai" in r.text.lower(), \
        f"Detail должен упоминать причину: {r.text[:200]}"


@pytest.mark.parametrize(
    "method,path",
    [
        # Реально зарегистрированные endpoints в `enrichment/router.py`.
        # Каждый должен ровно 503 при ENABLE_AI_SEARCH=0 — иначе router-guard
        # не работает либо обходится для какого-то метода.
        ("POST", "/api/enrich/p_test_id"),                         # router.post("/{person_id}")
        ("GET",  "/api/enrich/p_test_id"),                         # router.get("/{person_id}")
        ("GET",  "/api/enrich/p_test_id/history"),                 # router.get("/{person_id}/history")
        ("GET",  "/api/enrich/p_test_id/acceptances"),             # router.get("/{person_id}/acceptances")
        ("POST", "/api/enrich/p_test_id/feedback"),                # router.post("/{person_id}/feedback")
        ("POST", "/api/enrich/p_test_id/accept"),                  # router.post("/{person_id}/accept")
        ("POST", "/api/enrich/letters/sent"),                      # router.post("/letters/sent")
        ("GET",  "/api/enrich/jobs/some_job_id"),                  # router.get("/jobs/{job_id}")
        ("GET",  "/api/enrich/cache/some_cache_id"),               # router.get("/cache/{enrichment_id}")
        ("POST", "/api/enrich/acceptances/some_id/revert"),        # router.post("/acceptances/{id}/revert")
        ("GET",  "/api/enrich/health/api-key"),                    # router.get("/health/api-key")
    ],
)
def test_enrich_endpoint_returns_503_when_ai_disabled(
    uvicorn_server: str, method: str, path: str
):
    """TC-N4: каждый зарегистрированный /api/enrich/* endpoint при
    ENABLE_AI_SEARCH=0 должен возвращать **ровно 503** — router-level
    Depends(_require_ai_search_enabled) срабатывает раньше всех остальных
    зависимостей (auth, quota, etc.).

    Если endpoint вернул 404 — значит route не зарегистрирован
    (regression в backend).
    Если 401/403 — значит auth-проверка обогнала router-guard
    (он привязан к endpoint, а не к router-level → ошибка реализации).
    Если 200/500 — AI-кодпуть выполнился, что критическое нарушение.
    """
    r = httpx.request(method, f"{uvicorn_server}{path}", json={}, timeout=10)
    assert r.status_code == 503, (
        f"{method} {path}: ожидали 503 (router-guard), получили {r.status_code}. "
        f"Detail: {r.text[:200]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Owner UI — кнопка «Найти больше» в disabled state
# ─────────────────────────────────────────────────────────────────────────


def test_owner_profile_ai_button_is_disabled_with_skoro_text(
    owner_page: Page, owner_user
):
    """TC-N5: на карточке персоны (после клика на orbit-card)
    AI-кнопка «Найти больше» имеет:
    - атрибут disabled (HTML)
    - текст содержит «скоро» (визуальный индикатор)
    - tooltip про публичную бету

    Это **главная** UX-гарантия Phase B+C: пользователь видит что фича
    запланирована, но временно недоступна, а не получает молчаливый fail.

    Источник истины — `js/components/profile.js` отдаёт два варианта
    aiBtn в зависимости от `window.__features.ai_search_enabled`:
    - true: `<button data-action="enrich">Найти больше</button>` (active)
    - false: `<button disabled title="Поиск откроется в публичной бете">
              Найти больше (скоро)</button>`
    """
    page = owner_page
    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)

    # Profile открывается через `window.openProfile(personId)` (см.
    # js/init.js:42 `window.openProfile = openProfile`). Чтобы не зависеть
    # от конкретного UI-навигационного flow (orbit/search/breadcrumb),
    # используем глобальную JS-функцию напрямую — это публичный API
    # компонента profile, который покрывают и delegated event-handlers.
    # Берём первую существующую персону из API tree.
    person_ids = page.evaluate(
        "fetch('/api/tree').then(r => r.json()).then(d => "
        "(d.people || []).map(p => p.id).slice(0, 1))"
    )
    assert person_ids, \
        "API /api/tree не вернул людей — фикстура signup_via_api должна сидировать demo-tree"
    pid = person_ids[0]

    # Открываем профиль программно через публичный API компонента
    page.evaluate(f"window.openProfile({pid!r})")

    profile = page.locator(".profile-page")
    profile.wait_for(state="visible", timeout=5_000)

    # 1. Должна существовать кнопка с текстом «скоро»
    skoro_btn = profile.locator('button:has-text("скоро")')
    assert skoro_btn.count() == 1, (
        f"Ожидали ровно 1 кнопку «скоро» внутри .profile-page, "
        f"получили {skoro_btn.count()}. При ENABLE_AI_SEARCH=0 AI-кнопка "
        f"должна быть disabled с маркером «(скоро)» (см. js/components/profile.js)."
    )

    # 2. И именно disabled (HTML attribute, не css-класс)
    assert skoro_btn.first.is_disabled(), \
        "Кнопка «скоро» должна иметь HTML disabled атрибут — иначе клик " \
        "сработает и улетит в /api/enrich/"

    # 3. Tooltip с правильным текстом
    title = skoro_btn.first.get_attribute("title") or ""
    assert "публичной бете" in title, (
        f'title attribute должен содержать «публичной бете», получили {title!r}. '
        f'См. fallback aiBtn в js/components/profile.js.'
    )

    # 4. НЕ должно быть активной enrich-кнопки (data-action="enrich")
    active_enrich = profile.locator('button[data-action="enrich"]:not([disabled])')
    assert active_enrich.count() == 0, (
        f"При AI off не должно быть active enrich-кнопок (с data-action='enrich' "
        f"и без disabled), нашли {active_enrich.count()}. Это значит aiSearchOn "
        f"в profile.js разруливается неправильно."
    )


def test_window_features_reflects_ai_disabled(owner_page: Page, owner_user):
    """TC-N3: дополнительная проверка — window.__features действительно
    содержит ai_search_enabled=false (отдельно от UI-кнопки, чтобы знать
    что bootstrap отработал)."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle", timeout=10_000)
    flags = owner_page.evaluate("window.__features")
    assert flags is not None, \
        "window.__features не инициализирован — _bootstrapFeatureFlags() не отработал"
    assert flags.get("ai_search_enabled") is False, \
        f"window.__features.ai_search_enabled должен быть False, получили {flags}"


def test_features_endpoint_called_on_bootstrap(page: Page, base_url: str):
    """TC-N3: при загрузке главной страницы frontend должен дёрнуть
    /api/config/features (bootstrap window.__features в js/init.js)."""
    seen_calls = []
    page.on("request", lambda req: seen_calls.append(req.url) if "/api/config/features" in req.url else None)

    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)

    assert any("/api/config/features" in url for url in seen_calls), \
        f"Не было запроса к /api/config/features. Все запросы:\n" + \
        "\n".join(seen_calls[:10])
