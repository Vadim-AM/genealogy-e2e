"""Root pytest config.

Responsibilities:

1. Register fixture plugins (broken out by topic in `fixtures/`).
2. Apply the suite's domain-marker convention by file path: tests under
   `tests/<domain>/` automatically pick up `@pytest.mark.<domain>`.
3. Attach Playwright screenshot on test failure (Allure report).

Fixture content lives in `fixtures/`:
  - `patch.py`           — httpx monkey-patch + Playwright `expect()` default
  - `server.py`          — base_url / health gate / reset / AI-mock install
  - `users.py`           — AuthUser + signup / login / invite factories
  - `clients.py`         — tenant_client / auth_context_factory / owner_page
  - `utils.py`           — soft_check
  - `allure_support.py`  — Allure environment.properties
"""

from __future__ import annotations

import allure
import pytest


def pytest_configure(config: pytest.Config) -> None:
    try:
        from config.settings import settings  # noqa: F401
    except Exception as exc:
        pytest.exit(f"Settings validation failed: {exc}", returncode=2)

pytest_plugins = (
    "fixtures.patch",
    "fixtures.server",
    "fixtures.users",
    "fixtures.clients",
    "fixtures.utils",
    "fixtures.allure_support",
    "fixtures.page_factory",
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when == "call" and report.failed:
        page = getattr(item, "_pw_page", None)
        if page is not None and not page.is_closed():
            try:
                allure.attach(
                    page.screenshot(),
                    name="screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass

_DOMAIN_MARKERS = frozenset({
    "auth", "tree", "platform", "admin",
    "security", "enrichment", "ui",
})

# A test is `serial` (runs single-worker, keeps per-test global reset) if it
# mutates shared stand/backend state that a unique tenant cannot isolate.
# Detection is fixture-based (precise) — not path-based — so e.g. the
# `*_403_for_non_super` platform tests, which only pull `owner_user`, stay
# in the parallel bucket. Any fixture here implies a global mutation:
#   - `superadmin_user`: fixed PLATFORM_SUPERADMIN email + platform-wide
#     surface (settings/MFA/audit/feature-flags) shared across all tenants.
_SERIAL_FIXTURES = frozenset({"superadmin_user"})

# Files that must run single-worker. Two reasons:
# (1) mutate global state the fixture heuristic alone would miss:
#   - test_ai_disabled_flow.py: file-local autouse flips the global
#     `enable_ai_search` platform flag to False for the whole file.
#   - test_security_timing.py: micro-benchmarks latency — any concurrent
#     load invalidates the measurement, so it must run with nothing else.
# (2) heavy async UI / GEDCOM-import flows that are not robust under
#     concurrent host load (browser + import-job contention): the failure
#     set is non-deterministic across xdist worker counts (verified
#     2026-05-19: -n auto vs -n 4 fail *different* tests here), i.e. a
#     test-robustness gap, not a product bug — they are deterministically
#     green single-worker. Serial lane is their correct home; tests still
#     run with every assertion intact (NOT silenced). Root cause:
#     browser+backend resource contention under xdist, not missing
#     settle-waits (test_logout, test_enrichment_apply already have
#     wait_for_authed_shell). Moving back to parallel requires proving
#     stable under `-n 4` on CI hardware — not a code change.
_SERIAL_FILES = frozenset({
    "test_ai_disabled_flow.py",
    "test_security_timing.py",
    # Heavy GEDCOM-import-via-UI (upload + async import job + render) and
    # mobile/logout flows: a bounded, well-defined class that is not
    # concurrency-robust as written. Failure set is non-deterministic
    # across worker counts/runs (test-robustness, not a product bug);
    # all deterministically green single-worker.
    "test_gedcom_import_deep.py",
    "test_gedcom_import_ui.py",
    "test_mobile_smoke.py",
    "test_logout.py",
    # Enrichment-apply drives the AI modal (async job + result render +
    # accept/revert) — same heavy-UI, not-concurrency-robust class;
    # deterministically green single-worker.
    "test_enrichment_apply.py",
})


def pytest_collection_modifyitems(items):
    """Auto-apply markers by convention so individual files need no
    `pytestmark` lines:

    - `@pytest.mark.<domain>` for tests under `tests/<domain>/`
      (filter with `pytest -m auth`).
    - `@pytest.mark.serial` for state-mutating tests (filter the parallel
      pass with `-m "not serial"`; run the rest single-worker). See
      `_SERIAL_FIXTURES` / `_SERIAL_FILES`.

    Tests at the root of `tests/` get no domain marker.
    """
    for item in items:
        domain = item.path.parent.name
        if domain in _DOMAIN_MARKERS:
            item.add_marker(getattr(pytest.mark, domain))

        fixtures = getattr(item, "fixturenames", ())
        if _SERIAL_FIXTURES.intersection(fixtures) or item.path.name in _SERIAL_FILES:
            item.add_marker(pytest.mark.serial)
