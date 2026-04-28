"""INV-EMAIL-002: endpoint для смены email отсутствует.

**Сценарий:** пользователь компрометирован (известен email + ущербные
пароль), хочет сменить email на свой текущий безопасный. Без endpoint'а
смены email единственный путь — `/delete-tenant` + re-signup, что
**теряет всё пространство** (древо, photos, invites, history).

Run security 28.04 night confirmed: `POST /api/account/me/email`,
`PATCH /api/account/me`, `POST /api/account/change-email` — все 404
или 405. Endpoint просто отсутствует.

Этот тест **не пытается** угадать точный API path — пробует все
правдоподобные. Если ни один не существует, тест помечает gap.
"""

from __future__ import annotations

import httpx
import pytest

from tests.timeouts import TIMEOUTS


# Кандидаты по REST-conventions. Хотя бы один из них должен
# существовать (не возвращать 404/405).
_PROBE_PATHS_AND_METHODS = [
    ("POST", "/api/account/me/email"),
    ("PATCH", "/api/account/me"),
    ("POST", "/api/account/change-email"),
]


@pytest.mark.xfail(
    reason="INV-EMAIL-002: endpoint смены email полностью отсутствует. "
           "Run security 28.04 night: POST /me/email, PATCH /me, POST "
           "change-email — все 404/405. Compromised account нельзя "
           "восстановить без потери данных. Fix: добавить POST "
           "/api/account/me/email с двух-шаговым flow (новый email "
           "получает confirmation link, старый — notification).",
    strict=False,
)
def test_change_email_endpoint_exists(owner_user, base_url: str):
    """Хоть один из стандартных REST-paths смены email должен
    отвечать чем-то, кроме 404/405."""
    seen_404_405 = []
    for method, path in _PROBE_PATHS_AND_METHODS:
        r = httpx.request(
            method,
            f"{base_url}{path}",
            json={"new_email": "newaddr@e2e.example.com", "password": "test_password_8plus"},
            cookies=owner_user.cookies,
            headers={"X-Tenant-Slug": owner_user.slug},
            timeout=TIMEOUTS.api_request,
        )
        if r.status_code in (404, 405):
            seen_404_405.append((method, path, r.status_code))
            continue
        # Любой другой response — endpoint существует (пусть 401/422/500
        # — это уже forward progress, не «отсутствие endpoint'а»).
        return

    pytest.fail(
        f"INV-EMAIL-002: change-email endpoint missing on all probed "
        f"paths: {seen_404_405}. Compromised users can't recover their "
        f"account without /delete-tenant (data loss)."
    )
