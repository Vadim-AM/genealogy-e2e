# genealogy-e2e

UI / browser end-to-end test suite for [Genealogy Engine](https://github.com/Vadim-AM/Genealogy).

Drives a real Chromium against a live FastAPI backend. Maps 1:1 to test
cases in the upstream `docs/test-plan.md`.

## Quick start (local dev)

Requires PostgreSQL, the upstream backend, and Chromium.

```bash
# 0. Postgres (via Docker / Colima)
docker run -d --name genealogy-e2e-pg \
  -e POSTGRES_USER=genealogy -e POSTGRES_PASSWORD=genealogy \
  -e POSTGRES_DB=genealogy_test -p 5432:5432 postgres:16-alpine \
  -c max_locks_per_transaction=4096 -c max_connections=200

# 1. Boot test-instrumented backend (in the upstream repo)
cd /path/to/Vadim-AM/Genealogy/backend
GENEALOGY_TESTING=1 \
  GENEALOGY_ADMIN_PASSWORD=test_admin_password \
  GENEALOGY_TEST_TOKEN=e2e-test-token-default-2026 \
  GENEALOGY_PUBLIC_URL=http://127.0.0.1:8642 \
  WEBAUTHN_RP_ID=localhost \
  WEBAUTHN_ORIGIN=http://localhost:8642 \
  EMAIL_PROVIDER=mock FREE_SIGNUP_LIMIT=1000 \
  PLATFORM_SUPERADMIN_EMAILS=super@e2e.example.com \
  ANTHROPIC_API_KEY=sk-test-stub \
  GENEALOGY_TENANTS_ROOT=/tmp/genealogy-e2e-tenants \
  GENEALOGY_TRUST_FORWARDED_FOR=1 \
  GENEALOGY_DOCS_ENABLED=1 \
  DATABASE_URL='postgresql+psycopg://genealogy:genealogy@localhost:5432/genealogy_test' \
  uvicorn app.main:app --host 127.0.0.1 --port 8642 &

# 2. Set up this repo
cd /path/to/genealogy-e2e
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Run (two passes)
export E2E_BACKEND_URL=http://127.0.0.1:8642 E2E_TIMEOUT_MULTIPLIER=1.5
pytest tests/ -m "not serial" -n 4 --dist load -v   # parallel pass
pytest tests/ -m serial -p no:xdist -v               # serial pass
```

Useful invocations:

```bash
pytest tests/ -m auth              # single domain
pytest tests/test_smoke.py         # smoke only
pytest tests/ --headed --slowmo=300  # watch the browser
pytest tests/ -k "owner"           # name filter
```

## Layout

```
tests/
  _fixtures/        # global fixtures (auth, server, clients)
  _data/            # test data (GEDCOM, JPEG, device descriptors)
  helpers/          # domain-organized helper functions
    auth/ tree/ admin/ security/ enrichment/ ui/
  pages/            # Page Objects (21 classes)
  settings.py       # Pydantic env config (validated at collection)
  response.py       # fluent expect_response(r).status(200).json_has(...)
  step.py           # step() context manager for flow logging
  api_paths.py      # API endpoint constants
  constants.py      # credentials, email helpers
  messages.py       # locale-aware UI string catalogue
  timeouts.py       # timeout categories + E2E_TIMEOUT_MULTIPLIER
  auth/             # 15 test files (44 tests)
  tree/             # 13 test files (45 tests)
  platform/         # 9 test files (83 tests)
  admin/            # 5 test files (28 tests)
  security/         # 10 test files (30 tests)
  enrichment/       # 4 test files (12 tests)
  ui/               # 11 test files (60 tests)
  test_smoke.py     # canary
  test_regressions.py  # closed BUG-* tickets
  test_api_coverage.py # OpenAPI coverage gate
  test_api_invariants.py # backend-only contract tests
```

Domain markers (`auth`, `tree`, etc.) are auto-applied by file path.

## Cross-repo contract

The suite assumes the backend exposes test endpoints (gated by
`GENEALOGY_TEST_TOKEN`):

| Endpoint                            | Purpose                                               |
|-------------------------------------|-------------------------------------------------------|
| `POST /api/_test/reset`             | wipe DB + tenants + rate limits + MockSender + config |
| `POST /api/_test/reset-signup-rate` | only slowapi signup throttle (cheap)                  |
| `GET  /api/_test/last-email?to=...` | latest MockSender mail for a recipient                |
| `POST /api/_test/install-mock-ai`   | swap enrichment.ai_client for the supplied fixture    |
| `POST /api/_test/uninstall-mock-ai` | restore real ai_client                                |
| `POST /api/_test/set-platform-setting` | toggle platform flags (AI search, etc.)            |

## When to update this repo

- A test in `docs/test-plan.md` becomes feasible to automate — add a test.
- A `BUG-XXX` ticket gets closed — add a regression test in
  `test_regressions.py` (no xfail — green or not in the suite).
- A test fails because the upstream renamed a route or selector —
  update the POM or `api_paths.py`, not the assertion.

## License

Private. Not for redistribution.
