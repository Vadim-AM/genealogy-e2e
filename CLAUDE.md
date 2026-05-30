# Conventions for Claude Code working on this repo

Loaded into every session here. Captures **what's been learned working on
this suite** so future sessions don't repeat past mistakes. Read first.

## What this repo is

Browser e2e suite (Playwright + pytest) for **upstream `Vadim-AM/Genealogy`**
(separate repo, FastAPI + vanilla-JS product). Tests run against an externally
booted backend, test-instrumented via `GENEALOGY_TESTING=1` + the `/api/_test/*`
endpoints (`backend/app/_test_endpoints.py` upstream). `E2E_BACKEND_URL` points
at it. CI (`pr-check.yml`) checks out both repos and boots uvicorn.

## Hard rules — break these and the suite stops earning trust

Extracted from a real review where the suite was rewritten under explicit user
direction (28.04.2026). Memorise them. Rule numbers are a contract —
`scripts/check_drift.py` and commit messages cite them; never renumber.

### 1. Tests verify, never just pass

The suite exists to **catch regressions**. A test that passes regardless of
whether the feature works is worse than none — false safety.

**Tests are user journeys.** Walk the user's path through the browser —
navigate, type, click, observe — and assert on visible behaviour, not "endpoint
returned 200". Drive the UI; raw API calls belong only in fixtures and the few
backend invariants no UI can express (date-order rejection, cross-tenant
isolation). «Зашёл → ввёл почту → получил ссылку из письма → попал на стартовую
→ увидел welcome» is a test; a bare status-code assertion documents an endpoint.

**Anti-patterns that make tests pass-by-default:**
- `pytest.skip` fallback (`if status==404: skip`). A missing core endpoint is a
  regression — fail loud. No `skip` without an owner decision (Rule 13).
- `xfail`/`xpass`/`skip` markers — the suite carries none (Rule 13).
- OR-fallbacks (`assert a or b`) — one branch is usually the broken state. Hard
  `expect(...)` only.
- "Smoke" on functional tests (`expect(body).to_be_visible()`, `status < 500`,
  `"/login" in url`) — always true, says nothing about behaviour.
- `None` in whitelist (`status in (None, "ok")`) — absence silently passes.
- Accept-any-of-N field names (`tier or new_users or users`) — pin one, so a
  backend rename gets caught.

### 2. Linear flow, no branching in tests

Read top-to-bottom. No `if/else` for "X or Y is fine", no `try/except`
swallowing assertions, no data-driven early returns. Two valid outcomes = **two
tests**. Acceptable conditionals: `parametrize`, fixture setup, listener filters
(`page.on("response", lambda r: ... if ...)`).

### 3. Selectors must survive product refactors

The product flips between `onclick="..."` and `[data-action="..."]` (BUG-SEC-002
sweep is incremental); a test bound to one form breaks when the other lands.

**Use semantic locators:** `get_by_role("button", name=t(Buttons.EDIT))`,
`get_by_label`, `get_by_text`; class+scope
(`.profile-family-group:has-text("Родители") .profile-rel-add`) when role/name
isn't unique. **Avoid:** `[onclick*="..."]` substrings, `[data-action]` when
`onclick` is also used, bare shared-class chains (`button.btn-primary`), and
`.or_()` chains of 3 selectors (that's a TODO, not a passing test).

### 4. No hardcoded text in tests

Every Russian string the suite asserts on or selects by lives in `src/texts.py`
— switching to English is one file edit, not a ~30% rewrite. To add a string:
(1) pick the class (`Buttons`, `Links`, `Brand`, `Invite`, `PII`, `TestData`,
`FamilyGroups`, ...); (2) `dict[locale, str]` if it translates, plain `str` if
not (proper noun "ЦАМО", structural "0 HEAD"); (3) reference `t(Buttons.SAVE)`,
never inline. Add an `en` translation even without an English locale yet.

### 5. No hardcoded timeouts — and all config via `config/settings.py`

Every timeout routes through `config/timeouts.py`. Env config validates at
collection time via Pydantic (`config/settings.py`):

| Env var | Required | Default |
|---------|----------|---------|
| `E2E_BACKEND_URL` | **yes** | (none — must set) |
| `E2E_TIMEOUT_MULTIPLIER` | no | `1.0` |
| `E2E_TEST_TOKEN` | no | `e2e-test-token-default-2026` |
| `E2E_LOCALE` | no | `ru` |
| `E2E_RECORD_VIDEO` | no | `false` |

Invalid/missing required env → immediate `pytest.exit` before any fixture.
Default httpx timeout (10s) is built into the monkey-patch (`fixtures/patch.py`)
— don't pass `timeout=`; override only with `TIMEOUTS.api_long` (30s) for
exports/GEDCOM import/enrichment. Playwright `expect()` auto-wait is fine — no
explicit `timeout=10_000`; bump the global multiplier instead. **Never**
`page.wait_for_timeout(N)` — use `expect_response()`, `wait_for_url()`, or
`expect(loc).to_be_visible()`.

### 6. Document a new bug — don't xfail it

A journey test is **not committed while the bug is open** (Rule 13). Instead:
(1) record it in `memory/` — symptom, root-cause hint, where to fix; (2) raise
upstream with a fresh `BUG-XXX-N` ID — check upstream `docs/test-plan.md` for
collisions (their `BUG-EDITOR-001` = adaptive grid; ours empty `branch=""` on
save → `BUG-EDITOR-002`); (3) write the journey once the fix lands — green from
its first run. The coverage gate (`tests/test_api_coverage.py`, `KNOWN_GAPS`)
keeps the uncovered endpoint visible meanwhile.

### 7. Read JS/Python before guessing

Before a POM: read `js/components/<name>.js` for real selectors
(classes/IDs/`onclick` payloads beat guesses) and `backend/app/<area>.py` for
the response schema (pin one canonical field name). POMs with
`TODO Wave N: verify against ...` are selectors written without the source —
convert before merging.

### 8. Response assertions — go through `expect_response(r)`

```python
# bad:  assert r.status_code == 200; data = r.json(); assert "tenant_slug" in data
# good: expect_response(r).status(HTTPStatus.OK).json_has("tenant_slug")
```

Chains `.status()`, `.status_ok()`, `.json_has()`, `.json_eq()`,
`.schema(Model)` — every failure auto-includes method, URL, status, sanitised
body (tokens masked). Tests use it; fixtures keep `.raise_for_status()`. Typed
API helpers return the `ApiResponse` wrapper
(`ApiResponse(r).expect(label=...).status(...).schema(...)`). Raw `.json()` only
in `test_api_coverage.py` (OpenAPI parsing) and Playwright `Response`; all httpx
2xx go through `.schema(Model)` or typed `api/` helpers.

### 9. No raw `httpx.*` calls — go through `tenant_client(user)`

Encapsulates the per-call `cookies=user.cookies, headers={"X-Tenant-Slug": ...}`
plumbing + default timeout:

```python
def test_x(owner_user, tenant_client):
    api = tenant_client(owner_user)
    api.patch(routes.person(pid), json={"summary": "..."})
```

Per-request `timeout=TIMEOUTS.api_long` override is fine. Multiple users → call
the factory again (each closed on teardown). **Anonymous calls** (lending,
health) — `httpx.get(f"{base_url}{routes.HEALTH}")` directly, no client.

### 10. No raw URL strings — go through `api/routes`

```python
# bad:  api.get(f"/api/people/{pid}")
# good: api.get(routes.person(pid))
```

Backend rename → one place to update, autocomplete, contract visible in code.

### 11. No raw credentials/tokens — go through `config/constants`

```python
password = TestConfig.DEFAULT_PASSWORD           # not "test_password_8plus"
email = make_email("label")                       # deterministic
email = unique_email("waitlist1")                 # uuid-suffixed (when reset_state won't wipe the target table)
```

### 12. User creation — through conftest factories, not inline

Need... → use:
- verified, logged-in → `owner_user` (default) or `signup_via_api(email=...)`
- signed-up but **un**verified → `signup_unverified(email=...)`
- second login of existing → `login_existing(email)`
- latest MockSender token (verify/reset) → `read_email_token(email)`
- invite issued by owner → `create_invite(owner, role=..., name=...)`
- accept that invite → `accept_invite(token, cookies=...)`
- AI consent stamp → `grant_ai_consent(user)`

**Never** inline `SIGNUP → VERIFY_EMAIL → LOGIN` — 8+ lines of plumbing, and
auth-flow changes ripple through every test.

### 13. Green or it doesn't exist — no xfail/skip

The suite carries no `xfail`/`xpass`/`skip`/`pytest.mark.skip`. A test is green
or it's not in the suite — a non-green test normalises red and readers stop
trusting the signal. A caught bug is recorded, not xfail-tested (Rule 6/7); the
journey is written after the fix. `skip` for a genuinely inapplicable scenario
needs an explicit owner decision — never a default reach for a failing check.

### 14. Safe to run against a moving dev branch

Product main changes daily. Tests must be robust to UI changes (semantic
locators), decoupled from copy edits (catalogue + meaningful-keyword substrings
like "владелец", not whole sentences), and fail **for the right reason** —
contract break, not cosmetic refactor. A failure after a non-functional change
means the test over-fitted markup — refactor it to assert behaviour.

### 15. Parallel by default; serial only if it mutates the stand

Two passes (see "Running locally"):
- **parallel** (`-m "not serial" -n 4`) — tenant-scoped/independent tests, **no
  per-test reset**: isolation = unique tenant + unique identity (`owner_user` →
  `unique_email`). Many tenants coexist on purpose — that's the production
  condition where cross-tenant / workspace / rate-limit-key leaks surface. A new
  failure here is a **candidate real bug to triage**, not noise to reset away.
- **serial** (`-m serial -p no:xdist`) — tests mutating state a tenant can't
  isolate. Per-test global reset preserved.

`serial` is auto-applied in root `conftest.py` (fixture-based): a test is serial
iff it pulls `superadmin_user` **or** lives in `_SERIAL_FILES`
(`enrichment/test_ai_disabled_flow.py`, `security/test_security_timing.py`,
`admin/test_gedcom_import_deep.py`, `admin/test_gedcom_import_ui.py`,
`ui/test_mobile_smoke.py`, `auth/test_logout.py`,
`enrichment/test_enrichment_apply.py`). A stale entry warns at collection.

**The rule:** a test that mutates shared stand state (platform settings, global
`enable_ai_search`, MFA/audit/feature-flags — anything not tenant-isolated) MUST
be caught by that heuristic — use `superadmin_user`, add the file to
`_SERIAL_FILES`, or `@pytest.mark.serial`. A state-mutating test in the parallel
pass corrupts other workers. Conversely, don't reach for `serial` to paper over
a leak that is actually a product bug — triage it (Rule 1/14).

### 16. Test files contain only tests

A `test_*.py` holds **only** `def test_*()` + imports. Everything else:

| What | Where |
|------|-------|
| Helper functions (navigation, UI actions) | `helpers/<domain>/` |
| Typed API wrappers | `api/<domain>_api.py` |
| Test data (GEDCOM, JPEG bytes, devices) | `test_data/<topic>/` |
| Payload builders (tree/person/relationship) | `test_data/payloads/` |
| Global fixtures (auth, server, clients) | `fixtures/` |
| Domain fixtures (viewport, role builders) | `tests/<domain>/conftest.py` |
| File-scoped autouse fixtures | stays in the test file |
| Page Objects | `pages/` |

Module-level constants (`_IS_OPEN = re.compile(...)`, thresholds) may stay if
consumed only by that file. Pick `helpers/<domain>/` by semantic domain, not by
caller; a cross-domain helper still lives in one domain. No `helpers/common/` —
truly generic → `pages/` (UI) or `fixtures/`.

### 17. Step visibility — in helpers AND test functions

```python
with step("подготовка: создать пользователя"):
    user = signup_via_api()
with step("действие: добавить брата через профиль"):
    panel.click_add_sibling(); modal.fill_and_save(surname="Тест", given="Брат")
with step("проверка: персона добавлена"):
    should.have_length(tree_after, count_before + 1, ErrMsg.x)
```

**Every test >5 lines uses `step()`** with the `подготовка:`/`действие:`/
`проверка:` pattern. 5–10 lines: 2 steps; >10: 3–5. Renders as collapsible
Allure blocks with pass/fail + timing.

### 18. Shared utilities live in POMs, not test files

Reusable patterns belong on Page Objects: `custom_select_for(page, field)` →
`pages/base.py`; `ProfilePanel.navigate_to`, `open_editor_for` →
`pages/profile_panel.py`.

### 19. Type hints + one-line docstrings on all public functions

Full annotations on every param + return; one-line imperative docstring.

```python
def find_person_by_name(api: httpx.Client, *substrings: str) -> dict[str, Any]:
    """Find person whose name contains all substrings (unique match)."""
```

`Self` for fluent methods, `TYPE_CHECKING` for cross-module imports,
`from __future__ import annotations` at the top of every file.

### 20. Fluent-chain POM — methods return target page type

Navigation actions → target POM type; same-page actions → `Self`; void actions
(`expect_*`, `fill_*`) → `None`.

```python
def login(self, email: str, password: str) -> Self:
    """Fill credentials and submit the login form."""
    ...; return self
```

### 21. Semantic locators first, data-testid as fallback

Prefer `get_by_role`/`get_by_label`/`get_by_placeholder` over `data-testid`/ID.
When upstream HTML has no `<label>`/ARIA, keep `data-testid` + a
`# no semantic: <reason>` comment (e.g. `page.locator("#website")  # no
semantic: hidden field`).

### 22. API calls via typed helpers, not raw httpx

```python
# bad:  r = api.post(routes.PEOPLE, json={...}); r.raise_for_status(); r.json()["people"]
# good: person = create_person(api, PersonCreate(id=pid, name=name)); tree = get_tree(api)
```

Use `.schema(Model)` on `expect_response()` for validation. Keep raw calls only
for negative tests (expected 4xx/5xx).

### 23. Use PageFactory, not inline POM construction

```python
# bad:  tree = TreePage(owner_page).goto()
# good: tree = pages.navigate_to(TreePage)   # pages: PageFactory
```

### 24. Assertion messages via ErrMsg class

```python
# bad:  expect(locator).to_be_visible()
# good: expect(locator, ErrMsg.profile_not_visible).to_be_visible()
```

### 25. No `assert` in Page Objects — only `expect()` in tests

POMs hold locators + actions, never test assertions — the POM exposes a
`@property` locator, the test asserts (`expect(tree.h1, ErrMsg.x).to_*()`).
Precondition guards (`assert self._secret, "must call setup first"`) are allowed
— they catch programmer error, not test outcomes.

### 26. No private PO properties from tests

A test needing a POM locator means the property must be public — make it a
`@property`, don't reach into `page._internal_field`.

### 27. POM methods must guarantee stable state on return

A state-changing method waits for the result before returning. If the result is
one of two states (list appeared OR "no results"), wait for one explicitly
(`expect(list_or_empty.first).to_be_visible()`) — else a following
`not_to_be_visible()` is a false positive (element not yet in DOM → passes
instantly).

### 28. Max 2 levels of PO inheritance; decompose via components

`BasePage → FeaturePage` is the max. A third level → extract a component:
repeated UI blocks (modals, panels, dropdowns) become standalone `pages/`
classes receiving a `root: Locator`.

### 29. Files > 500 lines → decompose

Split by domain or component. One POM = one UI domain.

### 30. Diagnostics: MCP browser first, throwaway scripts second

Debug UI via the Playwright MCP browser
(`mcp__plugin_playwright_playwright__browser_*`): navigate → snapshot →
evaluate → click — faster than edit→pytest→screenshot. No `/tmp/` debug
scripts. On failure: trace viewer (`playwright show-trace`) + Allure shots.

### 31. No `except Exception` — use specific types

`except Exception` masks bugs. Use `json.JSONDecodeError`, `ValueError`,
`OSError`, `TypeError`, etc. Only acceptable broad catch: `except BaseException`
in a `finally`-like re-raise pattern.

### 32. No unnecessary `_` prefix

Underscore = "internal, don't import" — use only for truly private helpers
(`_sanitize_json`, `_fail`). Module-level constants, classes, public functions
are public: `Timeouts`, `LOCALE`, `build_timeouts()`.

### 33. Use `from http import HTTPStatus`

`.status(HTTPStatus.OK)`, not `.status(200)`. (httpx 10s default is in the
monkey-patch — don't pass `timeout=` unless overriding to `TIMEOUTS.api_long`.)

### 34. No bare `assert` in tests — use `should.*` or `expect_response`

Three channels, zero bare `assert`: Playwright UI `expect(loc, ErrMsg.x).to_*()`
· httpx API `expect_response(r).status(...).json_eq(...)` · everything else
`should.be_equal(actual, expected, ErrMsg.x)`.

```python
# bad:  assert len(tree.people) == 3
# good: should.have_length(tree.people, 3, ErrMsg.count_mismatch)
```

Custom assertions in `assertions/`: `base.py` (universal — `be_equal`,
`contain`, `any_match`, `be_empty`, `playwright_status`); `tree.py`/`auth.py`/
`platform.py` (domain wrappers). All `what` params use `ErrMsg.*`.

### 35. Test = clean scenario, details in POM (zero low-level calls)

A test body contains **zero** Playwright low-level calls — no `.locator()`,
`.click()`, `.fill()`, `.get_attribute()`, `.wait_for_*()`. The test reads as a
scenario script:

```python
def test_login_success(pages, auth_client) -> None:
    """DoQA #1619: вход в ЛК."""
    login = pages.navigate_to(LoginPage)
    expect(login.login_input, ErrMsg.form_not_visible).to_be_visible()
    login.login(identifier=username, password=password)   # scenario POM
    main = pages.create(MainPage); main.wait_for_page_load()
    expect(main.user_info, ErrMsg.login_success).to_be_visible()
```

**In the body:** `pages.navigate_to/create(POM)`, one-word scenario methods
(`login`, `logout`, `open_editor`, `submit`, `upload`), `expect(...)`,
`should.*()`, `expect_response(...)`. **Not in the body:** `page.locator/goto`,
`.click/.fill/.check`, `wait_for_load_state`, `get_attribute`, `page.on(...)`
(→ conftest fixture), standalone UI helpers (→ POM methods). **POM methods:**
scenario-level name, `with step(...)` inside, return target POM for chaining,
never contain `assert`/`should.*`.

### 36. UI-bound helpers → POM methods (migration complete)

The remaining `helpers/` are API-level (httpx, not page-bound) or cross-POM
orchestration — they correctly stay: `auth/session_helpers.py`,
`tree/tree_api.py`, `tree/add_relative.py` (cross-POM), `security/timing.py`,
`ui/viewport.py`, `ui/i18n_checks.py`. **New code:** a function taking a `Page`
or `Locator` and doing UI interactions belongs on a POM, not in `helpers/`.

### 37. Locators as `@property`, not `self.xxx =` in `__init__`

Lazy `@property` re-queries the DOM on each access:

```python
@property
def tab_map(self) -> Locator:
    return self.page.locator('[data-tab="map"]')
```

Reusable selector strings → module/class constants with `.format()`
(`_CS_OPTION = '...[data-value="{}"]'`). **Zero inline locator strings in POM
methods** — only in `@property` returns and `.format()` templates; methods
reference `self.xxx`.

### 38. Docstrings — 1 sentence, TC-ID preserved

Module docstring 1 line; function docstring 1 sentence + TC-ID. No
multi-paragraph explanations — code + step names tell the story.

```python
"""AI search disabled flow — TC-N3, TC-N4, TC-N5."""        # module
def test_ai_button_disabled(...) -> None:
    """TC-N5: owner → profile → AI-кнопка disabled."""       # function
```

## Project structure

```
genealogy-e2e/
├── assertions/      # should.* (base.py universal) + tree/auth/platform wrappers
├── api/             # routes.py (endpoint catalogue) + typed wrappers
│   └── person_api.py, auth_api.py, mfa_api.py, enrichment_api.py, platform_api.py, ...
├── config/          # settings.py (Pydantic), timeouts.py (TIMEOUTS), constants.py (TestConfig, make_email)
├── framework/       # response.py (expect_response + ApiResponse), step.py (Allure step())
├── models/          # Pydantic API contract models (person, auth, mfa, enrichment, site, platform)
├── fixtures/        # patch.py (httpx monkey-patch), server.py, users.py, clients.py, page_factory.py
├── pages/           # Page Objects — base.py, tree_page.py, profile_panel.py, person_editor.py, add_relative_modal.py, ...
├── helpers/         # API-level + cross-POM only (auth/, tree/, security/, ui/) — see Rule 36
├── src/texts.py     # ErrMsg + locale-aware strings + t() resolver
├── test_data/       # pure data — gedcom/, media/, devices/, payloads/
├── tests/           # ONLY test files + domain conftest.py
│   ├── auth/ tree/ platform/ admin/ security/ enrichment/ ui/
│   └── test_smoke.py, test_regressions.py, test_api_coverage.py, test_api_invariants.py
├── conftest.py      # loads fixtures/* plugins + path→marker + serial heuristic
├── scripts/check_drift.py   # lints rules #5/#8/#9/#10
└── .github/workflows/pr-check.yml
```

Tests under `tests/<domain>/` auto-get `@pytest.mark.<domain>` (root
`conftest.py`) — run one with `pytest -m auth`, no per-file markers.

## Drift enforcement

`scripts/check_drift.py` lints `tests/`/`pages/`/`helpers/` against rules
#5/#8/#9/#10 — a pre-pytest CI step. Catches `page.wait_for_timeout()`,
hardcoded `time.sleep(N)`, `timeout=N` literals, raw `'/api/...'` strings, and
raw `.json()` in test files. Docstring-aware. Whitelist with `# noqa: drift`.

## Running locally

Upstream `dev` is **PostgreSQL-only** since PR-B7 (commits `08cec28`/`4155020`,
cutover `d3836bd` 2026-05-14) — no SQLite fallback, backend `RuntimeError`s
without `DATABASE_URL`. `/api/_test/*` is fail-closed behind a shared-secret
token (commit `4a3f326`): without `GENEALOGY_TEST_TOKEN` it returns **503** and
the autouse `install_mock_ai`/`reset_state` fixtures error out the whole run.

### Docker Compose (рекомендуемый)

```bash
docker compose up --build --abort-on-container-exit e2e   # PG + backend + tests
docker compose run --rm e2e pytest tests/auth/ -v          # subset
allure serve test-results/allure-results                   # report
BACKEND_IMAGE=ghcr.io/vadim-am/genealogy-backend:pr-42 docker compose up --build e2e
```

### Ручной запуск (без Compose)

```bash
# 0. Postgres (Colima engine — `colima start` if down). max_locks_per_transaction
#    is raised: the parallel pass has no per-test reset → tenant schemas
#    accumulate, and the inter-pass `/api/_test/reset` DROPs all in ONE txn;
#    at default 64 locks that hits "out of shared memory" past ~100 tenants.
#    OUR test-container config (not a product change). Recreate (not restart)
#    to start from a clean volume.
docker rm -f genealogy-e2e-pg 2>/dev/null
docker run -d --name genealogy-e2e-pg \
  -e POSTGRES_USER=genealogy -e POSTGRES_PASSWORD=genealogy \
  -e POSTGRES_DB=genealogy_test -p 5432:5432 postgres:16-alpine \
  -c max_locks_per_transaction=4096 -c max_connections=200
# wait: docker exec genealogy-e2e-pg pg_isready -U genealogy -d genealogy_test

# 1. Boot test-instrumented backend (canonical env — matches pr-check.yml)
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
# GENEALOGY_TRUST_FORWARDED_FOR=1 → per-client synthetic X-Forwarded-For in the
# httpx patch — prevents 429s under xdist.

# 2. E2E setup
cd /path/to/genealogy-e2e
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && playwright install chromium

# 3. Run — TWO passes (one shot wedges at ~300 tenants)
export E2E_BACKEND_URL=http://127.0.0.1:8642 E2E_TIMEOUT_MULTIPLIER=1.5
pytest tests/ -m "not serial" -n 4 --dist load -v   # parallel
pytest tests/ -m serial -p no:xdist -v               # serial
```

Iterating? `pytest -m auth -m "not serial" -n 4`. A single file is fine
non-parallel: `pytest tests/ui/test_x.py` (one session baseline reset).

**Boot-env gotcha:** an incomplete env block produces false-positive failures
that look like product regressions. `GENEALOGY_PUBLIC_URL` missing →
`test_welcome_email` fails (`templates.py:38` falls back to prod domain);
`WEBAUTHN_RP_ID`/`WEBAUTHN_ORIGIN` missing → `test_platform_webauthn` 400;
`GENEALOGY_TEST_TOKEN` missing → **every** test errors at setup (503 on
install-mock-ai); `GENEALOGY_DOCS_ENABLED` missing → `/openapi.json` 404 →
`test_api_coverage` fails. Boot with the full block before triaging.

## Key fixtures

- `owner_user` — signed-up + verified + onboarded via `signup_via_api()`. Email
  UUID-suffixed (`owner-<hex8>@e2e.example.com`); default `full_name="Тестовый
  Пользователь"` (also tenant `display_name` + demo-self person `name` —
  search/profile tests rely on it).
- `superadmin_user` — same flow, `super@e2e.example.com` (matches
  `PLATFORM_SUPERADMIN_EMAILS`).
- `owner_page` — Playwright `Page` in an authed context (session cookies +
  `X-Tenant-Slug`).
- `auth_context_factory` — additional contexts (multiple users in one test).
- `signup_via_api` — custom user (different email/name).
- `soft_check` — `expect.soft(...)` for multi-fact smoke blocks.
- `reset_state` (autouse, **serial pass only**) — `/api/_test/reset` between
  serial tests; parallel pass skips it (unique-tenant isolation).

## Backend test endpoints (upstream)

In `genealogy/backend/app/_test_endpoints.py`, gated by `IS_TESTING` **and** a
shared-secret token (commit `4a3f326`, `INV-TEST-001/002/003`). Every call
carries `X-Test-Token: <GENEALOGY_TEST_TOKEN>`, injected by the httpx patch from
`settings.test_token`. Backend must boot with the same value or endpoints
fail-closed (503 no token → 401 no header → 403 wrong token).

| Endpoint | Purpose |
|----------|---------|
| `POST /api/_test/reset` | wipe DB rows + tenants/ + rate limits + MockSender + site_config |
| `POST /api/_test/reset-signup-rate` | only the slowapi signup throttle (cheap, between signups) |
| `GET  /api/_test/last-email?to=...` | latest MockSender mail for a recipient |
| `POST /api/_test/install-mock-ai` | swap enrichment.ai_client for the fixture |
| `POST /api/_test/uninstall-mock-ai` | restore real ai_client |

Contract change upstream → update both repos in lockstep.

## Gotchas

- **`customSelect`** (`js/components/select.js`) wraps every native `<select>`
  and hides it (`display:none`). `.select_option()` on `<select
  data-field="...">` fails "element not visible" — use
  `PersonEditor.select_dropdown(field, value)` (clicks wrapper + option).
  Applies to `gender`, `branch`, `status`.
- **Per-viewport tests** build their own context (default `conftest` viewport
  1440×900). Don't reuse `owner_page` for mobile/responsive — its viewport is
  fixed.

## Branching & commits

**Branch from `dev`, always** — `git switch -c <name> dev`. `dev` is the
integration branch; `main` lags it. A branch cut from `main` misses the current
layout/fixtures and turns structurally unmergeable into `dev` — that has already
cost a near-lost rewrite.

- **One branch = one logical change = one merge into `dev`.** No two parallel
  branches on the same topic — they diverge and work is lost.
- Branch names describe the change: `chore/<topic>`, `fix/<topic>`,
  `test/<topic>`.
- Merge with `--no-ff`, subject `merge: <branch> into dev`.
- Delete a branch once merged — locally **and** on `origin`.
- Commit: imperative subject; body explains the *why*. `Co-Authored-By` trailer
  when Claude wrote it.

## Quick reference: where to put new code

| I need to add... | Put it in... |
|------------------|-------------|
| A new test | `tests/<domain>/test_<feature>.py` |
| A helper function | `helpers/<domain>/<topic>.py` |
| A Page Object | `pages/<page_name>.py` |
| A typed API wrapper | `api/<domain>_api.py` |
| An API route | `api/routes.py` |
| Test data (GEDCOM, JSON, bytes) | `test_data/<topic>/` |
| A global / domain fixture | `fixtures/<topic>.py` / `tests/<domain>/conftest.py` |
| A UI string / ErrMsg | `src/texts.py` |
| A custom assertion | `assertions/base.py` (universal) or `assertions/<domain>.py` |
| An env var | `config/settings.py` (Pydantic field) |

## When in doubt

- Smoke or real contract? → If smoke, delete it (Rule 1).
- Red — commit anyway? → No. Green or it doesn't exist (Rule 13).
- Selector stable enough? → If the dev rewrote this component once, would it
  still pass? If no, refactor (Rule 3).
- Timeout right? → Use the catalogue; add a category, don't inline (Rule 5).

## Claude Code инструменты

- **Hooks** (`.claude/settings.json`) — PostToolUse runs `ruff format` +
  `ruff check --fix` after every `.py` edit.
- **Агент** `test-runner` (`.claude/agents/`) — запуск pytest, анализ падений.
- **Команда** `/verifier` (`.claude/commands/`) — drift-lint + ruff +
  import-check + правила.
