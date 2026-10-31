import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from core import get_pool, err, audit, rate_limit

JWT_SECRET = os.environ["JWT_SECRET"]
ALG = "HS256"
bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/auth")


def verify_secret(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(payload: dict, hours: int) -> str:
    data = {**payload, "exp": datetime.now(timezone.utc) + timedelta(hours=hours)}
    return jwt.encode(data, JWT_SECRET, algorithm=ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        err(401, "Sesi tidak valid atau kedaluwarsa")


async def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not cred:
        err(401, "Silakan masuk terlebih dahulu")
    claims = decode_token(cred.credentials)
    if claims.get("typ") != "session":
        err(401, "Sesi tidak valid")
    uid = int(claims["sub"])
    pool = await get_pool()
    u = await pool.fetchrow("SELECT id, username, full_name, role, active, session_version FROM users WHERE id=$1", uid)
    if not u or not u["active"]:
        err(401, "Akun tidak aktif")
    if claims.get("sv", 0) != u["session_version"]:
        err(401, "Sesi telah dicabut. Silakan masuk kembali.")
    result = dict(u)
    result.pop("session_version", None)
    return result


async def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        err(403, "Hanya Administrator yang diizinkan")
    return user


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


@router.post("/login")
async def login(body: LoginIn, request: Request):
    rate_limit(request, f"login:{body.username.lower()}", 8, 300)
    pool = await get_pool()
    u = await pool.fetchrow("SELECT * FROM users WHERE username=$1", body.username.strip().lower())
    if not u or not u["active"] or not verify_secret(body.password, u["password_hash"]):
        async with pool.acquire() as c:
            await audit(c, body.username[:64], "login", "auth", result="failed")
        err(401, "Username atau kata sandi salah")
    async with pool.acquire() as c:
        await audit(c, u["username"], "login", "auth", u["id"])
    token = make_token({"sub": str(u["id"]), "role": u["role"], "sv": u["session_version"], "typ": "session"}, 12)
    return {"token": token, "user": {"id": u["id"], "username": u["username"], "full_name": u["full_name"], "role": u["role"]}}


@router.post("/logout")
async def logout(user: dict = Depends(current_user)):
    pool = await get_pool()
    async with pool.acquire() as c:
        async with c.transaction():
            await c.execute("UPDATE users SET session_version=session_version+1 WHERE id=$1", user["id"])
            await audit(c, user["username"], "logout", "auth", user["id"], after={"sessions_revoked": True})
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return user
