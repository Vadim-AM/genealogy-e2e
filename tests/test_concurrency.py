"""INV-EDIT-001: lost update на concurrent PATCH.

**Сценарий:** редактор A открывает карточку Person в editor (загружает
state V1). Редактор B параллельно открывает ту же карточку (V1).
A правит summary → save → V2 в БД. B правит birth → save → V3 в БД.
Все правки B попадают в БД поверх V2 — правки A в полях, которые B
не редактировал, **сохраняются нетронутыми только потому что PATCH
шлёт лишь изменённые поля** (если PATCH семантика — partial). Но
если B также менял summary — правки A теряются молча, без
предупреждения.

**Защита через optimistic concurrency:**
- GET /api/people/{id} возвращает `ETag: "<version>"`.
- PATCH принимает `If-Match: "<version>"`. Если несоответствие → 412
  Precondition Failed; UI показывает «карточка изменена кем-то ещё —
  обновите страницу».

**Run security 28.04:** ни ETag, ни If-Match не реализованы. Concurrent
PATCH'и проходят без conflict signal.

Этот тест проверяет MINIMAL контракт: GET возвращает ETag header.
Полный optimistic-concurrency тест (race + 412) — отдельная история,
требует точной координации. Для регрессии достаточно факта наличия
ETag в response.
"""

from __future__ import annotations

import httpx
import pytest

from tests.messages import TestData
from tests.timeouts import TIMEOUTS


@pytest.mark.xfail(
    reason="INV-EDIT-001: GET /api/people/{id} не возвращает ETag — "
           "concurrent PATCH ведут к lost update без warning'а. Run "
           "security 28.04. Fix: backend handler возвращает ETag "
           "(e.g. hash of updated_at + key fields), PATCH handler "
           "принимает If-Match — иначе 412. См. RFC 7232.",
    strict=False,
)
def test_get_person_returns_etag_for_concurrency(owner_user, base_url: str):
    """INV-EDIT-001: GET /api/people/{id} returns an ETag header.

    Without ETag, frontend can't implement If-Match → no defence
    against lost updates from concurrent editors.
    """
    r = httpx.get(
        f"{base_url}/api/people/{TestData.DEMO_PERSON_ID}",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    etag = r.headers.get("etag") or r.headers.get("ETag")
    assert etag, (
        f"INV-EDIT-001: GET /api/people/{TestData.DEMO_PERSON_ID} "
        f"missing ETag header. Concurrent PATCH'и ведут к lost update "
        f"без conflict-signal'а."
    )
