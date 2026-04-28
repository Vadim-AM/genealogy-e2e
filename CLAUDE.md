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

**Anti-patterns that make tests pass-by-default:**
- `pytest.skip` as fallback (`if r.status_code == 404: pytest.skip(...)`).
  If a core endpoint is missing, that's a regression — fail loud, don't skip.
  Skip is for "this scenario doesn't apply here" (different config), never
  for "the feature isn't working".
- Runtime `pytest.xfail(...)` inside test body. Always passes (XPASS or
  XFAIL — never FAIL). Use `@pytest.mark.xfail(strict=False)` *outside* the
  function with a concrete bug reference.
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
- Running `pytest.xfail(reason=...)` at runtime when a check fails — this
  promotes the failure to expected without external review.

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
`tests/messages.py`. Switching to English will be one file edit instead
of a ~30% test rewrite.

When you need to add a new visible string:
1. Pick the right class (`Buttons`, `Links`, `Brand`, `Invite`, `PII`,
   `TestData`, `FamilyGroups`, ...).
2. Use `dict[locale, str]` if the value translates, plain `str` if it
   doesn't (proper noun like "ЦАМО", structural like "0 HEAD").
3. Reference via `t(Buttons.SAVE)` — never inline.

When extending the catalogue, add an `en` translation even if there's no
English locale yet — costs one minute, prevents future hunt.

### 5. No hardcoded timeouts

Every timeout (httpx, polling loops, Playwright `expect()`) routes through
`tests/timeouts.py`. Slow CI/Docker bumps everything via
`E2E_TIMEOUT_MULTIPLIER=1.5` — single env var.

**Categories** (pick the smallest one that fits):
- `api_short` (5s) — fire-and-forget admin/test endpoints.
- `api_request` (10s) — typical product API call.
- `api_long` (30s) — exports / bulk operations.
- `health_gate` (30s) — subprocess /api/health bootstrap.
- `enrichment_poll` (30s) — background job completion.

Playwright's `expect()` default auto-wait is fine — don't add explicit
`timeout=10_000` in tests; bumping the global multiplier covers it.

**Never** use `page.wait_for_timeout(N)` (fixed sleep — anti-pattern).
Use `page.expect_response("...")`, `page.wait_for_url(...)`, or
`expect(loc).to_be_visible()` (auto-wait).

### 6. Document new bugs the suite finds

When a test fails because the suite caught a real product issue:
1. Mark `@pytest.mark.xfail(strict=False, reason="BUG-XXX-N: <one-line cause>. <hint where to fix>.")`
   so CI stays clean while the bug is open.
2. Use a fresh `BUG-XXX-N` ID — check upstream `docs/test-plan.md` to avoid
   collisions (e.g., upstream's `BUG-EDITOR-001` was about adaptive grid;
   ours about empty `branch=""` on save → `BUG-EDITOR-002`).
3. When the upstream fix lands, the test goes XPASS — drop the marker
   immediately (XPASS is the signal to convert it back to a regression).

### 7. Linear product code knowledge: read JS/Python before guessing

Before writing a POM:
- Read `js/components/<name>.js` for selectors. Real classes/IDs/`onclick`
  payloads beat guesses.
- Read `backend/app/<area>.py` for response schema (canonical field names).
  Pin one, don't accept-any-of.

POMs with `TODO Wave N: verify against ...` are a code smell — they are
selectors written without the source. Convert before merging.

### 8. No raw `httpx.*` calls — go through `tenant_client(user)`

Each test was repeating `cookies=user.cookies, headers={"X-Tenant-Slug":
user.slug}, timeout=TIMEOUTS.api_request` on every API call. Encapsulated
in `tenant_client(user)` factory in conftest:

```python
def test_x(owner_user, tenant_client):
    api = tenant_client(owner_user)
    r = api.get(API.TREE)
    api.patch(API.person(pid), json={"summary": "..."})
```

Per-request override (`api.post(..., timeout=TIMEOUTS.api_long)`) is fine
when `enrichment` job needs longer. Multiple users in one test → multiple
factory calls (each closed automatically on teardown).

**Anonymous calls** (lending, public health) — pass `httpx.get(f"{base_url}{API.HEALTH}")`
directly; no client needed. Or use a top-level `httpx.Client(base_url=base_url)`.

### 9. No raw URL strings — go through `tests/api_paths.py::API`

```python
# bad
api.get(f"/api/people/{pid}")
# good
api.get(API.person(pid))
```

When backend renames an endpoint — one place to update, IDE autocomplete,
contract is visible in code.

### 10. No raw credentials/tokens — go through `tests/constants.py::TestConfig`

```python
# bad
password = "test_password_8plus"
# good
password = TestConfig.DEFAULT_PASSWORD

# bad
email = f"label@e2e.example.com"
# good
from tests.constants import make_email, unique_email
email = make_email("label")            # deterministic
email = unique_email("waitlist1")      # uuid-suffixed (when reset_state doesn't wipe target table)
```

### 11. User creation — through factories in conftest, not inline

If your test needs:
- a verified, logged-in user → `owner_user` (default) or `signup_via_api(email=...)`.
- a signed-up but **un**verified user → `signup_unverified(email=...)`.
- a second login of an existing user → `login_existing(email)`.
- the latest token from MockSender (verify, reset) → `read_email_token(email)`.
- an invite issued by owner → `create_invite(owner, role=..., name=...)`.
- accepting that invite → `accept_invite(token, cookies=...)`.
- AI consent stamp on owner → `grant_ai_consent(user)`.

**Never** inline `c.post(API.SIGNUP, ...) → c.post(API.VERIFY_EMAIL, ...) → c.post(API.LOGIN, ...)` —
that's 8+ lines of plumbing per test, and changes in the auth flow ripple through every test.

### 12. xfail markers are concrete

`@pytest.mark.xfail(strict=False, reason="INV-XXX-N: <one-line cause>. <where to fix>.")`.

When XPASS → drop marker, replace with a one-liner in docstring:
`"Was xfail until upstream commit `<sha>` (`<commit subject>`)."`. This
gives future readers the regression history without `git blame`.

### 13. Tests should be safe to run against a moving dev branch

The product main branch can change daily. Tests must be:
- Robust to UI implementation changes (semantic locators).
- Decoupled from arbitrary copy edits (use catalogue, substring on
  meaningful keywords like "владелец", not whole sentences).
- Failing **for the right reason** when product breaks the contract,
  not for an unrelated cosmetic refactor.

If a test fails after a non-functional product change, the test was
over-fitting to implementation. Refactor it to assert behaviour, not
markup.

## Project structure

```
genealogy-e2e/
├── tests/
│   ├── conftest.py           # fixtures: signup_*, login_*, tenant_client,
│   │                         # owner_page, grant_ai_consent, reset_state, etc.
│   ├── api_paths.py          # API.{TREE, person(pid), enrich(pid), ...}
│   ├── constants.py          # TestConfig.{DEFAULT_PASSWORD, EMAIL_DOMAIN, ...}
│   ├── messages.py           # locale-aware UI string catalogue + t() resolver
│   ├── timeouts.py           # TIMEOUTS dataclass + E2E_TIMEOUT_MULTIPLIER
│   ├── pages/                # Page Objects (one per page/component)
│   │   ├── base.py
│   │   ├── tree_page.py, signup_page.py, login_page.py, ...
│   │   └── profile_panel.py, person_editor.py, enrichment_modal.py
│   ├── fixtures/
│   │   └── ai_responses.json # mock-AI fixture installed via /api/_test/install-mock-ai
│   └── test_*.py             # one file per feature area
├── docker/Dockerfile.e2e     # CI-friendly image
├── docker-compose.yml        # backend + e2e wiring
├── .github/workflows/
│   └── pr-check.yml          # checkout both repos, boot uvicorn, run pytest
├── pytest.ini                # pythonpath=., markers=smoke|regression|slow
└── requirements.txt          # playwright>=1.45, pytest-playwright>=0.4.4
```

## Running locally

```bash
# 1. Boot test-instrumented backend (in upstream repo):
cd /path/to/genealogy/backend
GENEALOGY_TESTING=1 GENEALOGY_ADMIN_PASSWORD=test_admin_password \
  EMAIL_PROVIDER=mock FREE_SIGNUP_LIMIT=1000 \
  PLATFORM_SUPERADMIN_EMAILS=super@e2e.example.com \
  uvicorn app.main:app --port 8642 &

# 2. Run suite:
cd /path/to/genealogy-e2e
E2E_BACKEND_URL=http://127.0.0.1:8642 pytest tests/ -v
```

## Key fixtures

- `owner_user` — fully signed-up + verified + onboarding-completed user via
  `signup_via_api()`. Default email `owner@e2e.example.com`, default
  `full_name="Тестовый Пользователь"` (also becomes the tenant's
  `display_name` and the demo-self person's `name` — search/profile tests
  rely on this).
- `superadmin_user` — same flow but with `super@e2e.example.com` (matches
  `PLATFORM_SUPERADMIN_EMAILS` env).
- `owner_page` — Playwright `Page` inside an authenticated `BrowserContext`
  with the tenant's session cookies + `X-Tenant-Slug` header.
- `auth_context_factory` — factory for additional contexts (multiple users
  in one test).
- `signup_via_api` — factory if you need a custom user (different email/name).
- `soft_check` — yields `playwright.sync_api.expect` for `expect.soft(...)`
  multi-fact smoke blocks.
- `reset_state` (autouse) — calls `/api/_test/reset` between every test:
  wipes platform DB rows, tenants/, MockSender, slowapi rate-limit, site_config.

## Backend test endpoints (upstream)

The suite assumes these exist in `genealogy/backend/app/_test_endpoints.py`,
gated by `IS_TESTING`:

| Endpoint                            | Purpose                                                 |
|-------------------------------------|---------------------------------------------------------|
| `POST /api/_test/reset`             | wipe DB rows + tenants/ + rate limits + MockSender + site_config |
| `POST /api/_test/reset-signup-rate` | only slowapi signup throttle (cheap, used between signups in one test) |
| `GET  /api/_test/last-email?to=...` | latest MockSender mail for a recipient                  |
| `POST /api/_test/install-mock-ai`   | swap enrichment.ai_client for the supplied fixture      |
| `POST /api/_test/uninstall-mock-ai` | restore real ai_client                                  |

If a contract changes upstream, update both repos in lockstep.

## Run summary (28.04.2026 late night, post-Wave 9)

`E2E_BACKEND_URL=http://127.0.0.1:8645 pytest tests/` against fresh
upstream dev (`106a1c4`) → **102 passed, 21 xfailed in 80s**.

Wave 9 added 8 domain-invariant + auth-security regressions:

- `test_domain_invariants.py` — 6 tests covering INV-DOMAIN-001..005
  + INV-DATE-001:
  - death year before birth year (PATCH)
  - parent.birth after child.birth (PATCH)
  - garbage birth='foobar' accepted as date (PATCH)
  - 3rd parent relationship accepted (POST)
  - parent-cycle (A↔B) accepted (POST)
  - branch=demo on root subject accepted (PATCH)
- `test_session_invalidation.py` — INV-AUTH-001 stolen session NOT
  invalidated after password reset (P0 — defeats security purpose
  of reset).
- `test_concurrency.py` — INV-EDIT-001 GET /api/people/{id} returns
  ETag for optimistic concurrency (otherwise lost-update silent).

Out of e2e scope (delegated to backend pytest):
- INV-TEST-001/002/003 (`/api/_test/*` open anonymously) — the suite
  itself depends on anonymous access to those endpoints. Fix needs
  coordinated change in both repos; backend can validate via
  IS_TESTING-disabled run.
- INV-AI-003 (failed jobs don't decrement quota) — needs controllable
  AI-failure mock; marginal value for e2e.
- INV-PERM-002 (auth_v2 vs admin gate) — unclear expected contract,
  product decision pending.

## Run summary (28.04.2026 night, post-Wave 8)

`E2E_BACKEND_URL=http://127.0.0.1:8645 pytest tests/` against fresh
upstream dev (`106a1c4`) → **102 passed, 13 xfailed in 80s**.

Wave 8 added 13 new test files/cases covering security, a11y, privacy,
i18n, form contracts, and ux regressions surfaced by the QA funnel run:

- `test_security_timing.py` — TC-SEC-3/4 timing-based account
  enumeration on signup (≈9× ratio) and login (≈14×). Median p50
  ratio threshold = 3.0× (xfail until equal-work fix).
- `test_privacy_static.py` — TC-PRIVACY-1 PII regression-trail on
  `/js/constants.js` and inline scripts in `/`. Closed by
  `de7f53a` ("BUG-COPY-001 finalize") in Run 2; passing tests guard
  against regression.
- `test_a11y.py` — A-SU-3 (`aria-invalid` not set on validation
  fail) + A-SU-4 (honeypot lacks `aria-hidden="true"`).
- `test_form_method.py` — TC-FORM-1 signup/login/reset-password
  forms have explicit `method="post"` (not default GET → leaks
  passwords to query string).
- `test_login_unverified.py` — TC-VERIFY-1 / BUG-LG-001 unverified
  login returns specific `verification_required` discriminator,
  not generic English «Invalid email or password».
- `test_welcome_email.py` — TC-COPY-3 / BUG-COPY-003 welcome-email
  domain comes from `GENEALOGY_PUBLIC_URL`, not hardcoded
  `nasharodoslovnaya.ru`.
- `test_security.py` (extended) — TC-CSP-2 / BUG-CSP-001 served HTML
  has no inline `on*=` event-handler attributes (CSP header alone
  is not enough — index.html still ships `onload="this.media='all'"`
  on the fonts.css link, breaking font swap).
- `test_i18n.py` — BUG-i18N-001 backend error detail in Russian for
  RU-product (login wrong creds + signup short password).
- `test_profile_edit.py` (extended) — TC-EDITOR-3 / X-PR-3 (BUG-UX-002
  reopen) Delete button hidden in editor for the root subject.

Notes:
- TC-FORGOT-1 (forgot-password email bombing per-email rate-limit)
  **not automated** in Wave 8: requires a backend test endpoint to
  count emails sent (current `/api/_test/last-email` returns only
  the latest one). Sketched in CLAUDE.md backlog.
- All product-bug tests are `@pytest.mark.xfail(strict=False, ...)`
  with concrete BUG-XXX-N IDs and fix-hints, per Rule 6.

## Run summary (28.04.2026 evening, after upstream xfail-cleanup wave)

`E2E_BACKEND_URL=http://127.0.0.1:8643 pytest tests/` against fresh
upstream dev (`d0e878b`) → **99 passed, 0 xfailed in 42s**.

All 5 xfails closed by 4 upstream commits on dev:
- `731fbc9` BUG-AUTH-001 reopen → `test_deep_link.*` ×2 → regular tests.
- `fc2849e` BUG-COPY-001 → `test_landing_no_personal_owner_data` → regular.
- `7e39c57` BUG-EDITOR-002 → `test_owner_edits_demo_self_summary_through_ui` → regular.
- `8146ed5` BUG-DB-002 ep.4 → `test_enrichment_endpoint_returns_mocked_output` → regular.

xfail markers stripped from all four files. Suite now has zero xfails;
the next product bug we catch will get a fresh marker per Rule 6.

## Run summary (28.04.2026 afternoon, post-Wave 7 + harden pass)

`E2E_BACKEND_URL=http://127.0.0.1:8642 pytest tests/` → **94 passed, 5 xfailed in 82s**.

Wave 7 added (no overlap with prior waves):
- `test_site_config.py` — TC-MT-1 read/write/anon isolation (extends the
  one-line `test_bug_mt_001_*` regression with the full 8-step scenario).
- `test_enrichment_consent.py` — TC-AI-1 GDPR/152-FZ consent confirm:
  positive (text contains Anthropic + privacy reference) + negative
  (decline blocks POST `/api/enrich/`).
- `test_responsive.py` — TC-RESPONSIVE-1 viewport tests: 375×812 signup
  (no h-scroll, eye-toggle visible, agree-row fits) + 768×1024 owner
  (5 tabs visible).

Per-viewport tests use their own browser context (default conftest is
1440×900). Don't try to reuse `owner_page` — viewport is fixed there.

### Harden pass (28.04, evening)

Audit existing tests for smoke / antipatterns from Rule 1:
- **`test_enrichment_history_endpoint_after_run`** — was xfailed under the
  same reason as the `actor_kind` bug, but history endpoint reads
  `EnrichmentCache` not `EnrichmentJob` and never depended on that
  column. The actual failure was an outdated assertion: backend returns
  `{items: [...]}`, test asserted `isinstance(_, list)`. Fixed shape +
  dropped xfail → renamed `test_enrichment_history_endpoint_returns_items_dict`.
- **`test_logout::test_logout_clears_session`** — had a `pytest.skip`
  fallback when logout endpoint returned 404. Rule 1: a missing core
  endpoint is a regression, not «scenario doesn't apply». Removed
  fallback; assert is now hard-pinned to 200/204.
- **`test_waitlist::test_wait_duplicate_email_does_not_5xx`** — was a
  `status < 500` smoke. Backend contract is precise: 200 + JSON
  `{status: "ok"}` first, `{status: "already_subscribed"}` after.
  Pinned both. Renamed to `test_wait_duplicate_email_idempotent_status_field`.
  Side-finding: `_test/reset` does NOT wipe waitlist (it lives in legacy
  `genealogy.db`, not platform.db). Tests now use `_unique_email(label)`
  to avoid stale-row poisoning between runs.
- **`test_profile_edit::test_delete_button_invokes_confirm_dialog`** —
  had `"необратим" in msg or "необратимо" in msg`. Substring overlap
  (необратим ⊂ необратимо), the `or` was decorative. Simplified.
- **`test_enrichment_consent::test_first_enrich_click_*`** — same
  decorative `or` between `msg.lower()` and `msg`. Simplified to
  `in msg.lower()` only.

## Open xfails

None as of 28.04.2026 evening. Suite is fully green against
upstream `dev` at `d0e878b`.

When the suite catches a new product bug, mark it per Rule 6
(`@pytest.mark.xfail(strict=False, reason="BUG-XXX-N: ...")`)
so CI stays clean while the fix is open. When the fix lands →
XPASS → drop the marker.

### Notable fix landed in dev (28.04 merge)

- `customSelect` (new `js/components/select.js`) wraps every native `<select>` and hides the original with `display:none`. Tests that did `.select_option(value)` on `<select data-field="...">` would fail with "element not visible" — POM `PersonEditor.select_dropdown(field, value)` clicks the wrapper trigger and option instead. Use that for any `gender`, `branch`, `status` interaction.

## Commit style

- One logical wave per branch (`chore/wave-N-<topic>`).
- Branch names describe the change, not the date.
- Commit messages: imperative subject, body explains the *why* (especially
  for sanitize/refactor commits where the *what* is mechanical).
- Co-Authored-By trailer when Claude wrote the commit.

## When in doubt

- Is this test catching a real contract or just smoke? → If smoke, delete it.
- Should I make this `xfail` or fail? → Fail unless there's a known upstream
  bug ticket. Skip is almost never right.
- Is the selector stable enough? → If you imagine the dev rewriting this
  component once, would the test still pass? If no, refactor.
- Is the timeout right? → Use the catalogue. If you want a different value,
  add a category, don't inline a number.
