# Project State

Last updated: 2026-10-31

## Current state

- Phase: feature implementation is present; production integration and controlled-use smoke checks are complete. The comprehensive audit and release gate are still open.
- Frontend: [https://makare-v2.vercel.app](https://makare-v2.vercel.app)
- API: [https://makare-v2-api.vercel.app/api/health](https://makare-v2-api.vercel.app/api/health)
- Database: Neon PostgreSQL; migrations `001_initial_schema.sql` and `002_user_session_revocation.sql` are applied and the live health endpoint reports the DB connected.
- The owner confirmed all existing Neon rows are test data and authorized their cleanup. Neon now has zero employees, attendance, overtime, notes, advances, payroll periods/snapshots, and payroll adjustments; two application accounts, four departments, baseline settings, two migrations, and one cleanup audit event remain. All existing login sessions were revoked during cleanup.
- Generated admin/operator credentials and bootstrap values are stored only in the ignored local `backend/.env`; do not commit, display, or copy them into docs.
- Vercel production variables are configured for Neon TLS, production CORS, JWT signing, and first-admin bootstrap. Frontend production uses the same-origin API rewrite.

## Verification evidence

- Frontend production build: successful on Vercel; root and SPA deep link returned HTTP 200.
- Live API: health/readiness returned `ready` with Neon connected; login worked for admin and operator; operator was denied admin settings (403).
- Live report/PDF smoke: attendance JSON/PDF, employee directory PDF, advance report PDF, payroll recap PDF returned 200 with valid PDF headers.
- Backend isolated suite: 133 passed; sequential API acceptance: 15 passed; payroll adjustment API suite: 12 passed; targeted attendance report API/PDF regression: 1 passed.
- CORS preflight for the deployed frontend returned 200 with the exact frontend origin.
- Production bundle no longer contains localhost API configuration.

## Remaining before production-ready

- Reconcile every product row in `MASTER-PLAN-TRACKER.md` against code and acceptance evidence; several modules remain unverified.
- Run full security, dependency, accessibility/mobile, and cross-module audit; fix and retest findings.
- Execute and document Neon backup/restore recovery on an isolated branch, review provider retention, and finish rollback/incident runbooks.
- Run owner UAT and approve payroll/business examples, retention, and operational SOP.
- Push reviewed source to GitHub and confirm the new CI workflow runs successfully; Vercel deployments so far were CLI deployments from this workspace.

## Locked baseline

Business assumptions delegated by the owner are in `OWNER-WORKFLOW-DECISIONS.md`. The application is currently a clean initial deployment with no employee/payroll data, but is not yet certified production-ready under the release gate.
