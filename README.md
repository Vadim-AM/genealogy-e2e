# genealogy-e2e

Browser E2E test suite for [Genealogy Engine](https://github.com/Vadim-AM/Genealogy) — Playwright + pytest.

395 tests across 7 domains, 20 Page Objects, 38 codified rules.
Drives real Chromium against a live FastAPI + PostgreSQL backend.

## Quality standards

### Playwright best practices compliance

| Criterion | Status | Detail |
|-----------|--------|--------|
| Locators as lazy `@property` | ✅ | 260+ properties, zero eager `__init__` assignments |
| Auto-waiting (no `time.sleep`) | ✅ | 9 justified `wait_for_load_state` — all documented |
| Web-first assertions (`expect()`) | ✅ | Every UI assertion via `expect(loc, ErrMsg)` |
| Strict mode | ✅ | All locators scoped, no ambiguous multi-match |
| Test isolation | ✅ | Per-test BrowserContext + per-tenant data isolation |
| Traces & screenshots on failure | ✅ | Playwright tracing + Allure screenshots + optional video |
| Context per test | ✅ | `auth_context_factory` → fresh context per call |
| POM pattern | ✅ | `BasePage` with fluent chaining, scenario-level methods |

### Code quality rules (38 rules in CLAUDE.md)

| Area | Rule | Enforced by |
|------|------|-------------|
| Tests verify, not just pass | Rule 1 | No smoke asserts, no OR-fallbacks |
| Linear flow | Rule 2 | No `if/else` in test bodies |
| No hardcoded text | Rule 4 | All UI strings via `t()` from `src/texts.py` |
| No hardcoded timeouts | Rule 5 | Default in httpx monkey-patch, only `TIMEOUTS.api_long` override |
| Response chain | Rule 8 | `expect_response(r).status(HTTPStatus.OK).schema(Model)` |
| No raw URL strings | Rule 10 | `api/routes.py` constants + `scripts/check_drift.py` lint |
| No xfail/skip | Rule 13 | Green or not in the suite |
| `-> None` on all tests | Rule 19 | 395/395 annotated |
| Semantic locators first | Rule 21 | `get_by_role` > `data-testid` with `# no semantic:` justification |
| `ErrMsg` on every `expect()` | Rule 24 | `expect(loc, ErrMsg.xxx).to_be_visible()` |
| `HTTPStatus` enum | Rule 33 | `HTTPStatus.OK` not `200` |
| Zero bare `assert` | Rule 34 | `should.*` from `assertions/base.py` + ErrMsg |
| Test = scenario | Rule 35 | Zero `page.locator()` in test bodies — all through POM |
| Locators as `@property` | Rule 37 | Lazy evaluation, selector constants via `.format()` |

### Architecture patterns

| Pattern | Implementation |
|---------|---------------|
| Custom assertions by domain | `assertions/base.py` (`should.*`), `tree.py`, `auth.py`, `platform.py` |
| Typed API wrappers | `api/person_api.py`, `auth_api.py` — Pydantic models in/out |
| Module-level routes | `api/routes.py` — constants + builder functions |
| Response sanitization | `framework/response.py` — masks tokens/passwords in error messages |
| Polling via tenacity | `api/enrichment_api.py`, `fixtures/server.py` — `@retry` decorator |
| Parallel + serial passes | xdist `-n 4` parallel (tenant-isolated) + serial (shared-state) |

## Project structure

```
genealogy-e2e/
├── api/                  # routes.py + typed API wrappers (person, auth, mfa, ...)
├── assertions/           # should.* (base) + domain wrappers (tree, auth, platform)
├── config/               # settings.py, timeouts.py, constants.py
├── fixtures/             # pytest plugins: patch, server, users, clients, page_factory
├── framework/            # response.py (expect_response), step.py
├── models/               # Pydantic response models (person, auth, mfa, enrichment, ...)
├── pages/                # 20 Page Objects — @property locators, scenario methods
├── helpers/              # domain helpers (auth, tree, security, admin, enrichment, ui)
├── src/texts.py          # ErrMsg (300+ entries) + locale-aware UI strings + t()
├── test_data/            # GEDCOM samples, XSS/SQL payloads, device descriptors
├── tests/                # 73 test files — ONLY tests + domain conftest.py
│   ├── auth/             # 15 files — signup, login, logout, invite, MFA, session
│   ├── tree/             # 13 files — tree, profile, editor, photos, sources
│   ├── platform/         # 9 files — dashboard, analytics, MFA, WebAuthn, ops
│   ├── admin/            # 5 files — GEDCOM import, owner UI, site config
│   ├── security/         # 12 files — CSP, headers, XSS, SQL injection, timing
│   ├── enrichment/       # 4 files — AI consent, flow, apply, disabled mode
│   ├── ui/               # 11 files — landing, i18n, a11y, responsive, pricing
│   └── test_smoke.py, test_regressions.py, test_api_coverage.py
├── scripts/              # check_drift.py (rule lint), flakiness_report.py
├── Dockerfile            # CI-ready image
└── CLAUDE.md             # 38 rules — codified from real review sessions
```

## Quick start

```bash
# 0. PostgreSQL
docker run -d --name genealogy-e2e-pg \
  -e POSTGRES_USER=genealogy -e POSTGRES_PASSWORD=genealogy \
  -e POSTGRES_DB=genealogy_test -p 5432:5432 postgres:16-alpine \
  -c max_locks_per_transaction=4096

# 1. Boot backend (in upstream repo)
cd /path/to/Genealogy/backend
GENEALOGY_TESTING=1 GENEALOGY_TEST_TOKEN=e2e-test-token-default-2026 \
  EMAIL_PROVIDER=mock GENEALOGY_DOCS_ENABLED=1 \
  DATABASE_URL='postgresql+psycopg://genealogy:genealogy@localhost:5432/genealogy_test' \
  uvicorn app.main:app --port 8642 &

# 2. Install
cd /path/to/genealogy-e2e
pip install -e ".[dev]" && playwright install chromium

# 3. Run (two passes)
export E2E_BACKEND_URL=http://127.0.0.1:8642
pytest tests/ -m "not serial" -n 4 -v    # parallel
pytest tests/ -m serial -p no:xdist -v   # serial
```

```bash
pytest -m auth                    # single domain
pytest tests/test_smoke.py        # smoke only
pytest --headed --slowmo=300      # watch the browser
```

## Tech stack

- **Python 3.12+**, **Playwright** (sync API), **pytest** + xdist
- **Pydantic** (settings validation, API contract models)
- **httpx** (API calls with monkey-patched defaults)
- **tenacity** (retry/polling)
- **Allure** (reporting with traces, screenshots, video)
- **ruff** (lint + format)

## License

Private. Not for redistribution.
