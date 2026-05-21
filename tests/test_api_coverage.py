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

import httpx

from tests.api_paths import API
from tests.timeouts import TIMEOUTS

# Accepted coverage gaps — the debt registry. Each line is tagged with its
# journey-roadmap group. A gap is closed by a new journey test exercising
# the endpoint + a constant in `tests/api_paths.py::API`; the line then
# leaves this set. Do NOT add a line here just to silence the gate for a
# brand-new endpoint without recording which journey will own it.
KNOWN_GAPS: frozenset[str] = frozenset({
    # ── blocked by a product bug — journey written after the fix ──
    # BUG-SHARE-PG-001: GET /api/share/view → 500 (UndefinedTable
    # `share_token` on the anonymous tenant-less path).
    "/api/share/view/{}",
    # BUG-WAITLIST-PG-002: GET /api/platform/waitlist → 500
    # (UnboundExecutionError on the WaitlistSubscriber mapper).
    "/api/platform/waitlist",
    # ── enrichment tail — fire-and-forget telemetry, no journey ───
    "/api/enrich/{}/feedback",
    "/api/enrich/letters/sent",
    # ── subscription lifecycle — journey pending ──────────────────
    "/api/subscription/current",
    "/api/subscription/cancel",
    "/api/subscription/checkout",
    # ── tenant restore — needs a soft-deleted tenant fixture ──────
    "/api/account/restore-tenant",
    # ── invite-revoke journey — pending ───────────────────────────
    "/api/account/tenant/invites/{}",
    # ── photo upload / metadata journey — pending ─────────────────
    "/api/admin/upload-photo",
    "/api/admin/photos/{}",
    # ── person by display-slug — slug not auto-assigned to demo ───
    "/api/people/by-display-slug/{}",
    # ── platform superadmin tenant-admin — pending ────────────────
    "/api/admin/tenants",
    "/api/admin/tenants/{}",
    "/api/admin/waitlist",
    "/api/admin/waitlist/{}",
    # ── platform superadmin ops (step-up MFA gated) — pending ─────
    "/api/platform/backups",
    "/api/platform/send-onboarding-nudges",
    "/api/platform/tenant-override",
    "/api/platform/tenant-override/{}/{}",
    "/api/platform/tenant-overrides/{}",
    "/api/platform/waitlist/{}/invite",
})


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
