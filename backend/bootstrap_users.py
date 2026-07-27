"""Create real accounts with real passwords.

Nobody can log in today, so gating the API would lock you out of your own
dashboard. This closes that gap. It is idempotent — run it as many times as you
like; existing users keep their id and only gain a password if they lack one.

    python backend/bootstrap_users.py                 # show current state
    python backend/bootstrap_users.py --apply         # create/repair accounts
    python backend/bootstrap_users.py --reset-all     # force new passwords

Passwords are generated, printed once, and never stored in plaintext.
"""

import argparse
import hashlib
import os
import secrets
import sys
import uuid

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal  # noqa: E402

ITERATIONS = 260_000

# Edit these to match the real people before running with --apply.
SEED_USERS = [
    {"email": "ops@jdaem.com.ng",    "name": "Operations Manager", "role": "MANAGER"},
    {"email": "tech1@jdaem.com.ng",  "name": "Technician 1",       "role": "TECHNICIAN"},
    {"email": "tech2@jdaem.com.ng",  "name": "Technician 2",       "role": "TECHNICIAN"},
    {"email": "tech3@jdaem.com.ng",  "name": "Technician 3",       "role": "TECHNICIAN"},
    {"email": "tech4@jdaem.com.ng",  "name": "Technician 4",       "role": "TECHNICIAN"},
    {"email": "tech5@jdaem.com.ng",  "name": "Technician 5",       "role": "TECHNICIAN"},
]


def hash_password(password: str) -> str:
    """Matches verify_password() in routers/auth.py exactly."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def generate_password() -> str:
    """Readable on a phone screen in a plant room. No ambiguous characters."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join(
        "".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write changes")
    ap.add_argument("--reset-all", action="store_true", help="New password for every user")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        org = db.execute(
            text('SELECT id, name FROM "Organization" ORDER BY "createdAt" LIMIT 1')
        ).fetchone()
        if not org:
            print("No organisation found. Seed the database first.")
            return 1

        print(f"\nOrganisation: {org.name}  ({org.id})\n")

        rows = db.execute(text(
            'SELECT id, email, name, role, ("passwordHash" IS NOT NULL) AS has_pw '
            'FROM "User" WHERE "organizationId" = :o ORDER BY role, email'
        ), {"o": org.id}).fetchall()

        print(f"{'EMAIL':<32} {'NAME':<22} {'ROLE':<12} CAN LOG IN")
        print("-" * 82)
        for r in rows:
            print(f"{r.email or '—':<32} {r.name or '—':<22} {r.role or '—':<12} "
                  f"{'yes' if r.has_pw else 'NO'}")
        if not rows:
            print("(no users at all)")
        print()

        locked_out = [r for r in rows if not r.has_pw]
        if not args.apply and not args.reset_all:
            print(f"{len(rows)} users, {len(locked_out)} cannot log in.")
            print("Re-run with --apply to create missing accounts and set passwords.")
            return 0

        existing = {(r.email or "").lower(): r for r in rows}
        issued = []

        for spec in SEED_USERS:
            email = spec["email"].lower()
            found = existing.get(email)
            password = generate_password()

            if found and found.has_pw and not args.reset_all:
                continue

            if found:
                db.execute(text(
                    'UPDATE "User" SET "passwordHash" = :h, "isActive" = TRUE WHERE id = :i'
                ), {"h": hash_password(password), "i": found.id})
                issued.append((email, password, spec["role"], "password set"))
            else:
                db.execute(text(
                    'INSERT INTO "User" (id, email, name, role, "passwordHash", '
                    '"isActive", "organizationId", "createdAt") '
                    'VALUES (:i, :e, :n, :r, :h, TRUE, :o, NOW())'
                ), {"i": str(uuid.uuid4()), "e": email, "n": spec["name"],
                    "r": spec["role"], "h": hash_password(password), "o": org.id})
                issued.append((email, password, spec["role"], "account created"))

        # Any pre-existing user not in SEED_USERS still needs a way in.
        for r in rows:
            if not r.has_pw and (r.email or "").lower() not in {s["email"].lower() for s in SEED_USERS}:
                password = generate_password()
                db.execute(text('UPDATE "User" SET "passwordHash" = :h WHERE id = :i'),
                           {"h": hash_password(password), "i": r.id})
                issued.append((r.email, password, r.role, "existing user, password set"))

        db.commit()

        if not issued:
            print("Nothing to do — everyone can already log in.")
            return 0

        print("=" * 82)
        print("  CREDENTIALS — shown once. Copy them now, then close this terminal.")
        print("=" * 82)
        for email, pw, role, action in issued:
            print(f"  {email:<32} {pw:<16} {role:<12} ({action})")
        print("=" * 82)
        print("  Send each technician his own line only, by WhatsApp, and ask him to")
        print("  log in once today so you know the account works before it matters.")
        print("=" * 82 + "\n")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())