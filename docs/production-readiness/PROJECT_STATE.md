# Project State

Last updated: 2026-10-31

## Current state

- Phase: deployed application has passed the recorded controlled-use acceptance suites. The exhaustive module audit and production release gate remain open.
- Frontend: [https://makare-v2.vercel.app](https://makare-v2.vercel.app)
- API: [https://makare-v2-api.vercel.app/api/health](https://makare-v2-api.vercel.app/api/health)
- Database: Neon PostgreSQL; migrations `001`, `002`, and `003_database_rate_limits.sql` are applied. Live readiness confirms the connection.
- Owner confirmed Neon rows are test data and authorized cleanup. Final verified counts: 2 app accounts, 4 departments, 1 settings row, 3 migrations, 1 cleanup audit event; 0 employees, attendance, overtime, notes, periods/snapshots, advances, adjustments, or rate-limit rows.
- All existing sessions were revoked during cleanup. Generated app credentials and database connection string remain only in ignored local `backend/.env` and encrypted Vercel variables.
- Vercel production is configured for Neon TLS, explicit CORS, JWT signing, and bootstrap; frontend API is same-origin.

## Verification evidence

- Backend isolated tests: 135 passed after FastAPI `0.162.0` / Starlette `1.10.0` upgrade and database-backed rate limiter.
- Live API acceptance: 16/16; payroll correction acceptance: 12/12; targeted attendance report/PDF regression passed. Those full suites passed before migration 003; after migration 003, live health/login/logout, kiosk page/search, operator 403, reports/PDF, and a 12-request concurrent login-limit check all passed.
- Concurrent login-limit check returned 8 failed-login responses and 4 HTTP 429 responses for 12 parallel attempts against one bucket. The bucket is stored in Neon and shared across serverless instances.
- Frontend production build succeeded locally and on Vercel after dependency fixes. Production root/deep link and CORS preflight returned 200; report PDFs returned valid `%PDF` content.
- Dependency audit: `pip-audit -r requirements.txt` found no known vulnerabilities; Yarn runtime dependency audit found none. Full JavaScript audit reports 3 low-severity `deepmerge` advisories in build/test tooling, with no patched version indicated.
- The source tree and changed diff pass secret scanning and `git diff --check`; legacy GitHub, Vercel, and Neon credentials were revoked/rotated and redacted before a successful push.

## Remaining before production-ready

- Complete the evidence trace for every P-01?P-42 product row; test coverage is not the same as a full module audit.
- Finish responsive/keyboard/screen-reader/contrast/touch-target review and resolve/accept the build-only `deepmerge` advisories.
- Run a Neon backup/restore drill on an isolated branch, record recovery time, and finish rollback/incident runbooks.
- Complete owner UAT for payroll examples, retention, and operational SOP.
- The last pushed source commit is `822ec95`; dependency and rate-limit changes described above are in the current local working tree and still need a source commit/push. CI is prepared locally but not pushed because the available GitHub OAuth authorization lacks `workflow` scope. Once GitHub authorization includes that scope, push the workflow and confirm its run.

## Business baseline

Delegated phase-one decisions are documented in `OWNER-WORKFLOW-DECISIONS.md`. The app is a clean initial deployment with no employee/payroll rows. It is ready for controlled onboarding, but is not certified for general production rollout until the remaining gates above pass.
