import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from core import get_pool, close_pool
from schema import init_db
import security
import routes_admin
import routes_attendance
import routes_payroll

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("makare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(await get_pool())
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


for r in (security.router, routes_admin.router, routes_attendance.router, routes_payroll.router):
    app.include_router(r)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
