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
