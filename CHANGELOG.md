# Changelog

## Unreleased — 2026-10-31

- Completed the current React/FastAPI/Neon application flows for employees, departments, attendance, kiosk, manual/hourly payroll, advances, closing, adjustments, notes, reports, and audit UI/API.
- Added immutable schema migrations and Neon startup integration; deployed the web and API projects to Vercel.
- Added same-origin API routing, production readiness endpoint, explicit Vercel environment configuration, and backend/frontend CI jobs.
- Corrected attendance report query typing and added targeted API/PDF regression acceptance.
- Hardened initial account credentials and session signing secret; actual values remain local/Vercel secrets only.
- Comprehensive security, accessibility, backup/restore, owner UAT, and final release gate remain open.
