"""TC-PRIVACY-1: PII leakage in publicly-mounted static files.

Run 1 (28.04) выявила P0 privacy leak — `js/constants.js` и inline
`<script>` в `index.html` содержали реальные ФИО, фотографии, координаты
переездов реальной семьи владельца, включая несовершеннолетних. Эти
файлы отдаются анонимно через `app.mount("/js", StaticFiles(...))` и
`/` — каждый клиент Self-hosted получает их в своём deploy.

Run 2 (28.04 evening) подтвердила фикс: `constants.js` сжат до 40
строк, inline `<script>` зачищен. Эти тесты — **regression-trail**:
не позволяют PII вернуться в эти файлы при будущих рефакторингах.

`backend/data_updates.sql` ещё содержит 94 PII-совпадений, но в
runtime не применяется — отдельный issue для git/release-чистки,
здесь не покрывается (е2е проверяет HTTP-surface).
"""

from __future__ import annotations

import httpx

from tests.messages import PII
from tests.timeouts import TIMEOUTS


def test_constants_js_no_owner_pii(base_url: str):
    """`/js/constants.js` (public static mount) не содержит owner PII.

    Closed regression — фикс `de7f53a` ("BUG-COPY-001 finalize") убрал
    `photoCaptions` и `timelineGeo`. Этот тест держит файл чистым на
    случай будущих регрессий (например, кто-то inline'ит обратно
    «удобства ради»).
    """
    r = httpx.get(f"{base_url}/js/constants.js", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    body = r.text
    for needle in PII.OWNER_FAMILY_NAMES:
        assert needle not in body, (
            f"BUG-COPY-001 regression: {needle!r} found in /js/constants.js. "
            f"This file is on a public static mount — anyone can GET it "
            f"without auth. Move per-tenant data to API."
        )


def test_index_html_no_owner_pii_in_inline_scripts(base_url: str):
    """`/` (anonymous landing) inline scripts must not contain owner PII.

    Closed regression — фикс `de7f53a` зачистил inline timelineGeo +
    photoCaptions из index.html. Этот тест держит лендинг чистым.
    """
    r = httpx.get(f"{base_url}/", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    body = r.text
    for needle in PII.OWNER_FAMILY_NAMES:
        assert needle not in body, (
            f"BUG-COPY-001 regression: {needle!r} on anonymous landing /. "
            f"Owner data must not be embedded in HTML/inline JS — load "
            f"from per-tenant API or remove."
        )


def test_constants_js_has_no_geo_coordinates(base_url: str):
    """Sanity check: hardcoded migration coordinates removed.

    Old version had explicit lat/lng for places like Тукумс, Черняховск,
    Калининград, Усть-Каменогорск, Да Нанг — owner's family migration
    history. Не должно быть нигде в констанах per-tenant data.
    """
    r = httpx.get(f"{base_url}/js/constants.js", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    body = r.text
    # Любые из owner-specific places — paranoia regression catch.
    forbidden_places = ("Тукумс", "Черняховск", "Усть-Каменогорск", "Да Нанг")
    found = [p for p in forbidden_places if p in body]
    assert not found, (
        f"BUG-COPY-001 regression: owner migration places leaked into "
        f"/js/constants.js: {found}. These should live in per-tenant DB "
        f"(PersonLocation + Location), not as constants."
    )
