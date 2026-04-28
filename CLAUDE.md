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

### 8. Tests should be safe to run against a moving dev branch

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
│   ├── conftest.py           # uvicorn URL, signup_via_api, owner_page,
│   │                         # auth_context_factory, soft_check, reset_state
│   ├── messages.py           # locale-aware string catalogue + t() resolver
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
