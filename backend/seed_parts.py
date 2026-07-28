"""Seed the parts catalogue with JDAEM's actual consumables.

Idempotent — matches on partNumber, so re-running updates rather than
duplicating. Opening quantities are zero: stock is what you count, not what a
script asserts. Receive real quantities through the Parts page so every balance
has a ledger entry behind it.

    railway run python backend/seed_parts.py --apply
"""

import argparse
import os
import sys
import uuid

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal  # noqa: E402

# (partNumber, name, unit, category, reorderLevel)
PARTS = [
    ("CU-0250", 'Copper pipe 1/4"',  "m", "Pipe", 30),
    ("CU-0375", 'Copper pipe 3/8"',  "m", "Pipe", 30),
    ("CU-0500", 'Copper pipe 1/2"',  "m", "Pipe", 30),
    ("CU-0625", 'Copper pipe 5/8"',  "m", "Pipe", 30),
    ("CU-0750", 'Copper pipe 3/4"',  "m", "Pipe", 20),

    ("ARM-0375", 'Armaflex 3/8"', "pcs", "Insulation", 20),
    ("ARM-0625", 'Armaflex 5/8"', "pcs", "Insulation", 20),
    ("ARM-0750", 'Armaflex 3/4"', "pcs", "Insulation", 15),

    ("FLN-0250", 'Flare nut 1/4"', "pcs", "Fittings", 25),
    ("FLN-0375", 'Flare nut 3/8"', "pcs", "Fittings", 25),
    ("FLN-0500", 'Flare nut 1/2"', "pcs", "Fittings", 25),
    ("FLN-0625", 'Flare nut 5/8"', "pcs", "Fittings", 25),
    ("FLN-0750", 'Flare nut 3/4"', "pcs", "Fittings", 15),

    ("REF-R22",  "Refrigerant R22",   "kg", "Refrigerant", 10),
    ("REF-R410", "Refrigerant R410A", "kg", "Refrigerant", 10),
    ("REF-R32",  "Refrigerant R32",   "kg", "Refrigerant", 10),

    ("FLX-075", "Flexible pipe 75mm", "m", "Ducting", 20),
    ("FLX-055", "Flexible pipe 55mm", "m", "Ducting", 20),

    ("TRK-075", "Trunking 75mm", "length", "Trunking", 10),
    ("TRK-055", "Trunking 55mm", "length", "Trunking", 10),
    ("TRK-016", "Trunking 16mm", "length", "Trunking", 10),

    ("KIT-INST", "Installation kit (assorted pipe)", "set", "Kit", 5),

    ("CAP-R25",  "Run capacitor 25uF",     "pcs", "Electrical", 6),
    ("CAP-R35",  "Run capacitor 35uF",     "pcs", "Electrical", 6),
    ("CAP-R45",  "Run capacitor 45uF",     "pcs", "Electrical", 6),
    ("CON-25A",  "Contactor 25A",          "pcs", "Electrical", 4),
    ("CON-40A",  "Contactor 40A",          "pcs", "Electrical", 4),
    ("OLP-STD",  "Overload protector",     "pcs", "Electrical", 4),

    ("DRI-STD",  "Filter drier",           "pcs", "Consumable", 6),
    ("BRZ-15",   "Brazing rod 15% silver", "pcs", "Consumable", 20),
    ("NIT-TEST", "Nitrogen (pressure testing)", "kg", "Consumable", 5),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Write to the database")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        org = db.execute(
            text('SELECT id, name FROM "Organization" ORDER BY "createdAt" LIMIT 1')
        ).fetchone()
        if not org:
            print("No organisation found.")
            return 1

        print(f"\nOrganisation: {org.name}\n")

        existing = {
            r.partNumber: r.id
            for r in db.execute(text(
                'SELECT id, "partNumber" FROM "PartsInventory" WHERE "organizationId" = :o'
            ), {"o": org.id}).fetchall()
        }

        print(f"{'PART NO':<12} {'NAME':<38} {'UNIT':<8} {'CATEGORY':<14} ACTION")
        print("-" * 92)

        created = updated = 0
        for number, name, unit, category, reorder in PARTS:
            action = "update" if number in existing else "create"
            print(f"{number:<12} {name:<38} {unit:<8} {category:<14} {action}")

            if not args.apply:
                continue

            if number in existing:
                db.execute(text(
                    'UPDATE "PartsInventory" SET name = :n, unit = :u, category = :c, '
                    '"reorderLevel" = :r, "updatedAt" = NOW() WHERE id = :i'
                ), {"n": name, "u": unit, "c": category, "r": reorder,
                    "i": existing[number]})
                updated += 1
            else:
                db.execute(text(
                    'INSERT INTO "PartsInventory" '
                    '(id, name, "partNumber", quantity, "reorderLevel", unit, category, '
                    '"organizationId", "createdAt", "updatedAt") '
                    'VALUES (:i, :n, :p, 0, :r, :u, :c, :o, NOW(), NOW())'
                ), {"i": str(uuid.uuid4()), "n": name, "p": number, "r": reorder,
                    "u": unit, "c": category, "o": org.id})
                created += 1

        if not args.apply:
            print(f"\n{len(PARTS)} parts. Read-only — re-run with --apply to write.")
            return 0

        db.commit()
        print(f"\n{created} created, {updated} updated.\n")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())