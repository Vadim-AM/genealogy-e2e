"""Coverage gate — backend API surface must not silently drift from the suite."""

from __future__ import annotations

import inspect
import re
from http import HTTPStatus

import allure
import httpx

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

# Принятые пробелы покрытия — реестр долга. Каждая строка помечена
# группой roadmap. Пробел закрывается новым journey-тестом, проверяющим
# endpoint + константой в `tests/_core/api_paths.py`; после этого строка
# удаляется. НЕ добавляйте строку только чтобы заглушить gate для
# нового endpoint'а без указания, какой journey его покроет.
KNOWN_GAPS: frozenset[str] = frozenset()
# Пусто: каждый backend `/api/*` путь покрыт journey- или
# backend-invariant тестом. Новые endpoint'ы должны попадать сюда с
# roadmap-тегом, или (предпочтительно) с покрывающим тестом в том же изменении.


_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalise(path: str) -> str:
    """Collapse a parameterised path to canonical form: `{anything}` → `{}`."""
    return _PARAM_RE.sub("{}", path)


def _catalogue_paths() -> set[str]:
    """Every `/api/*` path the suite knows via `tests._core.api_paths`."""
    paths: set[str] = set()
    for name, value in vars(routes).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str) and value.startswith("/api/"):
            paths.add(_normalise(value))
        elif callable(value) and not isinstance(value, type):
            argc = len(inspect.signature(value).parameters)
            if argc == 0:
                continue
            rendered = value(*(["{X}"] * argc))
            if isinstance(rendered, str) and rendered.startswith("/api/"):
                paths.add(_normalise(rendered))
    return paths


def _backend_api_paths(base_url: str) -> set[str]:
    """Every `/api/*` path from the backend's live OpenAPI schema."""
    r = httpx.get(f"{base_url}/openapi.json")
    expect_response(
        r, label="GET /openapi.json (boot with GENEALOGY_DOCS_ENABLED=1)",
    ).status(HTTPStatus.OK)
    spec = r.json()
    return {
        _normalise(path)
        for path in spec["paths"]
        if path.startswith("/api/") and not path.startswith("/api/_test/")
    }


@allure.title("Покрытие: все backend API-пути известны каталогу тестов")
def test_every_backend_api_path_is_known(base_url: str) -> None:
    """Every backend `/api/*` endpoint is in the routes catalogue or `KNOWN_GAPS`."""
    with step("действие: сравнить backend OpenAPI с каталогом API"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()
        unknown = backend - catalogue - KNOWN_GAPS

    with step("проверка: нет неизвестных эндпоинтов"):
        should.be_empty(unknown, ErrMsg.unknown_endpoints_found)


@allure.title("Покрытие: KNOWN_GAPS не содержит устаревших записей")
def test_known_gaps_not_stale(base_url: str) -> None:
    """`KNOWN_GAPS` must not rot."""
    with step("действие: проверить KNOWN_GAPS на устаревшие записи"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()

    with step("проверка: нет удалённых upstream и нет уже покрытых"):
        removed_upstream = KNOWN_GAPS - backend
        should.be_empty(removed_upstream, ErrMsg.stale_known_gaps)
        now_covered = KNOWN_GAPS & catalogue
        should.be_empty(now_covered, ErrMsg.covered_known_gaps)
