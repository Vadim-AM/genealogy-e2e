# genealogy-e2e

UI / browser end-to-end test suite for [Genealogy Engine](https://github.com/Vadim-AM/Genealogy).

Drives a real Chromium against the live FastAPI backend. Maps 1:1 to test
cases in the upstream `docs/test-plan.md` and `docs/qa-first-touch-funnel.md`.

## What this repo does NOT contain

The backend itself — including the `/api/_test/*` instrumentation endpoints
that the suite relies on (DB reset, mock-AI install, MockSender peek). Those
live in the upstream `genealogy` repo under `backend/app/_test_endpoints.py`,
gated by `IS_TESTING=1`.

## Run mode 1: local dev

You already have the backend running on `:8642` (or any port).

```bash
# 1. Start the backend with test instrumentation (in the genealogy repo):
cd /path/to/genealogy/backend
GENEALOGY_TESTING=1 GENEALOGY_ADMIN_PASSWORD=test_admin_password \
  EMAIL_PROVIDER=mock FREE_SIGNUP_LIMIT=1000 \
  PLATFORM_SUPERADMIN_EMAILS=super@e2e.example.com \
  uvicorn app.main:app --port 8642 &

# 2. Set up this repo:
cd /path/to/genealogy-e2e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Run:
E2E_BACKEND_URL=http://127.0.0.1:8642 pytest tests/ -v
```

Useful invocations:

```bash
pytest tests/test_smoke.py            # smoke check
pytest tests/ -m smoke                # only @pytest.mark.smoke tests
pytest tests/ -k "owner"              # name filter
pytest tests/ --headed --slowmo=300   # watch the browser
pytest tests/ --tracing=retain-on-failure  # capture traces
pytest tests/ -n 4                    # parallel (pytest-xdist)
```

## Run mode 2: Docker (CI / clean env)

```bash
# 1. Pull backend image built in the upstream PR
export BACKEND_IMAGE=ghcr.io/vadim-am/genealogy-backend:test-<sha>

# 2. Build e2e image and run the suite
docker compose up --build --abort-on-container-exit e2e
```

Test artifacts (traces, screenshots, videos for failures) land in
`./test-results/`.

## Layout

```
genealogy-e2e/
├── tests/
│   ├── conftest.py             # fixtures: signup_via_api, owner_page, etc.
│   ├── pages/                  # POM (one class per page/component)
│   ├── fixtures/               # static JSON used by tests (AI mock, GEDCOM)
│   ├── test_smoke.py           # canary, runs first
│   ├── test_landing.py         # F-LND-* funnel
│   ├── test_signup_flow.py     # signup + email verify
│   ├── test_login_flow.py      # login + forgot-password
│   ├── test_first_visit.py     # tree render after login
│   ├── test_tree_navigation.py # tabs, F5-routing
│   ├── test_profile.py         # person profile rendering
│   ├── test_owner_ui.py        # /owner — settings, invites, export
│   ├── test_admin_ui.py        # /admin — legacy admin password
│   ├── test_invite_accept.py   # invite acceptance flow
│   ├── test_waitlist.py        # /wait
│   ├── test_legal_pages.py     # /privacy, /terms render HTML
│   ├── test_versioning.py      # footer version comes from API
│   ├── test_platform_dashboard.py  # superadmin metrics
│   ├── test_logout.py
│   ├── test_enrichment_flow.py     # ★ Найти больше (mocked AI)
│   ├── test_regressions.py     # closed BUG-* tickets
│   └── test_edge_cases.py
├── docker/
│   └── Dockerfile.e2e
├── docker-compose.yml          # backend (image) + e2e (built locally)
├── pytest.ini
├── requirements.txt
└── .github/workflows/
    └── pr-check.yml            # boots upstream uvicorn locally, runs full suite
```

## Cross-repo contract

The suite assumes the backend exposes:

| Endpoint                            | Purpose                                               |
|-------------------------------------|-------------------------------------------------------|
| `POST /api/_test/reset`             | wipe DB + tenants + rate limits + MockSender + config |
| `POST /api/_test/reset-signup-rate` | only slowapi signup throttle (cheap)                  |
| `GET  /api/_test/last-email?to=...` | latest MockSender mail for a recipient                |
| `POST /api/_test/install-mock-ai`   | swap enrichment.ai_client for the supplied fixture    |
| `POST /api/_test/uninstall-mock-ai` | restore real ai_client                                |

Plus the standard product endpoints (`/api/account/*`, `/api/tree`, etc.).

## When to update this repo

- A test in `docs/test-plan.md` becomes feasible to automate → add a test here.
- A `BUG-XXX` ticket gets closed → flip the `pytest.mark.xfail` into a
  regular regression assertion (`test_regressions.py`).
- A test starts failing because the upstream renamed a route or selector →
  update the POM, not the assertion. The assertion is the contract.

## License

Private. Not for redistribution.
