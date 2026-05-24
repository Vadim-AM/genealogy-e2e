# Conventions for Claude Code working on this repo

This file is loaded automatically into every Claude Code session here.
It captures **what's been learned working on this suite** so future sessions
don't repeat past mistakes. Read it first before extending or refactoring.

## What this repo is

Browser end-to-end test suite (Playwright + pytest) for **upstream
`Vadim-AM/Genealogy`** (a separate repo, the FastAPI + vanilla-JS product).
Tests run against an externally booted backend (test-instrumented via
`GENEALOGY_TESTING=1` + the `/api/_test/*` endpoints in
`backend/app/_test_endpoints.py` upstream).

`E2E_BACKEND_URL` env var points at the running backend. CI workflow
(`pr-check.yml`) checks out both repos and boots uvicorn.

## Hard rules — break these and the suite stops earning trust

These were extracted from a real review where the suite was rewritten under
explicit user direction (28.04.2026). Memorise them.

### 1. Tests verify, never just pass

The point of the suite is to **catch regressions** in product behaviour. A
test that always passes (regardless of whether the feature works) is worse
than no test — it signals false safety.

**Tests are user journeys.** An e2e test walks the user's path through the
browser — navigate, type, click, observe what they see — and asserts on
visible behaviour, not on "the endpoint returned 200". Drive the UI; raw
API calls belong only in fixtures (setup/teardown) and in the few backend
invariants no UI can express (date-order rejection, cross-tenant
isolation). «Зашёл → ввёл почту → получил ссылку из письма → попал на
стартовую → увидел welcome» — that is a test; a bare status-code assertion
documents an endpoint, it is not a journey.

**Anti-patterns that make tests pass-by-default:**
- `pytest.skip` as a fallback (`if r.status_code == 404: pytest.skip(...)`).
  A missing core endpoint is a regression — fail loud. The suite uses no
  `skip` without an explicit owner decision (Rule 13).
- `xfail` / `xpass` / `skip` markers of any kind — the suite carries none;
  a test is green or it is not in the suite (Rule 13).
- OR-fallbacks in assertions (`assert visible_a or visible_b`). One of the
  branches usually IS the broken state. Hard `expect(...)` only.
- "Smoke" assertions on functional tests (`expect(body).to_be_visible()`,
  `assert response.status < 500`, `assert "/login" in url`). The body is
  always visible, status<500 is meaningless, URL preservation says nothing
  about feature behaviour.
- `None` in whitelist (`assert status in (None, "ok")`). Absence of value
  silently passes. List concrete values only.
- Accept-any-of-N field names (`tier or new_users or users`). Pin one.
  Backend rename → suite catches it.

### 2. Linear flow, no branching in tests

Tests are read top-to-bottom. No `if/else` for "either X or Y is fine"; no
`try/except` swallowing assertion errors; no early returns based on data.

If the code path the test should exercise has two valid outcomes — that's
**two tests**, not one branched test.

Acceptable conditional behaviour: `parametrize`, fixture setup decisions,
listener filters (`page.on("response", lambda r: collect.append(r) if ...)`).

### 3. Selectors must survive product refactors

The product moves between `onclick="..."` inline handlers and
`[data-action="..."]` event delegation back and forth (BUG-SEC-002 sweep
is incremental). Tests bound to one form break when the other lands.

**Use semantic Playwright locators:**
- `get_by_role("button", name=t(Buttons.EDIT))` — works regardless of
  `onclick` vs `data-action`.
- `get_by_label`, `get_by_text` for content-driven elements.
- Class names + scope (`.profile-family-group:has-text("Родители") .profile-rel-add`)
  when role/name isn't unique enough.

**Avoid:**
- `[onclick*="openProfileEdit"]` substring on inline handlers — breaks on
  serialisation changes (quotes, spacing).
- `[data-action="..."]` when the product also sometimes uses `onclick=`.
- Bare class chains for action buttons (`button.btn-primary`) when several
  buttons share that class.
- `.or_()` chains of three different selectors — that's "I don't know
  what the real selector is", which is a TODO, not a passing test.

### 4. No hardcoded text in tests

Every Russian-language text the suite asserts on or selects by lives in
`src/texts.py`. Switching to English will be one file edit instead
of a ~30% test rewrite.

When you need to add a new visible string:
1. Pick the right class (`Buttons`, `Links`, `Brand`, `Invite`, `PII`,
   `TestData`, `FamilyGroups`, ...).
2. Use `dict[locale, str]` if the value translates, plain `str` if it
   doesn't (proper noun like "ЦАМО", structural like "0 HEAD").
3. Reference via `t(Buttons.SAVE)` — never inline.

When extending the catalogue, add an `en` translation even if there's no
English locale yet — costs one minute, prevents future hunt.

### 5. No hardcoded timeouts — and all config via `config/settings.py`

Every timeout routes through `config/timeouts.py`. All environment config
validates at collection time via Pydantic in `config/settings.py`:

| Env var | Required | Default |
|---------|----------|---------|
| `E2E_BACKEND_URL` | **yes** | (none — must set) |
| `E2E_TIMEOUT_MULTIPLIER` | no | `1.0` |
| `E2E_TEST_TOKEN` | no | `e2e-test-token-default-2026` |
| `E2E_LOCALE` | no | `ru` |
| `E2E_RECORD_VIDEO` | no | `false` |

Invalid or missing required env → immediate `pytest.exit` with a Pydantic
error before any fixture runs.

Default httpx timeout (10s) is built into the monkey-patch (`fixtures/patch.py`)
— don't pass `timeout=` explicitly. Override only when needed:
- `TIMEOUTS.api_long` (30s) — exports, GEDCOM import, enrichment jobs.

Playwright's `expect()` default auto-wait is fine — don't add explicit
`timeout=10_000` in tests; bumping the global multiplier covers it.

**Never** use `page.wait_for_timeout(N)` (fixed sleep — anti-pattern).
Use `page.expect_response("...")`, `page.wait_for_url(...)`, or
`expect(loc).to_be_visible()` (auto-wait).

### 6. Document a new bug — don't xfail it

When the suite catches a real product bug, the journey test is **not
committed while the bug is open** — a non-green test never enters the
suite (Rule 13). Instead:
1. Record the bug in project memory (`memory/`) — symptom, root-cause
   hint, where to fix.
2. Raise it upstream with a fresh `BUG-XXX-N` ID — check upstream
   `docs/test-plan.md` to avoid collisions (e.g. upstream's
   `BUG-EDITOR-001` was adaptive grid; ours empty `branch=""` on save →
   `BUG-EDITOR-002`).
3. Write the e2e journey once the upstream fix lands — green from its
   first run. The coverage gate (`tests/test_api_coverage.py`,
   `KNOWN_GAPS`) keeps the still-uncovered endpoint visible meanwhile.

### 7. Linear product code knowledge: read JS/Python before guessing

Before writing a POM:
- Read `js/components/<name>.js` for selectors. Real classes/IDs/`onclick`
  payloads beat guesses.
- Read `backend/app/<area>.py` for response schema (canonical field names).
  Pin one, don't accept-any-of.

POMs with `TODO Wave N: verify against ...` are a code smell — they are
selectors written without the source. Convert before merging.

### 8. Response assertions — go through `expect_response(r)`

```python
# bad
assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
data = r.json()
assert "tenant_slug" in data

# good
from framework.response import expect_response
expect_response(r).status(HTTPStatus.OK).json_has("tenant_slug")
```

`expect_response(r)` chains `.status()`, `.status_ok()`, `.json_has()`,
`.json_eq()`, `.schema(Model)`. Every failure automatically includes:
method, URL, status, sanitised body excerpt (tokens/passwords masked).
Use in tests; fixtures keep `.raise_for_status()`.

For API helpers returning typed responses, use `ApiResponse` wrapper:
```python
from framework.response import ApiResponse
resp = ApiResponse(raw_response)
data = resp.expect(label="create person").status(HTTPStatus.CREATED).schema(PersonResponse)
```

Raw `.json()` is allowed only in `test_api_coverage.py` (OpenAPI spec
parsing) and Playwright `Response` objects. All httpx `2xx` responses
must go through `.schema(Model)` or typed API helpers from `api/`.

### 9. No raw `httpx.*` calls — go through `tenant_client(user)`

Each test was repeating `cookies=user.cookies, headers={"X-Tenant-Slug":
user.slug}` on every API call. Default timeout is built into the httpx
monkey-patch. Encapsulated in `tenant_client(user)` factory in conftest:

```python
def test_x(owner_user, tenant_client):
    api = tenant_client(owner_user)
    r = api.get(routes.TREE)
    api.patch(routes.person(pid), json={"summary": "..."})
```

Per-request override (`api.post(..., timeout=TIMEOUTS.api_long)`) is fine
when `enrichment` job needs longer. Multiple users in one test → multiple
factory calls (each closed automatically on teardown).

**Anonymous calls** (lending, public health) — pass `httpx.get(f"{base_url}{routes.HEALTH}")`
directly; no client needed. Or use a top-level `httpx.Client(base_url=base_url)`.

### 10. No raw URL strings — go through `api/routes`

```python
# bad
api.get(f"/api/people/{pid}")
# good
api.get(routes.person(pid))
```

When backend renames an endpoint — one place to update, IDE autocomplete,
contract is visible in code.

### 11. No raw credentials/tokens — go through `tests/constants.py::TestConfig`

```python
# bad
password = "test_password_8plus"
# good
password = TestConfig.DEFAULT_PASSWORD

# bad
email = f"label@e2e.example.com"
# good
from config.constants import make_email, unique_email
email = make_email("label")            # deterministic
email = unique_email("waitlist1")      # uuid-suffixed (when reset_state doesn't wipe target table)
```

### 12. User creation — through factories in conftest, not inline

If your test needs:
- a verified, logged-in user → `owner_user` (default) or `signup_via_api(email=...)`.
- a signed-up but **un**verified user → `signup_unverified(email=...)`.
- a second login of an existing user → `login_existing(email)`.
- the latest token from MockSender (verify, reset) → `read_email_token(email)`.
- an invite issued by owner → `create_invite(owner, role=..., name=...)`.
- accepting that invite → `accept_invite(token, cookies=...)`.
- AI consent stamp on owner → `grant_ai_consent(user)`.

**Never** inline `c.post(routes.SIGNUP, ...) → c.post(routes.VERIFY_EMAIL, ...) → c.post(routes.LOGIN, ...)` —
that's 8+ lines of plumbing per test, and changes in the auth flow ripple through every test.

### 13. Green or it doesn't exist — no xfail/skip

The suite carries no `xfail` / `xpass` / `skip` / `pytest.mark.skip`
markers. A test is green or it is not in the suite. A non-green test
normalises red — readers stop trusting the signal.

A bug the suite catches is recorded, not xfail-tested (Rule 7); its
journey test is written after the fix. `skip` for a genuinely
inapplicable scenario needs an explicit owner decision — never a default
reach for a failing check.

### 14. Tests should be safe to run against a moving dev branch

The product main branch can change daily. Tests must be:
- Robust to UI implementation changes (semantic locators).
- Decoupled from arbitrary copy edits (use catalogue, substring on
  meaningful keywords like "владелец", not whole sentences).
- Failing **for the right reason** when product breaks the contract,
  not for an unrelated cosmetic refactor.

If a test fails after a non-functional product change, the test was
over-fitting to implementation. Refactor it to assert behaviour, not
markup.

### 15. Parallel by default; serial only if it mutates the stand

The suite runs in two passes (see "Running locally"):
- **parallel** (`-m "not serial" -n 4`) — tenant-scoped/independent
  tests. **No per-test global reset**: isolation is a unique tenant +
  unique identity (`owner_user` → `unique_email`). Many tenants coexist
  on one backend on purpose — that's the production condition, and where
  cross-tenant / workspace / rate-limit-key leak bugs surface. A new
  failure here is a **candidate real bug to triage**, not noise to
  silence with a reset.
- **serial** (`-m serial -p no:xdist`) — tests that mutate state a
  unique tenant can't isolate. Per-test global reset is preserved.

`serial` is auto-applied in root `conftest.py` (fixture-based, precise):
a test is serial iff it pulls `superadmin_user` **or** lives in
`_SERIAL_FILES` (domain-qualified paths: `enrichment/test_ai_disabled_flow.py`,
`security/test_security_timing.py`, `admin/test_gedcom_import_deep.py`,
`admin/test_gedcom_import_ui.py`, `ui/test_mobile_smoke.py`,
`auth/test_logout.py`, `enrichment/test_enrichment_apply.py`). A stale
entry triggers a pytest warning at collection time.

**The rule:** if a test mutates shared stand/backend state (platform
settings, the global `enable_ai_search` flag, MFA/audit/feature-flags,
anything not isolated by tenant), it MUST be caught by that heuristic —
either it genuinely uses `superadmin_user`, or add its file to
`_SERIAL_FILES` (or `@pytest.mark.serial` it explicitly). A
state-mutating test that lands in the parallel pass will corrupt other
workers and produce confusing cross-talk. Conversely, do not reach for
`serial` to paper over a leak failure that is actually a product bug —
triage it (Rule 1/14).

### 16. Test files contain only tests

A `test_*.py` file must contain **only** `def test_*()` functions and
imports. Everything else has a dedicated home:

| What | Where |
|------|-------|
| Helper functions (navigation, UI actions) | `helpers/<domain>/` |
| Typed API wrappers | `api/<domain>_api.py` |
| Test data (GEDCOM samples, JPEG bytes, device descriptors) | `test_data/<topic>/` |
| Payload builders (tree, person, relationship factories) | `test_data/payloads/` |
| Global fixtures (auth, server, clients) | `fixtures/` |
| Domain-scoped fixtures (viewport factories, role builders) | `tests/<domain>/conftest.py` |
| File-scoped autouse fixtures (AI-flag toggle, device parametrize) | stays in the test file |
| Page Objects | `pages/` |

**Module-level constants** (`_IS_OPEN = re.compile(...)`, threshold values)
may stay in the test file when they are consumed only by that file.

When adding a new helper: pick `helpers/<domain>/` by semantic domain,
not by which test file calls it. A helper used by multiple domains still
lives in one domain — the domain it most naturally belongs to. No
`helpers/common/` — if it's truly generic, it goes in `pages/`
(if UI-related) or `fixtures/` (if fixture-related).

### 17. Step visibility — in helpers AND test functions

```python
from framework.step import step

with step("подготовка: создать пользователя"):
    user = signup_via_api()
with step("действие: добавить брата через профиль"):
    panel.click_add_sibling()
    modal.fill_and_save(surname="Тест", given="Брат")
with step("проверка: персона добавлена"):
    assert len(tree_after) == count_before + 1
```

**Every test function >5 lines must use `step()`** to wrap logical phases.
Step names follow the pattern: `подготовка:`, `действие:`, `проверка:`.
Short tests (5-10 lines): 2 steps. Long tests (>10 lines): 3-5 steps.
Steps render as collapsible blocks in Allure with pass/fail + timing.

### 18. Shared utilities live in POMs, not in test files

Patterns reusable across tests belong on Page Objects:
- `custom_select_for(page, field)` → `pages/base.py`
- `ProfilePanel.navigate_to(page, person_id)` → `pages/profile_panel.py`
- `open_editor_for(page, person_id)` → `pages/profile_panel.py`

### 19. Type hints + one-line docstrings on all public functions

Every public function, method, and fixture has:
- Full type annotations on all parameters and return type
- A one-line imperative docstring (`"""Verb + what it does."""`)

```python
def find_person_by_name(api: httpx.Client, *substrings: str) -> dict[str, Any]:
    """Find person whose name contains all substrings (unique match)."""
```

Use `Self` for fluent methods, `TYPE_CHECKING` for cross-module imports.
`from __future__ import annotations` at the top of every file.

### 20. Fluent-chain POM — methods return target page type

POM action methods return the target page object for chaining:
- Navigation actions → return the target POM type
- Same-page actions → return `Self`
- Void actions (expect_*, fill_*) → return `None`

```python
class LoginPage(BasePage):
    def login(self, email: str, password: str) -> Self:
        """Fill credentials and submit the login form."""
        ...
        return self
```

### 21. Semantic locators first, data-testid as fallback

Prefer Playwright semantic locators (`get_by_role`, `get_by_label`,
`get_by_placeholder`) over `data-testid` or ID-based selectors. When
HTML upstream doesn't support semantic (no `<label>`, no ARIA role), keep
`data-testid` and add `# no semantic: <reason>` comment.

```python
# good — semantic
self.submit_btn = page.get_by_role("button", name=t(Buttons.LOGIN))
self.email = page.get_by_label(t(Labels.EMAIL))

# fallback — with justification
self.honeypot = page.locator("#website")  # no semantic: hidden field
```

### 22. API calls via typed helpers, not raw httpx

```python
# bad — raw API call with inline JSON and untyped response
r = api.post(routes.PEOPLE, json={"id": pid, "name": name, "branch": "paternal", "gender": "m"})
r.raise_for_status()
people = r.json()["people"]

# good — typed helper with Pydantic model
from api.person_api import create_person, get_tree
from models.person import PersonCreate

person = create_person(api, PersonCreate(id=pid, name=name))
tree = get_tree(api)
assert person.name == name
```

Use `.schema(Model)` on `expect_response()` for response validation.
Keep raw calls only for negative tests (expected 4xx/5xx).

### 23. Use PageFactory, not inline POM construction

```python
# bad
tree = TreePage(owner_page).goto()

# good
def test_tree(pages: PageFactory):
    tree = pages.navigate_to(TreePage)
```

### 24. Assertion messages via ErrMsg class

```python
# bad
expect(locator).to_be_visible()

# good
from src.texts import ErrMsg
expect(locator, ErrMsg.profile_not_visible).to_be_visible()
```

### 25. No `assert` in Page Objects — only `expect()` in tests

Page Objects contain only locators and actions, never test assertions. All
test assertions live in test functions via `expect(locator, ErrMsg.x).to_*()`.
Precondition guards (`assert self._secret, "must call setup first"`) are
allowed — they protect against programmer error, not test outcomes.

```python
# bad — assert in POM
class TreePage(BasePage):
    def verify_rendered(self):
        assert self.h1.is_visible()  # ← never

# good — POM returns locator, test asserts
class TreePage(BasePage):
    @property
    def h1(self) -> Locator:
        return self._page.locator("h1")

def test_tree(pages):
    tree = pages.navigate_to(TreePage)
    expect(tree.h1, ErrMsg.tree_not_rendered).to_be_visible()
```

### 26. No private PO properties from tests

If a test needs a POM locator, the property must be public. Don't access
`page._internal_field` from a test file — make it a `@property`.

### 27. POM methods must guarantee stable state on return

Every POM method that changes page state must wait for the result to
stabilise before returning. If the result can be one of two states (list
appeared OR "no results" label appeared), wait for one of them explicitly
(e.g. `expect(list_or_empty.first).to_be_visible()`) — otherwise
`not_to_be_visible()` after the method gives a false positive (element
not yet in DOM → check passes instantly).

### 28. Max 2 levels of PO inheritance; decompose via components

`BasePage → FeaturePage` is the maximum. A third level is a signal to
extract a component. Repeated UI blocks (modals, panels, dropdowns)
become standalone classes in `pages/` that receive a `root: Locator`.

### 29. Files > 500 lines → decompose

A test file or POM exceeding 500 lines is a signal to split by domain or
component. One POM = one UI domain.

### 30. Diagnostics: MCP browser first, throwaway scripts second

When debugging UI, use the Playwright MCP browser
(`mcp__plugin_playwright_playwright__browser_*`) for interactive
iterations: navigate → snapshot → evaluate → click. This is faster than
the cycle of edit code → run pytest → wait → read screenshot.

Don't create throwaway scripts in `/tmp/` for debugging — MCP browser
covers most scenarios. On test failure — trace viewer
(`playwright show-trace`) + Allure screenshots.

### 31. No `except Exception` — use specific types

`except Exception` masks bugs. Use `json.JSONDecodeError`, `ValueError`,
`OSError`, `TypeError` etc. The only acceptable broad catch is
`except BaseException` in a `finally`-like pattern that re-raises.

### 32. No unnecessary `_` prefix on names

Underscore means "internal, don't import." Use it only for truly private
helpers (`_sanitize_json`, `_fail`). Module-level constants, classes, and
public functions are public: `Timeouts`, `LOCALE`, `build_timeouts()`.

### 33. Use `from http import HTTPStatus` for status codes

`expect_response(r).status(HTTPStatus.OK)`, not `.status(200)`.
httpx default timeout (10s) is built into the monkey-patch — don't pass
`timeout=` explicitly unless overriding to `TIMEOUTS.api_long`.

### 34. No bare `assert` in tests — use `should.*` or `expect_response`

Three assertion channels, zero bare `assert`:
- **Playwright UI**: `expect(locator, ErrMsg.x).to_be_visible()`
- **httpx API**: `expect_response(r).status(HTTPStatus.OK).json_eq("key", val)`
- **Everything else**: `should.be_equal(actual, expected, ErrMsg.x)`

```python
# bad
assert len(tree.people) == 3, f"expected 3, got {len(tree.people)}"

# good
from assertions.base import should
should.have_length(tree.people, 3, ErrMsg.count_mismatch)
```

Custom assertions live in `assertions/`:
- `base.py` — universal: `should.be_equal`, `contain`, `any_match`,
  `be_empty`, `playwright_status`, etc.
- `tree.py`, `auth.py`, `platform.py` — domain-specific wrappers.

All `what` parameters use `ErrMsg.*` — no inline strings.

### 35. Test = clean scenario, details in POM (zero low-level calls)

A test function must contain **zero** Playwright low-level calls:
no `.locator()`, `.click()`, `.fill()`, `.get_attribute()`,
`.wait_for_load_state()`, `.wait_for()` in test bodies. Everything
goes through POM methods with `step()` inside.

**Reference pattern** (account_ui_autotests `test_login_success`):
```python
# test reads like a scenario script — no Playwright API
def test_login_success(pages, auth_client) -> None:
    """DoQA #1619: вход в ЛК."""
    login = pages.navigate_to(LoginPage)
    expect(login.login_input, ErrMsg.form_not_visible).to_be_visible()

    login.login(identifier=username, password=password)  # scenario POM
    main = pages.create(MainPage)
    main.wait_for_page_load()                            # scenario POM
    expect(main.user_info, ErrMsg.login_success).to_be_visible()

    main.logout()                                         # scenario POM
    login = pages.create(LoginPage)
    expect(login.login_input, ErrMsg.logout_ok).to_be_visible()
```

**What belongs in test body:**
- `pages.navigate_to(POM)` / `pages.create(POM)` — POM creation
- `pom.scenario_method()` — one-word scenario actions (login, logout,
  open_profile, submit, upload)
- `expect(pom.locator, ErrMsg.x).to_*()` — UI assertions
- `should.*()` — non-UI assertions
- `expect_response(r).status().schema()` — API assertions

**What must NOT be in test body:**
- `page.locator(...)` — use POM property
- `locator.click()` / `.fill()` / `.check()` — wrap in POM method
- `page.wait_for_load_state(...)` — wrap in POM `wait_for_page_load()`
- `locator.get_attribute(...)` — wrap in POM method that returns value
- `page.on("request", ...)` — extract into conftest fixture
- `page.goto(...)` — use `pages.navigate_to(POM)`
- helpers as standalone functions (`auth_name(page)`) — make POM methods

**POM method rules:**
- Scenario-level name: `login()`, `logout()`, `open_editor()`,
  `expect_authed_state()`, `expect_guest_tabs()`
- Contains `with step("...")` inside
- Returns target POM for fluent chaining where applicable
- Never contains `assert` / `should.*` — only Playwright interactions

### 36. Standalone helpers → POM methods (migration complete)

UI-bound helper functions (`auth_name(page)`, `logout_link(page)`,
`wait_for_authed_shell(page)`, etc.) have been migrated to POM methods.
Deleted: `helpers/auth/auth_ui.py`, `helpers/auth/signup_helpers.py`,
`helpers/admin/gedcom_ui.py`, `helpers/enrichment/enrichment_ui.py`,
`helpers/tree/photos.py`, `helpers/tree/tree_navigation.py`.

The remaining `helpers/` files are API-level (httpx, not page-bound) or
cross-POM orchestration — they correctly stay in `helpers/`:
- `helpers/auth/session_helpers.py` — API-level session management
- `helpers/tree/tree_api.py` — API-level tree operations
- `helpers/tree/add_relative.py` — orchestration across multiple POMs
- `helpers/security/timing.py` — benchmarks (no Playwright)
- `helpers/ui/viewport.py` — browser context factory
- `helpers/ui/i18n_checks.py` — text utility

**Rule for new code:** if a function takes a `Page` or `Locator` and
performs UI interactions, it belongs on a POM class, not in `helpers/`.

### 37. Locators as `@property`, not `self.xxx =` in `__init__`

Playwright best practice: every locator is a `@property`, not an
`__init__` assignment. Lazy evaluation — re-queries DOM on each access.

```python
# bad — eager
def __init__(self, page):
    self.tab_map = page.locator('[data-tab="map"]')

# good — lazy @property
@property
def tab_map(self) -> Locator:
    return self.page.locator('[data-tab="map"]')
```

Reusable selector strings → module/class constants with `.format()`:
```python
_CS_TRIGGER = '[data-testid="custom-select-trigger"]'
_CS_OPTION = '[data-testid="custom-select-option"][data-value="{}"]'

def select_dropdown(self, field, value):
    custom = custom_select_for(self.page, field)
    custom.locator(_CS_TRIGGER).click()
    custom.locator(_CS_OPTION.format(value)).click()
```

**Zero inline locator strings in POM methods** — only in `@property`
return statements and `.format()` templates.

Methods that use locators reference `self.xxx` — the `@property`
evaluates lazily. No inline `self.page.locator(...)` in methods.

### 38. Docstrings — 1 sentence, TC-ID preserved

Module docstring: 1 line. Function docstring: 1 sentence + TC-ID.
No multi-paragraph explanations — the code and step names tell the story.

```python
"""AI search disabled flow — TC-N3, TC-N4, TC-N5."""  # module

def test_ai_button_disabled(...) -> None:
    """TC-N5: owner → profile → AI-кнопка disabled."""  # function
```

## Project structure

```
genealogy-e2e/
├── assertions/               # Custom assertion functions (should.* + domain wrappers)
│   ├── base.py               # should.be_equal, contain, any_match, be_empty, playwright_status
│   ├── tree.py, auth.py, platform.py  # domain-specific assertion wrappers
├── api/                      # routes.py (endpoint catalogue) + typed API wrappers
│   ├── routes.py             # module-level constants + builder functions
│   ├── person_api.py         # get_tree, create_person, patch_person, delete_person
│   ├── auth_api.py           # signup, verify_email, login, read_email_token
│   ├── mfa_api.py, enrichment_api.py, platform_api.py, relationship_api.py, site_api.py
├── config/                   # Pydantic settings, timeouts, test constants
│   ├── settings.py           # E2E_BACKEND_URL, locale, multiplier (Pydantic)
│   ├── timeouts.py           # TIMEOUTS dataclass (default, api_long, pw_*)
│   └── constants.py          # TestConfig, make_email, unique_email
├── framework/                # Response assertions, step decorator
│   ├── response.py           # expect_response() chain + ApiResponse wrapper
│   └── step.py               # Allure step() context manager
├── models/                   # Pydantic API contract models
│   ├── person.py, auth.py, mfa.py, enrichment.py, site.py, platform.py
├── fixtures/                 # Global pytest fixture plugins
│   ├── patch.py              # httpx monkey-patch (headers, default timeout) + Playwright expect
│   ├── server.py             # base_url, health gate, reset_state, install_mock_ai
│   ├── users.py              # AuthUser + signup_via_api / owner_user / superadmin_user
│   ├── clients.py            # tenant_client, auth_context_factory, owner_page
│   ├── page_factory.py       # PageFactory + pages/anon_pages fixtures
│   └── utils.py              # soft_check
├── pages/                    # Page Objects
│   ├── base.py               # BasePage, custom_select_for
│   ├── tree_page.py          # TreePage (orbit cards, tabs, search, open_center_profile)
│   ├── profile_panel.py      # ProfilePanel + open_editor_for
│   ├── person_editor.py      # PersonEditor
│   ├── add_relative_modal.py  # AddRelativeModal (dedup, link-mode, suggestions)
│   └── ...                   # login, signup, forgot, invite, owner, mfa, enrichment, etc.
├── helpers/                  # Domain helpers (API-level + cross-POM orchestration)
│   ├── auth/                 # session_helpers (API-level)
│   ├── tree/                 # tree_api (API-level), add_relative (cross-POM)
│   ├── security/             # timing (benchmarks)
│   └── ui/                   # viewport, i18n_checks
├── src/texts.py              # ErrMsg + locale-aware UI strings + t() resolver
├── test_data/                # Pure test data (no logic)
│   ├── gedcom/samples.py, media/jpeg.py, devices/descriptors.py, payloads/
├── tests/                    # ONLY test files + domain conftest.py
│   ├── auth/, tree/, platform/, admin/, security/, enrichment/, ui/
│   ├── test_smoke.py, test_regressions.py, test_api_coverage.py, test_api_invariants.py
├── conftest.py               # root: loads fixtures/* plugins + path→marker rule
├── scripts/check_drift.py    # Lints rules #5/#8/#10 against tests/ + pages/ + helpers/
├── pyproject.toml            # deps, pytest config, ruff, mypy
└── .github/workflows/pr-check.yml
```

Tests under `tests/<domain>/` automatically get `@pytest.mark.<domain>` via
`pytest_collection_modifyitems` in root `conftest.py`. Run a single domain
with `pytest -m auth`, `pytest -m security`, etc. — no per-file marker lines.

## Drift enforcement

`scripts/check_drift.py` lints `tests/`, `pages/`, and `helpers/`
against rules #5, #8, and #10 — runs in CI as a pre-pytest step. Catches
`page.wait_for_timeout()`, hardcoded `time.sleep(N)`, `timeout=N` literals,
raw `'/api/...'` strings, and raw `.json()` calls in test files (must use
`.schema(Model)` or typed helpers). Docstring-aware: skips triple-quoted
blocks. Whitelist legitimate uses with a trailing `# noqa: drift` comment.

## Running locally

Upstream `dev` is **PostgreSQL-only** since PR-B7 (commit `08cec28` "retire
SQLite production codepath" / `4155020` PG backend, cutover finalised
`d3836bd` 2026-05-14). The SQLite fallback is gone — the backend `RuntimeError`s
at startup without `DATABASE_URL`. The `/api/_test/*` endpoints are also
fail-closed behind a shared-secret token gate (commit `4a3f326`): without
`GENEALOGY_TEST_TOKEN` they return **503**, and the suite's autouse
`install_mock_ai`/`reset_state` fixtures error out the entire run.

```bash
# 0. Postgres. Docker engine on this machine is Colima — `colima start`
#    if down. `max_locks_per_transaction` is raised because the parallel
#    pass has no per-test reset → tenant schemas accumulate over a run,
#    and the session/inter-pass `/api/_test/reset` DROPs them all in ONE
#    transaction; at default 64 locks that hits "out of shared memory"
#    once a run has built up >~100 tenants. This is OUR test-container
#    config (not a product change). Recreate the container (not just
#    `docker restart`) to start from a clean volume.
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
# GENEALOGY_TRUST_FORWARDED_FOR=1 enables per-client synthetic
# X-Forwarded-For in the httpx patch — prevents 429s under xdist.

# 2. E2E setup
cd /path/to/genealogy-e2e
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# 3. Run suite — TWO passes (don't run in one shot: wedges at ~300 tenants)
export E2E_BACKEND_URL=http://127.0.0.1:8642 E2E_TIMEOUT_MULTIPLIER=1.5
pytest tests/ -m "not serial" -n 4 --dist load -v   # parallel
pytest tests/ -m serial -p no:xdist -v               # serial
```

Iterating on one area? `pytest -m auth -m "not serial" -n 4` etc.
Single file/test is fine non-parallel: `pytest tests/ui/test_x.py`
(it gets one session baseline reset; no per-test reset unless `serial`).

**Boot-env gotcha:** an incomplete env block produces false-positive
failures that masquerade as product regressions. Specifically:
`GENEALOGY_PUBLIC_URL` missing → `test_welcome_email` fails (template falls
back to the prod domain by design, `templates.py:38`); `WEBAUTHN_RP_ID` /
`WEBAUTHN_ORIGIN` missing → `test_platform_webauthn` register/complete `400`;
`GENEALOGY_TEST_TOKEN` missing → **every** test errors at setup (503 on
`/api/_test/install-mock-ai`); `GENEALOGY_DOCS_ENABLED` missing →
`/openapi.json` is 404 → `test_api_coverage` fails. Always boot with the
full block above before triaging failures as regressions.

## Key fixtures

- `owner_user` — fully signed-up + verified + onboarding-completed user via
  `signup_via_api()`. Email is UUID-suffixed (`owner-<hex8>@e2e.example.com`)
  for parallel isolation; default `full_name="Тестовый Пользователь"` (also
  becomes the tenant's `display_name` and the demo-self person's `name` —
  search/profile tests rely on this).
- `superadmin_user` — same flow but with `super@e2e.example.com` (matches
  `PLATFORM_SUPERADMIN_EMAILS` env).
- `owner_page` — Playwright `Page` inside an authenticated `BrowserContext`
  with the tenant's session cookies + `X-Tenant-Slug` header.
- `auth_context_factory` — factory for additional contexts (multiple users
  in one test).
- `signup_via_api` — factory if you need a custom user (different email/name).
- `soft_check` — yields `playwright.sync_api.expect` for `expect.soft(...)`
  multi-fact smoke blocks.
- `reset_state` (autouse, **serial pass only**) — calls `/api/_test/reset`
  between serial tests; parallel pass skips it (isolation via unique tenants).

## Backend test endpoints (upstream)

The suite assumes these exist in `genealogy/backend/app/_test_endpoints.py`,
gated by `IS_TESTING` **and** a shared-secret token (commit `4a3f326`,
`INV-TEST-001/002/003`). Every `/api/_test/*` call must carry
`X-Test-Token: <GENEALOGY_TEST_TOKEN>`; the suite injects it automatically
via the httpx monkey-patch in `fixtures/patch.py` using
`settings.test_token` from `config/settings.py` (env `E2E_TEST_TOKEN`). The backend
must boot with the **same** value in `GENEALOGY_TEST_TOKEN` or the endpoints
fail-closed (`503` no token → `401` no header → `403` wrong token):

| Endpoint                            | Purpose                                                 |
|-------------------------------------|---------------------------------------------------------|
| `POST /api/_test/reset`             | wipe DB rows + tenants/ + rate limits + MockSender + site_config |
| `POST /api/_test/reset-signup-rate` | only slowapi signup throttle (cheap, used between signups in one test) |
| `GET  /api/_test/last-email?to=...` | latest MockSender mail for a recipient                  |
| `POST /api/_test/install-mock-ai`   | swap enrichment.ai_client for the supplied fixture      |
| `POST /api/_test/uninstall-mock-ai` | restore real ai_client                                  |

If a contract changes upstream, update both repos in lockstep.

## Gotchas

- **`customSelect`** (`js/components/select.js`) wraps every native
  `<select>` and hides the original (`display:none`). Calling
  `.select_option()` on a `<select data-field="...">` fails with
  "element not visible" — use `PersonEditor.select_dropdown(field,
  value)`, which clicks the wrapper trigger and the option. Applies to
  `gender`, `branch`, `status`.
- **Per-viewport tests** build their own browser context — the default
  `conftest` viewport is 1440×900. Don't reuse `owner_page` for a
  mobile/responsive test; its viewport is fixed.

## Branching & commits

**Branch from `dev`, always** — `git switch -c <name> dev`. `dev` is the
integration branch; `main` lags it (promoting `dev → main` is a separate
explicit step). A branch cut from `main` misses the current layout and
fixtures and turns structurally unmergeable into `dev` — that has
already cost a near-lost rewrite.

- **One branch = one logical change = one merge into `dev`.** Don't run
  two branches on the same topic in parallel — they diverge, and the
  work gets duplicated or lost.
- Branch names describe the change, not the date: `chore/<topic>`,
  `fix/<topic>`, `test/<topic>`.
- Merge into `dev` with `--no-ff`, subject `merge: <branch> into dev` —
  keeps the branch boundary visible in history.
- Delete a branch once merged — locally **and** on `origin`.
- Commit messages: imperative subject; the body explains the *why* (the
  *what* is already in the diff). Add a `Co-Authored-By` trailer when
  Claude wrote the commit.

## Quick reference: where to put new code

| I need to add... | Put it in... |
|------------------|-------------|
| A new test | `tests/<domain>/test_<feature>.py` |
| A helper function | `helpers/<domain>/<topic>.py` |
| A Page Object | `pages/<page_name>.py` |
| A typed API wrapper | `api/<domain>_api.py` |
| An API route | `api/routes.py` (module-level constants + builders) |
| Test data (GEDCOM, JSON, bytes) | `test_data/<topic>/` |
| A global fixture | `fixtures/<topic>.py` |
| A domain fixture | `tests/<domain>/conftest.py` |
| A UI string / ErrMsg | `src/texts.py` |
| A custom assertion | `assertions/base.py` (universal) or `assertions/<domain>.py` |
| An env var | `config/settings.py` (Pydantic field) |

## When in doubt

- Is this test catching a real contract or just smoke? → If smoke, delete it.
- This test is red — commit it anyway? → No. Green or it doesn't exist
  (Rule 13). Fix the product, or record the bug and write the test after.
- Is the selector stable enough? → If you imagine the dev rewriting this
  component once, would the test still pass? If no, refactor.
- Is the timeout right? → Use the catalogue. If you want a different value,
  add a category, don't inline a number.

## Claude Code инструменты

### Hooks (`.claude/settings.json`)

PostToolUse hook автоматически запускает `ruff format` + `ruff check --fix`
после каждого редактирования `.py` файла.

### Агенты (`.claude/agents/`)

| Агент | Назначение |
|-------|-----------|
| `test-runner` | Запуск pytest, анализ падений, диагностика |

### Команды (`.claude/commands/`)

| Команда | Назначение |
|---------|-----------|
| `/verifier` | Верификация: drift-lint + ruff + import-check + правила |

### Скиллы (`.claude/skills/`)

| Скилл | Назначение |
|-------|-----------|
| `/gen-test` | Генерация нового теста по конвенциям (30 правил) |
| `/refactor` | Пошаговый рефакторинг: анализ → сводка → подтверждение → реализация |
