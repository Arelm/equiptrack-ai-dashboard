import hashlib
import hmac
import os
import re
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
    # Named 'email' for backward compatibility with the existing login page,
    # but it accepts a phone number too. Renaming it would break every client
    # in the field for no gain.
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


def normalise_phone(raw: str) -> str | None:
    """Reduce anything a Nigerian technician might type to one stored form.

    08012345678, +234 801 234 5678, 234-801-234-5678 and 2348012345678 are the
    same number. A technician standing in a plant room will type whichever he
    remembers, and being told 'invalid' because of a leading zero is the kind
    of friction that ends with him not using the app.

    Returns None if the input does not look like a phone number at all, which
    is how the caller decides to treat it as an email instead.
    """
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if not digits:
        return None

    if digits.startswith("+234"):
        rest = digits[4:]
    elif digits.startswith("234"):
        rest = digits[3:]
    elif digits.startswith("0"):
        rest = digits[1:]
    else:
        return None

    # Nigerian subscriber numbers are 10 digits after the country code.
    if not rest.isdigit() or len(rest) != 10:
        return None

    return f"+234{rest}"


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    identifier = body.email.strip()
    phone = normalise_phone(identifier)

    if phone:
        row = db.execute(
            text(
                'SELECT id, email, name, role, "organizationId", "passwordHash", '
                '"isActive" FROM "User" WHERE phone = :ph'
            ),
            {"ph": phone},
        ).fetchone()
    else:
        row = db.execute(
            text(
                'SELECT id, email, name, role, "organizationId", "passwordHash", '
                '"isActive" FROM "User" WHERE email = :em'
            ),
            {"em": identifier.lower()},
        ).fetchone()

    # One message for every failure. Distinguishing "no such user" from "wrong
    # password" tells an attacker which phone numbers are registered.
    if not row or not row.passwordHash or not verify_password(body.password, row.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    if row.isActive is False:
        raise HTTPException(
            status_code=403,
            detail="This account has been deactivated. Speak to your supervisor.",
        )

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


def get_current_user_optional(authorization: str = Header(None)):
    """Like get_current_user, but returns None instead of 401 when no/invalid token.

    Used only by the Client Portal intake route, where raising a service request
    must not require an account.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(token, AUTH_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None