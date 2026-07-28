"""Import technicians from a CSV file.

Editing a Python list to onboard staff does not scale and puts names in git.
This reads a file that stays on your machine.

CSV columns — name and phone required, email and role optional:

    name,phone,email,role
    Emeka Okafor,+2348012345678,,TECHNICIAN
    Bola Adeyemi,08023456789,bola@jdaem.com.ng,TECHNICIAN

Phone numbers are normalised, so 0801..., +234801... and 234801... all store
identically. Role defaults to TECHNICIAN. Where no email is given a placeholder
is generated: email remains the identity key in the database, but a technician
never types it — he logs in with his phone number.

    railway run python backend/import_technicians.py technicians.csv
    railway run python backend/import_technicians.py technicians.csv --apply

Idempotent: matches on phone, so re-running updates rather than duplicating.
Existing users keep their id, their history, and their password.
"""

import argparse
import csv
import hashlib
import os
import re
import secrets
import sys
import unicodedata
import uuid

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal  # noqa: E402

ITERATIONS = 260_000
VALID_ROLES = {"TECHNICIAN", "MANAGER", "ADMIN"}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def generate_password() -> str:
    """Readable on a phone screen in a plant room. No ambiguous characters."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3))


def normalise_phone(raw: str) -> str | None:
    """Must match normalise_phone() in routers/auth.py exactly, or a number
    imported one way will not be found when the technician logs in."""
    digits = re.sub(r"[^\d+]", "", (raw or "").strip())
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
    if not rest.isdigit() or len(rest) != 10:
        return None
    return f"+234{rest}"


def placeholder_email(name: str, phone: str) -> str:
    """A unique, obviously-internal address for someone with no work email.

    The .local suffix is deliberate: it will never route, so nobody mistakes it
    for a mailbox and sends a real message to it.
    """
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", ".", slug.lower()).strip(".")
    return f"{slug or 'tech'}.{phone[-4:]}@jdaem.local"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", help="Path to the CSV file")
    ap.add_argument("--apply", action="store_true", help="Write changes")
    args = ap.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"File not found: {args.csv_path}")
        return 1

    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("The CSV has no rows.")
        return 1

    missing = {"name", "phone"} - {(k or "").strip().lower() for k in rows[0]}
    if missing:
        print(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
        print("Expected header: name,phone,email,role")
        return 1

    db = SessionLocal()
    try:
        org = db.execute(
            text('SELECT id, name FROM "Organization" ORDER BY "createdAt" LIMIT 1')
        ).fetchone()
        if not org:
            print("No organisation found.")
            return 1

        print(f"\nOrganisation: {org.name}")
        print(f"Source: {args.csv_path}\n")

        existing = {
            r.phone: r
            for r in db.execute(text(
                'SELECT id, phone, name, ("passwordHash" IS NOT NULL) AS has_pw '
                'FROM "User" WHERE "organizationId" = :o AND phone IS NOT NULL'
            ), {"o": org.id}).fetchall()
        }

        parsed, problems, seen = [], [], set()

        for i, raw in enumerate(rows, start=2):  # row 1 is the header
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            name = row.get("name", "")
            phone = normalise_phone(row.get("phone", ""))
            email = row.get("email", "").lower()
            role = (row.get("role") or "TECHNICIAN").upper()

            if not name:
                problems.append(f"Row {i}: no name")
                continue
            if not phone:
                problems.append(f"Row {i}: '{row.get('phone', '')}' is not a valid Nigerian number")
                continue
            if phone in seen:
                problems.append(f"Row {i}: {phone} appears more than once in the file")
                continue
            if role not in VALID_ROLES:
                problems.append(f"Row {i}: role '{role}' is not one of {', '.join(sorted(VALID_ROLES))}")
                continue

            seen.add(phone)
            parsed.append({
                "name": name,
                "phone": phone,
                "email": email or placeholder_email(name, phone),
                "role": role,
                "generated_email": not email,
            })

        if problems:
            print("PROBLEMS — nothing was written:\n")
            for p in problems:
                print(f"  {p}")
            print("\nFix the file and run again.")
            return 1

        print(f"{'NAME':<24} {'PHONE':<16} {'ROLE':<12} {'LOGIN EMAIL':<32} ACTION")
        print("-" * 104)

        for p in parsed:
            action = "update" if p["phone"] in existing else "create"
            shown = p["email"] + (" *" if p["generated_email"] else "")
            print(f"{p['name']:<24} {p['phone']:<16} {p['role']:<12} {shown:<32} {action}")

        print("\n* generated placeholder — this person logs in with his phone number")

        if not args.apply:
            creates = sum(1 for p in parsed if p["phone"] not in existing)
            print(f"\n{len(parsed)} rows: {creates} to create, {len(parsed) - creates} to update.")
            print("Read-only. Re-run with --apply to write.")
            return 0

        issued = []
        for p in parsed:
            found = existing.get(p["phone"])
            if found:
                # Never overwrite a working password. A technician mid-shift
                # should not be logged out because someone re-ran the import.
                db.execute(text(
                    'UPDATE "User" SET name = :n, role = :r, "isActive" = TRUE, '
                    '"updatedAt" = NOW() WHERE id = :i'
                ), {"n": p["name"], "r": p["role"], "i": found.id})
                if not found.has_pw:
                    pw = generate_password()
                    db.execute(text('UPDATE "User" SET "passwordHash" = :h WHERE id = :i'),
                               {"h": hash_password(pw), "i": found.id})
                    issued.append((p["name"], p["phone"], pw))
            else:
                pw = generate_password()
                db.execute(text(
                    'INSERT INTO "User" (id, email, name, phone, role, "passwordHash", '
                    '"isActive", "organizationId", "createdAt", "updatedAt") '
                    'VALUES (:i, :e, :n, :p, :r, :h, TRUE, :o, NOW(), NOW())'
                ), {"i": str(uuid.uuid4()), "e": p["email"], "n": p["name"],
                    "p": p["phone"], "r": p["role"], "h": hash_password(pw), "o": org.id})
                issued.append((p["name"], p["phone"], pw))

        db.commit()

        if not issued:
            print("\nNothing to issue — everyone already has a password.")
            return 0

        print("\n" + "=" * 72)
        print("  CREDENTIALS — shown once. Copy them now.")
        print("=" * 72)
        for name, phone, pw in issued:
            print(f"  {name:<24} logs in with {phone}   password: {pw}")
        print("=" * 72)
        print("  Send each man his own line only, by WhatsApp. Ask him to log in")
        print("  today, so you find a broken account now and not on a callout.")
        print("=" * 72 + "\n")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())