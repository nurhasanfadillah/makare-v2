# Final Audit Plan

The full audit starts only after the module inventory has no implementation gaps. Target environment is the owner-authorized Neon test dataset; never run synthetic writes against a production branch.

## Scope

1. Reconcile `MASTER-PLAN-TRACKER.md`, product specification, pages, API routes, schema, and migrations.
2. Exercise each role and direct API permission, IDOR/PII boundaries, session revocation, kiosk token/PIN expiry and replay.
3. Verify employee/settings/attendance/overtime workflows including WIB, overnight boundaries, breaks, tolerances, first-hour loss, incomplete sessions, and concurrent writes.
4. Reconcile payroll hourly/manual calculations, kasbon ledger, close idempotency/atomicity, snapshots, corrections, adjustment caps, and every PDF/report.
5. Check audit coverage/redaction, server error handling, rate limiting behind Vercel, CORS, input limits, and dependency vulnerabilities.
6. Review every screen for responsive layout, keyboard/focus behavior, labels, contrast, loading/empty/error states, and kiosk touch flow.
7. Verify Vercel/Neon configuration, CI, logs/readiness, backup/restore, recovery, onboarding, and UAT evidence.

## Method and gates

- Use isolated synthetic fixtures and cleanup; keep concurrent API suites serialized when sharing module state.
- Record environment/version, command or route, expected/actual result, evidence, risk, and follow-up for each item.
- Fix all critical/high findings and rerun targeted regression plus the relevant full suite.
- Complete backup/restore, business UAT, and owner approval before changing release state from controlled-use to production-ready.

## Current status

Deployment smoke and the listed API/unit suites passed. The exhaustive per-module audit has not been run. See `PROJECT_STATE.md` and `MASTER-PLAN-TRACKER.md` for open release gates.
