import hashlib
import os
import secrets
import time
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import Field
from api import store
from api.schemas import StrictModel

router = APIRouter(prefix="/v1/auth", tags=["authentication"])
COOKIE = "tsi_session"
SESSION_SECONDS = 86400
hasher = PasswordHasher()
dummy_hash = hasher.hash("invalid-account-timing-placeholder")


class Credentials(StrictModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9_]+$")
    password: str = Field(min_length=12, max_length=128)


def origin_check(request: Request):
    origin = request.headers.get("origin")
    expected = os.getenv("TSI_APP_ORIGIN", "http://127.0.0.1:8000")
    if origin and origin != expected:
        raise HTTPException(403, "Origin not allowed")


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def limited(request: Request, action: str, username: str):
    now = time.time()
    host = request.client.host if request.client else "unknown"
    # Count all attempts, including successful ones. Limits persist across restarts.
    keys = [digest(f"{action}:ip:{host}"), digest(f"{action}:name:{username}")]
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM auth_limits WHERE started<?", (now - 600,))
        for key in keys:
            row = db.execute("SELECT attempts FROM auth_limits WHERE key=?", (key,)).fetchone()
            if row and row["attempts"] >= 10:
                raise HTTPException(429, "Too many attempts. Try again in ten minutes.")
        for key in keys:
            db.execute("INSERT INTO auth_limits (key,started,attempts) VALUES (?,?,1) ON CONFLICT(key) DO UPDATE SET attempts=attempts+1", (key, now))


def session_response(user, response: Response):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    with store.connection() as db:
        db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        db.execute("INSERT INTO sessions (token_hash,user_id,csrf,expires) VALUES (?,?,?,?)", (digest(token), user["id"], csrf, time.time() + SESSION_SECONDS))
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=os.getenv("TSI_COOKIE_SECURE", "true") == "true",
                        samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"user": {"id": user["id"], "username": user["username"]}, "csrf_token": csrf}


def current_user(request: Request):
    token = request.cookies.get(COOKIE, "")
    with store.connection() as db:
        row = db.execute("SELECT users.id,users.username,sessions.csrf FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token_hash=? AND sessions.expires>?", (digest(token), time.time())).fetchone()
    if not row:
        raise HTTPException(401, "Sign in to continue")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin_check(request)
        if not secrets.compare_digest(request.headers.get("X-TSI-CSRF", ""), row["csrf"]):
            raise HTTPException(403, "Invalid CSRF token")
    return dict(row)


@router.post("/register", status_code=201)
def register(credentials: Credentials, request: Request, response: Response):
    origin_check(request)
    if os.getenv("TSI_REGISTRATION_ENABLED", "false") != "true":
        raise HTTPException(403, "Registration is disabled on this instance")
    limited(request, "register", credentials.username)
    password_hash = hasher.hash(credentials.password)
    user = {"id": str(uuid4()), "username": credentials.username}
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 100:
            raise HTTPException(429, "Development account limit reached")
        if db.execute("SELECT id FROM users WHERE username=?", (credentials.username,)).fetchone():
            raise HTTPException(409, "Username unavailable")
        db.execute("INSERT INTO users (id,username,password_hash,created) VALUES (?,?,?,?)", (user["id"], user["username"], password_hash, time.time()))
    return session_response(user, response)


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response):
    origin_check(request)
    limited(request, "login", credentials.username)
    with store.connection() as db:
        user = db.execute("SELECT id,username,password_hash FROM users WHERE username=?", (credentials.username,)).fetchone()
    try:
        hasher.verify(user["password_hash"] if user else dummy_hash, credentials.password)
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, "Invalid username or password")
    if not user:
        raise HTTPException(401, "Invalid username or password")
    if hasher.check_needs_rehash(user["password_hash"]):
        with store.connection() as db:
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (hasher.hash(credentials.password), user["id"]))
    return session_response(user, response)


@router.get("/me")
def me(response: Response, user=Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"user": {"id": user["id"], "username": user["username"]}, "csrf_token": user["csrf"]}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, user=Depends(current_user)):
    with store.connection() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(request.cookies.get(COOKIE, "")),))
    response.delete_cookie(COOKIE, path="/")
    response.headers["Cache-Control"] = "no-store"
