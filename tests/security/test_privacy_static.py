"""TC-PRIVACY-1: PII leakage in publicly-mounted static files."""

from __future__ import annotations

import allure
import httpx

from assertions.base import should
from framework.step import step
from src.texts import PII, ErrMsg


@allure.title("Приватность: constants.js не содержит ФИО владельца")
def test_constants_js_no_owner_pii(base_url: str) -> None:
    """`/js/constants.js` (public static mount) не содержит owner PII."""
    with step("действие: запрашиваем /js/constants.js"):
        r = httpx.get(f"{base_url}/js/constants.js")
        r.raise_for_status()
        body = r.text

    with step("проверка: ни одного ФИО владельца в файле"):
        for needle in PII.OWNER_FAMILY_NAMES:
            should.not_contain(body, needle, ErrMsg.pii_leaked)


@allure.title("Приватность: index.html не содержит PII в inline-скриптах")
def test_index_html_no_owner_pii_in_inline_scripts(base_url: str) -> None:
    """`/` (anonymous landing) inline scripts must not contain owner PII."""
    with step("действие: запрашиваем / (лендинг)"):
        r = httpx.get(f"{base_url}/")
        r.raise_for_status()
        body = r.text

    with step("проверка: ни одного ФИО владельца в inline-скриптах"):
        for needle in PII.OWNER_FAMILY_NAMES:
            should.not_contain(body, needle, ErrMsg.pii_leaked)


@allure.title("Приватность: constants.js не содержит координат миграций")
def test_constants_js_has_no_geo_coordinates(base_url: str) -> None:
    """Sanity check: hardcoded migration coordinates removed."""
    with step("действие: запрашиваем /js/constants.js"):
        r = httpx.get(f"{base_url}/js/constants.js")
        r.raise_for_status()
        body = r.text

    with step("проверка: нет координат миграций владельца"):
        forbidden_places = ("Тукумс", "Черняховск", "Усть-Каменогорск", "Да Нанг")
        found = [p for p in forbidden_places if p in body]
        should.be_empty(found, ErrMsg.geo_coordinates_leaked)


# Catch-all для будущих PII попыток без необходимости предсказать имя.
# После фикса `de7f53a` constants.js — ~40 строк (1.5 KB). Любое
# inline'ивание per-tenant данных раздует файл — bound 5KB ловит это
# регардлесс конкретного содержимого.
_CONSTANTS_JS_MAX_BYTES = 5 * 1024


@allure.title("Приватность: размер constants.js не превышает 5 КБ")
def test_constants_js_size_bounded(base_url: str) -> None:
    """`/js/constants.js` is small — guard against re-inlining of."""
    with step("действие: запрашиваем /js/constants.js"):
        r = httpx.get(f"{base_url}/js/constants.js")
        r.raise_for_status()
        size = len(r.content)

    with step("проверка: размер файла не превышает 5 КБ"):
        should.less(size, _CONSTANTS_JS_MAX_BYTES + 1, ErrMsg.constants_js_too_large)
