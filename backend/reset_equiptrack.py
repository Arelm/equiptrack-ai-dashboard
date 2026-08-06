"""
EquipTrack production data reset — 28 July 2026

KEEPS:  JDAEM organization, 11 users (admin + manager + 9 technicians),
        31 parts (quantities zeroed), JDAEM's 3 locations.

CLEARS: all assets, work orders, assignments, parts used, stock movements,
        maintenance logs, transfers, disposals, alerts, audit logs,
        the 3 demo organizations (and their locations),
        the 5 test technician accounts.

Restore point: Aurora snapshot equiptrack-pre-reset-20260728

Run from the backend folder with the venv active:
    python reset_equiptrack.py
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

JDAEM_ORG_ID = "9cc8f40a-92a1-4361-b566-d79b65b9c38d"

TEST_USER_IDS = [
    "a541bf05-cfac-4e18-a335-2a3730e15019",  # Technician 1
    "036832b6-e9c7-435e-9a39-2a634e65d105",  # Technician 2
    "ead5cfa2-a71c-4a31-914e-39b04f81bc60",  # Technician 3
    "1bb346c5-def5-447a-83c5-53d56879c267",  # Technician 4
    "3bcfe33e-311f-4ce5-ad40-d2fcb944c28b",  # Technician 5
]

# Child tables first, parents last — respects foreign keys.
WIPE_ORDER = [
    "Alert",
    "AuditLog",
    "PartsUsed",
    "StockMovement",
    "WorkOrderAssignment",
    "MaintenanceLog",
    "WorkOrder",
    "AssetTransfer",
    "AssetDisposal",
    "Asset",
]

ALL_TABLES = [
    "Alert", "Asset", "AssetDisposal", "AssetTransfer", "AuditLog",
    "Location", "MaintenanceLog", "Organization", "PartsInventory",
    "PartsUsed", "StockMovement", "User", "WorkOrder", "WorkOrderAssignment",
]


def counts(cur):
    out = {}
    for t in ALL_TABLES:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        out[t] = cur.fetchone()[0]
    return out


def show(label, data):
    print(f"\n{label}")
    print("-" * 46)
    for table, n in data.items():
        print(f"  {table:<22} {n:>5}")


def main():
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not found in .env")

    conn = psycopg2.connect(url)
    conn.autocommit = False
    cur = conn.cursor()

    before = counts(cur)
    show("BEFORE", before)

    print("\nThis will permanently delete the rows listed above except:")
    print("  - JDAEM organization and its 3 locations")
    print("  - 11 users (admin, manager, 9 named technicians)")
    print("  - 31 parts, with quantity reset to 0")
    print("\nRestore point: Aurora snapshot equiptrack-pre-reset-20260728")

    if input('\nType RESET to proceed: ').strip() != "RESET":
        print("Aborted. Nothing changed.")
        conn.rollback()
        return

    try:
        # 1. Clear all transactional tables.
        for table in WIPE_ORDER:
            cur.execute(f'DELETE FROM "{table}"')
            print(f"  cleared {table:<22} ({cur.rowcount} rows)")

        # 2. Remove the five test technician accounts.
        cur.execute(
            'DELETE FROM "User" WHERE id = ANY(%s)', (TEST_USER_IDS,)
        )
        print(f"  deleted test users        ({cur.rowcount} rows)")

        # 3. Remove demo organizations and their locations.
        cur.execute(
            'DELETE FROM "Location" WHERE "organizationId" <> %s',
            (JDAEM_ORG_ID,),
        )
        print(f"  deleted demo locations    ({cur.rowcount} rows)")

        cur.execute(
            'DELETE FROM "Organization" WHERE id <> %s', (JDAEM_ORG_ID,)
        )
        print(f"  deleted demo orgs         ({cur.rowcount} rows)")

        # 4. Zero every part so the shelf can be counted in fresh.
        cur.execute('UPDATE "PartsInventory" SET "quantity" = 0')
        print(f"  zeroed part quantities    ({cur.rowcount} rows)")

    except Exception as exc:
        conn.rollback()
        sys.exit(f"\nFAILED — rolled back, nothing changed.\n{exc}")

    after = counts(cur)
    show("AFTER (uncommitted)", after)

    expected = {"Organization": 1, "User": 11, "PartsInventory": 31, "Location": 3}
    problems = [
        f"{t}: expected {n}, got {after[t]}"
        for t, n in expected.items()
        if after[t] != n
    ]

    if problems:
        conn.rollback()
        sys.exit("\nUnexpected result — rolled back:\n  " + "\n  ".join(problems))

    if input('\nType COMMIT to save, anything else rolls back: ').strip() != "COMMIT":
        conn.rollback()
        print("Rolled back. Nothing changed.")
        return

    conn.commit()
    print("\nCommitted. Reset complete.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
