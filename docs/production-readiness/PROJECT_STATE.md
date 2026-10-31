# Project State

Last updated: 2026-10-31

## Current state

- Phase: deployed application has passed the recorded controlled-use acceptance suites. The exhaustive module audit and production release gate remain open.
- Frontend (correct Vercel account, `nurhasanfadillah`): [https://makare-v2-zeta.vercel.app](https://makare-v2-zeta.vercel.app)
- API: [https://makare-v2-api-five.vercel.app/api/health](https://makare-v2-api-five.vercel.app/api/health)
- Database: Neon PostgreSQL; migrations `001`, `002`, and `003_database_rate_limits.sql` are applied. Live readiness confirms the connection.
- Owner confirmed Neon rows are test data and authorized cleanup. Final verified counts: 2 app accounts, 4 departments, 1 settings row, 3 migrations, 1 cleanup audit event; 0 employees, attendance, overtime, notes, periods/snapshots, advances, adjustments, or rate-limit rows.
- All existing sessions were revoked during cleanup. Generated app credentials and database connection string remain only in ignored local `backend/.env` and encrypted Vercel variables.
- Vercel production is configured for Neon TLS, explicit CORS, JWT signing, and bootstrap; frontend API requests use the same-origin `/api` rewrite to the API project.
- GitHub repository `nurhasanfadillah/makare-v2` branch `main` is connected to both Vercel projects in the correct account. Frontend root is `frontend`; API root is `backend`. A push to commit `104dd52` triggered both production deployments and GitHub CI.

## Verification evidence

- Backend isolated tests: 135 passed after FastAPI `0.162.0` / Starlette `1.10.0` upgrade and database-backed rate limiter.
- Live API acceptance: 16/16; payroll correction acceptance: 12/12; targeted attendance report/PDF regression passed. Those full suites passed before migration 003; after migration 003, live health/login/logout, kiosk page/search, operator 403, reports/PDF, and a 12-request concurrent login-limit check all passed.
- Concurrent login-limit check returned 8 failed-login responses and 4 HTTP 429 responses for 12 parallel attempts against one bucket. The bucket is stored in Neon and shared across serverless instances.
- Frontend production build succeeded locally and on Vercel after dependency fixes. New-account frontend root and its `/api/health` proxy return 200; API readiness returns `ready` and Neon reports `connected`. Production root/deep link and CORS preflight returned 200; report PDFs returned valid `%PDF` content.
- Dependency audit: `pip-audit -r requirements.txt` found no known vulnerabilities; Yarn runtime dependency audit found none. Full JavaScript audit reports 3 low-severity `deepmerge` advisories in build/test tooling, with no patched version indicated.
- The source tree and changed diff pass secret scanning and `git diff --check`; legacy GitHub, Vercel, and Neon credentials were revoked/rotated and redacted before a successful push.

## Remaining before production-ready

- Complete the evidence trace for every P-01?P-42 product row; test coverage is not the same as a full module audit.
- Finish responsive/keyboard/screen-reader/contrast/touch-target review and resolve/accept the build-only `deepmerge` advisories.
- Run a Neon backup/restore drill on an isolated branch, record recovery time, and finish rollback/incident runbooks.
- Complete owner UAT for payroll examples, retention, and operational SOP.
- Latest pushed source commit: `104dd52`. GitHub Actions run `41190163574` passed; Vercel Git integration produced ready production deployments for both projects. GitHub CLI OAuth is authorized with `workflow` scope and stored in the local keyring; the one-time PAT pasted into chat was revoked (HTTP 202).

## Business baseline

Delegated phase-one decisions are documented in `OWNER-WORKFLOW-DECISIONS.md`. The app is a clean initial deployment with no employee/payroll rows. It is ready for controlled onboarding, but is not certified for general production rollout until the remaining gates above pass.
