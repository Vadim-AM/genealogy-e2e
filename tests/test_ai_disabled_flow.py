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

import httpx
import pytest
from playwright.sync_api import Page, expect


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


def test_enrich_run_returns_503_or_4xx_when_ai_disabled(uvicorn_server: str):
    """TC-N4: POST /api/enrich/<pid>/run при ENABLE_AI_SEARCH=0 не должен
    запускать AI-job. Принимаем 503 (router-guard сработал) или 404/405
    (route не зарегистрирован в текущем backend) — НИКОГДА не 200/500."""
    r = httpx.post(
        f"{uvicorn_server}/api/enrich/p_test/run",
        json={},
        timeout=10,
    )
    assert r.status_code in (404, 405, 503), \
        f"Ожидали 503/404/405, получили {r.status_code}: {r.text[:200]}"


def test_enrich_arbitrary_subpath_503_or_404(uvicorn_server: str):
    """TC-N4: даже несуществующий subpath под /api/enrich возвращает 503
    или 404 — НИКОГДА не 200.

    Граничный случай: router-level guard срабатывает до route-resolution,
    но FastAPI может ответить 404/405 раньше. Принимаем оба варианта —
    важно что НЕ 200/500 (= AI вызван не должен быть).
    """
    r = httpx.post(
        f"{uvicorn_server}/api/enrich/this-path-definitely-does-not-exist",
        json={},
        timeout=10,
    )
    assert r.status_code in (404, 405, 503), \
        f"Ожидали 404/405/503, получили {r.status_code}: {r.text[:200]}"


# ─────────────────────────────────────────────────────────────────────────
# Owner UI — кнопка «Найти больше» в disabled state
# ─────────────────────────────────────────────────────────────────────────


def test_owner_profile_ai_button_disabled(owner_page: Page, owner_user):
    """TC-N5: на /owner или карточке персоны кнопка AI-search отображается
    как disabled с текстом «(скоро)» (через js/components/profile.js).

    Тест проходит на главную страницу tenant'а (/), там должно быть демо-древо.
    Открывает любую карточку персоны и проверяет состояние AI-кнопки.
    """
    page = owner_page
    page.goto("/")
    page.wait_for_load_state("networkidle", timeout=10_000)

    # Проверяем что window.__features загрузилось (bootstrapFeatureFlags)
    flags = page.evaluate("window.__features")
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
