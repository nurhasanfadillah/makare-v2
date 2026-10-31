# Deployment Runbook

## Vercel projects

- `makare-v2` — root directory `frontend`; builds the React app and proxies `/api/*` to `https://makare-v2-api.vercel.app/api/*`.
- `makare-v2-api` — root directory `backend`; Python 3.12 FastAPI entrypoint is `server.py`.
- Production URLs: [web](https://makare-v2.vercel.app) and [API health](https://makare-v2-api.vercel.app/api/health).

## Production environment variables

Backend secrets/config are stored in Vercel Production only: `DATABASE_URL`, `DATABASE_SSL_MODE=require`, `APP_ENV=production`, `JWT_SECRET`, `CORS_ORIGINS`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, and `INITIAL_ADMIN_FULL_NAME`. The current owner-directed setup uses the existing Neon URL for runtime and migrations. Never print or commit their values.

Frontend production sets `REACT_APP_BACKEND_URL=https://makare-v2.vercel.app`; the browser then uses the same-origin `/api` rewrite. Local `.env` files must remain ignored.

## Deploy

From the repository root, deploy the backend first and then frontend:

```powershell
vercel --cwd backend --prod --yes
vercel --cwd frontend --prod --yes
```

The API lifespan checks/applies pending versioned migrations before serving requests. Current live ledger contains `001_initial_schema.sql`, `002_user_session_revocation.sql`, and `003_database_rate_limits.sql`. Do not edit applied SQL files; add a numbered migration.

## Credentials and rotation

- Local bootstrap and test credentials are held in ignored `backend/.env`; never commit it or paste values into logs/issues.
- Change the initial admin password through Settings before onboarding additional accounts; role changes and password resets revoke prior sessions.
- Rotate `JWT_SECRET` in Vercel Production and redeploy the API to invalidate all sessions. Set the same secret in the local ignored env only when local sessions should match.
- Admin can update the overtime kiosk PIN and rotate the kiosk token in Settings; rotating the token invalidates previous kiosk URLs.

## Recovery status

Migration and deployment rollback procedures have not yet been tested against a Neon branch. Before general production use, document a Neon backup/restore point, perform an isolated restore drill, verify the restored schema/data, and test application rollback without modifying the active database.
