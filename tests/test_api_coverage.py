"""Coverage gate — backend API surface must not silently drift from the suite.

Not a functional test. Compares the live OpenAPI schema of the backend
against the paths the suite knows about (`tests.api_paths.API`) and a
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

import allure
import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS

# Accepted coverage gaps — the debt registry. Each line is tagged with its
# journey-roadmap group. A gap is closed by a new journey test exercising
# the endpoint + a constant in `tests/api_paths.py::API`; the line then
# leaves this set. Do NOT add a line here just to silence the gate for a
# brand-new endpoint without recording which journey will own it.
KNOWN_GAPS: frozenset[str] = frozenset()
# Empty: every backend /api/* path is exercised by a journey or a
# backend-invariant test. New endpoints must land here with a roadmap
# tag, or (preferably) with their covering test in the same change.


_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalise(path: str) -> str:
    """Collapse a parameterised path to canonical form: `{anything}` → `{}`.

    OpenAPI and the catalogue name path params differently
    (`{person_id}` vs `{pid}`) — normalisation makes them comparable.
    """
    return _PARAM_RE.sub("{}", path)


def _catalogue_paths() -> set[str]:
    """Every `/api/*` path the suite knows via `tests.api_paths.API`.

    String constants are taken verbatim; `staticmethod` builders are
    invoked with a sentinel argument to recover the path template.
    """
    paths: set[str] = set()
    for name, value in vars(API).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str) and value.startswith("/api/"):
            paths.add(_normalise(value))
        elif isinstance(value, staticmethod):
            fn = value.__func__
            argc = len(inspect.signature(fn).parameters)
            rendered = fn(*(["{X}"] * argc))
            if rendered.startswith("/api/"):
                paths.add(_normalise(rendered))
    return paths


def _backend_api_paths(base_url: str) -> set[str]:
    """Every `/api/*` path from the backend's live OpenAPI schema.

    `/api/_test/*` is excluded — it is test instrumentation, not the
    product surface the suite must cover.
    """
    r = httpx.get(f"{base_url}/openapi.json", timeout=TIMEOUTS.api_request)
    assert r.status_code == 200, (
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
def test_every_backend_api_path_is_known(base_url: str):
    """Every backend `/api/*` endpoint is in the `API` catalogue or `KNOWN_GAPS`.

    Goes red when the backend grows a NEW endpoint the suite has never
    seen — the signal that a user-journey touching it is needed (and the
    path, meanwhile, belongs in `KNOWN_GAPS` as recorded debt).
    """
    backend = _backend_api_paths(base_url)
    catalogue = _catalogue_paths()

    unknown = backend - catalogue - KNOWN_GAPS
    assert not unknown, (
        "New backend endpoints outside the catalogue and outside KNOWN_GAPS:\n  "
        + "\n  ".join(sorted(unknown))
        + "\n\nAdd a user-journey test exercising the endpoint plus a "
        "constant in tests/api_paths.py::API — or, if coverage is "
        "deferred, a line in KNOWN_GAPS tagged with its roadmap group."
    )


@allure.title("Покрытие: KNOWN_GAPS не содержит устаревших записей")
def test_known_gaps_not_stale(base_url: str):
    """`KNOWN_GAPS` must not rot.

    A path leaves the registry once (a) the backend dropped it, or (b) it
    reached the `API` catalogue (i.e. it is covered) — otherwise the
    whitelist accumulates noise and masks real gaps.
    """
    backend = _backend_api_paths(base_url)
    catalogue = _catalogue_paths()

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
