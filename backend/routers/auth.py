import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter()

AUTH_SECRET = os.environ["AUTH_SECRET"]
TOKEN_HOURS = 12


class LoginRequest(BaseModel):
    email: str
    password: str


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        ).hex()
        return hmac.compare_digest(computed, hash_hex)
    except (ValueError, AttributeError):
        return False


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            'SELECT id, email, name, role, "organizationId", "passwordHash" '
            'FROM "User" WHERE email = :em'
        ),
        {"em": body.email.strip().lower()},
    ).fetchone()

    if not row or not row.passwordHash or not verify_password(body.password, row.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    payload = {
        "sub": row.id,
        "name": row.name,
        "role": row.role,
        "orgId": row.organizationId,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    token = jwt.encode(payload, AUTH_SECRET, algorithm="HS256")

    return {
        "token": token,
        "user": {
            "id": row.id,
            "email": row.email,
            "name": row.name,
            "role": row.role,
            "orgId": row.organizationId,
        },
    }


def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, AUTH_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired - please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker