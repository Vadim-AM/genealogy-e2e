# Upstream report — e2e run vs `Vadim-AM/Genealogy` dev @ `98f761a`

**Date:** 2026-05-18
**Suite:** `genealogy-e2e` @ `chore/adapt-dev-pg-token-cutover`
**Backend:** upstream `dev` (PostgreSQL-only, PR-B7), full canonical e2e env.

## TL;DR — 1 real product regression (waitlist), now fixed upstream

The cutover surfaced one genuine PostgreSQL-only product bug
(BUG-WAITLIST-PG-001) plus a backend perf problem that made the full
suite unrunnable. Both were fixed upstream on `dev` by 2026-05-19
(`318a2e1`, `092f8d6`). Every *other* failure was e2e-side: stale boot
config, suite over-fit to intentional upstream changes, or local-infra
overload.

## ✅ BUG-WAITLIST-PG-001 — real, confirmed, fixed upstream

`POST /api/waitlist/subscribe` → 500: `WaitlistSubscriber` was never
registered with `init_platform_db()`, so `waitlistsubscriber` was absent
from the PG public schema (PR-B7 retired its legacy SQLite home).
**Correction of the record:** mid-session on 2026-05-18 this was
*wrongly retracted* — an XPASS on a re-run looked like "not reproducible"
but the table had been created as a side-effect of an earlier run, masking
the bug. The original diagnosis was correct. Upstream confirmed it
(`318a2e1 fix(waitlist): BUG-WAITLIST-PG-001`, review-followup `689fd64`)
and fixed it exactly as first described: `waitlist/__init__.py` now calls
`register_table_provider(_waitlist_table_provider)` so `init_platform_db()`
creates the table. e2e markers stay off (now correct because *fixed*, not
because "never a bug"); the hardened `test_wait_submit_email_success`
(Rule 1, pins HTTP 200) guards the regression going forward.

## ✅ Per-tenant alembic provisioning — perf bug, fixed upstream

Every `signup_via_api` ran a full `alembic_tenant upgrade` into the new
schema; ~300 of those serialized and exhausted the backend connection
pool, wedging it mid-suite (looked like mass `ReadTimeout` setup-errors).
Fixed upstream `092f8d6 perf(provision): create_all + stamp head instead
of alembic runner per signup` — the exact change recommended in the
2026-05-18 root-cause analysis. The full local suite is runnable again.

## ⚙️ Infra note (e2e-side, already fixed here)

Upstream `dev` is PostgreSQL-only (PR-B7). The e2e `pr-check.yml` and
`CLAUDE.md` were pre-cutover (SQLite paths, no `DATABASE_URL`, no
`GENEALOGY_TEST_TOKEN`) — they were updated this session to mirror upstream
`ci.yml`'s `pytest_postgres` service. Flagging only so anyone booting the
backend the old way knows it now `RuntimeError`s without `DATABASE_URL`.

Local caveat (not an upstream bug): a single local PG container cannot
sustain the full suite — every `signup_via_api` provisions a tenant schema
+ runs the `0001_initial_pg` alembic migration; ~300 of those saturate a
laptop-class Colima VM and the backend falls over mid-run. CI is fine
(ephemeral per-job PG). Locally: run in small batches against a freshly
booted backend.

## ✅ Intentional upstream changes the e2e suite adapted to (not bugs)

| upstream change | commit | e2e adaptation |
|---|---|---|
| admin_password + admin login UI removed | `dac8535` v2-Phase2 | retired `test_admin_ui` ×4 + `admin_page` POM; dropped `/api/admin/invites` from the anon-401 parametrize |
| invite-accept = magic-link (invite+email+unauth → backend creates passwordless user) + email-match 403 | v2-Phase1 H5 | rewrote `test_invite_accept` ×2 to the new contract + added a magic-link auto-accept test |
| AI `output_schema.json` restructured (`archive_suggestions` required, `archives` gone, new top-level shape) | — | rewrote `tests/fixtures/ai_responses.json`; pinned the canonical field name |
| `/api/health` adds `dialect` + `active_tenants` | PR-B7 | assert behaviour (`status == ok`), not exact dict (Rule 13) |
| platform dashboard CSP `script-src 'self'` (no unsafe-eval) | — | feature-flags tests: replaced `wait_for_function("<string>")` (CSP-blocked eval) with a driver-level locator assertion |
| PG slower than retired in-proc SQLite → widened a guest→authed render race | PR-B7 | added `wait_for_authed_shell()` so tab tests wait for `/api/tree`+render before clicking |

## ✅ Boot-env false positives (resolved by the full canonical env)

`test_welcome_email` (`GENEALOGY_PUBLIC_URL`), `test_platform_webauthn` ×2
(`WEBAUTHN_RP_ID`/`WEBAUTHN_ORIGIN`), `test_owner_settings_save_persists`
(state flake), `test_mobile_smoke` signup (per-device context missed the
cookie-consent pre-seed — fixed in the suite). All pass with the documented
env.

---

## 2026-05-19 — parallelization: NO upstream change. (Earlier root-cause here was WRONG — retracted.)

Context: e2e suite split into a parallel pass (tenant-scoped, no per-test
global reset) + a serial pass. Verified — serial 81/81 green; parallel
runs in **41 s vs the old 36 min**, xdist healthy, no wedge.

**Retraction.** An earlier draft of this section claimed the
`/api/account/login` 429 cascade was an upstream bug (programmatic
limiter "not honouring its own docstring") and asked for a one-line
product change. **That root-cause was wrong** — a hypothesis presented
as fact, the exact thing Rule 1 forbids. The authoritative contract is
the *function* docstring of `check_rate_limit`/`is_within_rate_limit`
(`rate_limiting.py:~111`): *"Не уважает limiter.enabled. Тесты, которые
проверяют 429-behavior, должны работать против programmatic check."* The
login throttle is **intentionally, by documented invariant, ON in test
mode** so brute-force protection stays testable. The "Test mode:
отключаем slowapi" comment applies to the slowapi *decorator* (signup),
not to login. The product is correct; the guard that blocked the patch
was right on the merits.

**Actual cause — e2e infra, not the product.** Parallel xdist workers
all hit the backend from one IP (`127.0.0.1`) → they share the
`login:<ip>` bucket → the honest 10/60 s limit fires (~240 logins from
`signup_via_api` in 41 s, one window). The old per-test global reset was
incidentally clearing `_buckets` every test, masking this.

**Fix — e2e-side only, product untouched, throttle stays real
(Option A).** Boot the e2e *target* with `GENEALOGY_TRUST_FORWARDED_FOR=1`
(verified real env, `security_utils.py:22`; `client_ip()` then reads
`X-Real-IP`→`X-Forwarded-For` — this is a config flag of *our* test
instance, the same one prod uses behind Caddy, not a code change) and
inject a **per-test / per-httpx-client** synthetic `X-Forwarded-For`
(seam already exists: the `httpx.Client.request` monkey-patch in
`tests/_fixtures/patch.py`). Each logical client → its own IP → its own
bucket → the 10/min throttle stays genuine *per identity* (a
single-identity brute-force-style test still gets 429), suite green.
Keying must be per-test/per-client, **not per-worker**: the parallel run
is 41 s ⊂ one 60 s window with ~240 logins; per-worker (~8) ≈ 30
logins/IP > 10 → would still 429.

Option B (move login-heavy tests to the serial bucket) does **not** fit
this suite: a login is universal (every parallel test → `owner_user` /
`signup_via_api` → exactly one login), so "serialize login-heavy" ≈
serialize everything, defeating the parallelization.

The earlier `RATE_LIMIT_DISABLED=1` added to CLAUDE.md/pr-check.yml is
**replaced** by `GENEALOGY_TRUST_FORWARDED_FOR=1` + the per-client XFF
injection. No upstream/product ask.

### Final verified outcome (parallelization)

Both passes deterministically CLEAN, **no product change**:
- parallel `-m "not serial" -n 4`: **210 passed, 2 xfailed, 0 fail,
  0 error, 0 xpass, ~91 s** (was a 36-min run that didn't finish).
- serial `-m serial -p no:xdist`: **112 passed, 0 fail, ~95 s**.
- Full suite ≈ **3 min** two-pass, deterministically clean, vs old 36 min.

Worker count is bounded **`-n 4`, not `-n auto`**: `auto` = one worker
per logical CPU; on a high-core host that runs ~10+ concurrent Chromium
against the one shared backend → resource contention that flakes a
*different random light test each run* (`signup_flow`, etc. — verified
non-deterministic). Not bad tests, not a product bug: host
over-subscription. `-n 4` is stable on 2-core CI and locally.

The 2 xfailed are `FEATURE-PARENT-SEARCH-001` only — a deterministic,
documented spec-xfail for an un-built feature (never flips; Rule-1 clean).

**Retraction (again, same discipline):** the `test_owner_settings_save_persists`
"site_config not persisted under concurrent load" was briefly marked
`xfail` as a suspected `BUG-MT-001` reopen. Reading the code path proved
it a **test bug, not a product bug**: `OwnerPage.update_settings()` opens
the settings tab first (a *GET* /api/site/config to populate the form)
then clicks save (the write); the test's
`expect_response("**/api/site/config")` matched that **GET**, so it never
awaited the write and raced it — invisible in isolation, "not persisted"
only under load. Fixed by matching a non-GET /api/site/config response;
marker removed; product exonerated. No `BUG-MT-001`. Lesson (third time):
read the code on the request path before attributing a load-only failure
to the product.

Parallel-load-flaky heavy UI/GEDCOM-import files (`test_mobile_smoke`,
`test_gedcom_import_deep`, `test_logout`) were moved to the serial lane
(non-deterministic across worker counts = test-robustness gap, green
single-worker; fully run+asserted there — not silenced; TODO-harden with
semantic settle-waits). PG test container needs
`max_locks_per_transaction=4096` (no per-test reset → tenants accumulate
→ the bulk `DROP SCHEMA` must fit) — our container config, not a product
change. **Net: the dirty-parallel model found no product bug this round;
every residual was e2e-side and is fixed or correctly lane-placed.**
