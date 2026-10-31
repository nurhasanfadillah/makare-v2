import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from core import get_migration_pool, close_pool
from config import parse_cors_origins
from schema import init_db
import security
import routes_admin
import routes_attendance
import routes_payroll
import routes_reports

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("makare")
CORS_ORIGINS = parse_cors_origins(os.environ.get("CORS_ORIGINS"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(await get_migration_pool())
    yield
    await close_pool()


app = FastAPI(title="MAKARE API", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Terjadi kesalahan pada server"})


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, exc: RequestValidationError):
    fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
    return JSONResponse(status_code=422, content={"detail": f"Data tidak valid pada kolom: {', '.join(fields)}"})


@app.get("/api/")
async def root():
    return {"app": "MAKARE", "status": "ok"}


@app.get("/api/health")
async def health():
    """Readiness probe for the deployed API and its configured database."""
    from core import get_pool

    pool = await get_pool()
    await pool.fetchval("SELECT 1")
    return {"app": "MAKARE", "status": "ready", "database": "connected"}


for r in (security.router, routes_admin.router, routes_attendance.router, routes_payroll.router, routes_reports.router):
    app.include_router(r)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
