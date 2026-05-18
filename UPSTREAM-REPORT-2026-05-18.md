# Upstream report — e2e run vs `Vadim-AM/Genealogy` dev @ `98f761a`

**Date:** 2026-05-18
**Suite:** `genealogy-e2e` @ `chore/adapt-dev-pg-token-cutover`
**Backend:** upstream `dev` (PostgreSQL-only, PR-B7), full canonical e2e env.

## TL;DR — no product regressions

The first run against the cutover looked alarming (326 setup-errors, then
21 "failures"), but after booting with the **complete** canonical env and
isolating each failure, **every failure was on the e2e side**: stale boot
config, suite over-fit to intentional upstream changes, or local-infra
overload. No upstream code change is required.

## ⚠️ Earlier "BUG-WAITLIST-001" — RETRACTED (not a regression)

An early run had `POST /api/waitlist/subscribe` → 500 with the
`waitlistsubscriber` table absent in the PG public schema, and it was
provisionally filed as a regression. **This did not reproduce on a healthy
backend.** On a clean boot `init_platform_db()` creates `waitlistsubscriber`
and both waitlist tests pass (verified XPASS → markers dropped per the
suite's Rule 6). The original 500 was an artifact of that first run: the
local backend was already in an overload death-spiral (DB unreachable,
see infra note) when the late-alphabet `tests/ui/test_waitlist.py` ran.
No upstream action.

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
