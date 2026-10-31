# Work Log

## 2026-10-31 — Neon, deployment, and acceptance

- Owner authorized implementation/deployment on local, Neon, Vercel, and GitHub; owner confirmed Neon records are test data.
- Read-only Neon discovery found test rows and no migration ledger. Applied the versioned migrations `001` and `002`; verified both ledger rows and preserved existing data.
- Deployed FastAPI and React as separate Vercel projects. Configured production-only Neon URL, TLS, CORS, JWT, and bootstrap variables without printing secret values.
- Rotated the test admin/operator credentials and JWT secret; credentials exist only in ignored `backend/.env`.
- Verified production login/RBAC, health/readiness, SPA deep links, CORS, attendance report/PDF, directory PDF, advance PDF, and payroll recap PDF.
- Fixed attendance PDF SQL parameter numbering after production logs showed `IndeterminateDatatypeError`; added an API/PDF regression test and confirmed both endpoints return 200 locally and in production.
- Fixed frontend production API URL by setting Vercel `REACT_APP_BACKEND_URL` to the same-origin app URL and excluding local `.env` files from deploy uploads.
- Acceptance: 133 isolated backend tests, 15 sequential end-to-end API tests, 12 payroll adjustment API tests, and 1 focused attendance report API/PDF test passed. The API suite requires `-n0` because module tests share ordered state.
- Removed test-created fixture periods, employees, departments, and accounts after acceptance. No production business data was handled.
- Remaining: full audit, dependency/security/a11y pass, backup/restore drill, owner UAT, GitHub push/CI verification, and final release decision.


## 2026-10-31 ? Empty-branch acceptance and cleanup

- Owner confirmed any existing records are test/trial data. Completed a transactional cleanup of all Neon employee, attendance, overtime, notes, PIN, payroll, advance, adjustment, temporary-account, TEST-department, and test audit rows. Preserved two application accounts, four departments, app settings, and the two applied migrations; reset settings to safe defaults and revoked all existing sessions. Final counts: employees/attendance/overtime/payroll/advances/adjustments = 0; users = 2; settings = 1; migrations = 2; cleanup audit event = 1.
- Frontend production build succeeded; isolated backend suite passed (133). `git diff --check` passed.
- Latest live API suite against the empty database: 15 passed, 1 failed because the RBAC projection test required at least one employee. Updated the assertion to accept an empty list and to validate privacy for all rows present; the full live suite still needs a rerun. A token emitted by pytest output was invalidated by incrementing all user session versions during cleanup.
- Release gates remain: rerun the corrected live acceptance, finish module-by-module audit, dependency/security/accessibility/mobile review, isolated Neon restore drill, owner UAT, and GitHub CI verification.


## 2026-10-31 ? Final live acceptance and credential response

- Corrected empty-installation RBAC acceptance, then reran the complete production API suite: 16 passed. Prepared a two-day historical payroll fixture, checked the expected Rp240.000 gross / Rp200.000 kasbon / Rp40.000 net snapshot, and ran payroll-correction API suite: 12 passed.
- Removed all synthetic acceptance rows in one transaction after tests. Final counts verified: 2 app users, 4 departments, 1 settings row, 2 migrations, 1 cleanup audit event; employee, attendance, overtime, notes, payroll, advance, and adjustment rows all 0. Default app settings restored and all sessions revoked.
- A credential scan found old Neon, GitHub, and Vercel credentials embedded in the supplied build prompt. Replaced them with placeholders before any successful push; GitHub accepted revocation (HTTP 202), Vercel accepted revocation (HTTP 200), and the Neon role password was rotated and synchronized to Vercel/local configuration. The first GitHub push was blocked by secret scanning; the identified credentials were removed/revoked, and the sanitized source then pushed successfully.
- Updated local development API target to port 8002 and CORS origins; restarted API with the rotated Neon URL. Local health, production health, admin login, and operator login returned success.
- GitHub commit `ded1e4b` is on main. CI workflow remains local because the available OAuth authorization lacks `workflow` scope. Comprehensive security, accessibility/mobile, backup/restore, UAT, and module-by-module release audit remain open.


## 2026-10-31 ? Shared rate limiter and final cleanup

- Replaced per-process API rate limits with atomic Neon-backed fixed-window buckets; migration `003_database_rate_limits.sql` is live. Parallel login smoke produced 8 expected failed-login responses and 4 rate-limit responses from 12 same-bucket attempts.
- Upgraded FastAPI/Starlette and patched frontend dependency resolutions; backend isolated suite: 135 passed; Python runtime audit and Yarn runtime audit are clean. The full Yarn audit reports three low `deepmerge` advisories in build/test tooling.
- Re-ran final transactional cleanup after the last live smoke. Verified: 2 users, 4 departments, 1 settings row, 3 migrations, 1 cleanup audit event; zero employees, attendance, overtime, employee notes/revisions, payroll periods/snapshots, advances, adjustments, or rate-limit buckets. Revoked all existing sessions.
- Updated deployment/readiness records. CI workflow remains local because GitHub authorization lacks the `workflow` scope. Latest implementation files are not yet committed/pushed. The comprehensive module trace, browser accessibility audit, isolated backup/restore drill, hosted CI run, and owner UAT remain release gates.


## 2026-10-31 ? GitHub workflow authorization and CI pass

- Authorized GitHub CLI OAuth with the `workflow` scope through the device flow. The credential is held in the local GitHub CLI keyring, not in the repository. The PAT pasted into chat was revoked via GitHub's credential-revocation endpoint (HTTP 202).
- Pushed `.github/workflows/ci.yml` and fixed its test dependency declaration (`pytest-xdist==3.8.0`, required by the repository's `pytest.ini`).
- GitHub Actions run `41188865261` completed successfully: backend isolated tests and `pip-audit`, plus Yarn runtime dependency audit and frontend production build.
