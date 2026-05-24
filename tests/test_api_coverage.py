"""Coverage gate — backend API surface must not silently drift from the suite.

Not a functional test. Compares the live OpenAPI schema of the backend
against the paths the suite knows about (`tests._core.api_paths`) and a
registry of accepted gaps (`KNOWN_GAPS`). When the backend grows a NEW
endpoint covered by neither a test nor the whitelist, this gate goes red —
and the author decides which user-journey should exercise it.

The gate is a *visibility signal*, not a way to "cover" a feature: adding
a line to `KNOWN_GAPS` records debt, it does not discharge it. Real
coverage is a user-journey test (see CLAUDE.md rules). `KNOWN_GAPS` is the
executable roadmap — closing a gap means a new journey + a constant in
`API`, and the line leaves this file.

Requires the backend booted with `GENEALOGY_DOCS_ENABLED=1` (otherwise
`/openapi.json` is 404 — see CLAUDE.md "Running locally").
"""

from __future__ import annotations

import inspect
import re
from http import HTTPStatus

import allure
import httpx

from api import routes
from framework.step import step

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
    """Collapse a parameterised path to canonical form: `{anything}` → `{}`.

    OpenAPI and the catalogue name path params differently
    (`{person_id}` vs `{pid}`) — normalisation makes them comparable.
    """
    return _PARAM_RE.sub("{}", path)


def _catalogue_paths() -> set[str]:
    """Every `/api/*` path the suite knows via `tests._core.api_paths`.

    Module-level string constants are taken verbatim; builder functions
    are invoked with a sentinel argument to recover the path template.
    """
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
    """Every `/api/*` path from the backend's live OpenAPI schema.

    `/api/_test/*` is excluded — it is test instrumentation, not the
    product surface the suite must cover.
    """
    r = httpx.get(f"{base_url}/openapi.json")
    assert r.status_code == HTTPStatus.OK, (
        f"GET /openapi.json → {r.status_code}; the backend must be booted "
        f"with GENEALOGY_DOCS_ENABLED=1 (see CLAUDE.md 'Running locally')."
    )
    spec = r.json()
    return {
        _normalise(path)
        for path in spec["paths"]
        if path.startswith("/api/") and not path.startswith("/api/_test/")
    }


@allure.title("Покрытие: все backend API-пути известны каталогу тестов")
def test_every_backend_api_path_is_known(base_url: str) -> None:
    """Every backend `/api/*` endpoint is in the routes catalogue or `KNOWN_GAPS`.

    Goes red when the backend grows a NEW endpoint the suite has never
    seen — the signal that a user-journey touching it is needed (and the
    path, meanwhile, belongs in `KNOWN_GAPS` as recorded debt).
    """
    with step("действие: сравнить backend OpenAPI с каталогом API"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()
        unknown = backend - catalogue - KNOWN_GAPS

    with step("проверка: нет неизвестных эндпоинтов"):
        assert not unknown, (
            "New backend endpoints outside the catalogue and outside KNOWN_GAPS:\n  "
            + "\n  ".join(sorted(unknown))
            + "\n\nAdd a user-journey test exercising the endpoint plus a "
            "constant in tests/_core/api_paths.py — or, if coverage is "
            "deferred, a line in KNOWN_GAPS tagged with its roadmap group."
        )


@allure.title("Покрытие: KNOWN_GAPS не содержит устаревших записей")
def test_known_gaps_not_stale(base_url: str) -> None:
    """`KNOWN_GAPS` must not rot.

    A path leaves the registry once (a) the backend dropped it, or (b) it
    reached the routes catalogue (i.e. it is covered) — otherwise the
    whitelist accumulates noise and masks real gaps.
    """
    with step("действие: проверить KNOWN_GAPS на устаревшие записи"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()

    with step("проверка: нет удалённых upstream и нет уже покрытых"):
        removed_upstream = KNOWN_GAPS - backend
        assert not removed_upstream, (
            "KNOWN_GAPS references endpoints no longer in the backend — "
            "drop the stale lines:\n  " + "\n  ".join(sorted(removed_upstream))
        )
        now_covered = KNOWN_GAPS & catalogue
        assert not now_covered, (
            "KNOWN_GAPS references endpoints already in the API catalogue — "
            "drop the closed lines:\n  " + "\n  ".join(sorted(now_covered))
        )
