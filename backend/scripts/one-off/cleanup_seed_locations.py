"""
cleanup_seed_locations.py

Two changes, in one transaction:

  1. DELETE the duplicate asset "2HP Panasonic at 264 F7R3" (created
     2026-08-04 08:37:46, sitting on Victoria Island HQ). Verified to have
     zero references in Alert, AssetDisposal, AssetTransfer, MaintenanceLog
     and WorkOrder. The real record, "2HP Panasonic at 264 F7B R3" on plot
     264, keeps all the history.

  2. Set isActive = false on the three seeded locations: Lekki Project Site,
     Ikorodu Site Office, Victoria Island HQ. Rows are kept, not deleted,
     so this is reversible with a single UPDATE.

DRY RUN BY DEFAULT. Nothing is written unless you pass --apply.

    python cleanup_seed_locations.py            # preview only
    python cleanup_seed_locations.py --apply    # commit

Safety net: Aurora snapshot pre-cleanup-2026-08-07 (Available).
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL not found in .env")

APPLY = "--apply" in sys.argv

DUPLICATE = "2HP Panasonic at 264 F7R3"
SURVIVOR = "2HP Panasonic at 264 F7B R3"
SEED_NAMES = ["Lekki Project Site", "Ikorodu Site Office", "Victoria Island HQ"]

conn = psycopg2.connect(url)
conn.autocommit = False

try:
    with conn.cursor() as cur:

        print("\n" + ("APPLYING CHANGES" if APPLY else "DRY RUN — nothing will be written"))
        print("=" * 52)

        # ---- preflight: the duplicate must still be reference-free -------
        cur.execute('''
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'Asset'
        ''')
        blocking = []
        for table, col in cur.fetchall():
            cur.execute(f'''
                SELECT COUNT(*) FROM "{table}" t
                JOIN "Asset" a ON a.id = t."{col}"
                WHERE a.name = %s
            ''', (DUPLICATE,))
            n = cur.fetchone()[0]
            if n:
                blocking.append(f"{table}.{col} ({n})")

        if blocking:
            raise SystemExit(
                "\nABORTED — the duplicate is now referenced by: "
                + ", ".join(blocking)
                + "\nRepoint that history at the survivor first.\n"
            )

        # ---- preflight: the survivor must exist --------------------------
        cur.execute('SELECT COUNT(*) FROM "Asset" WHERE name = %s', (SURVIVOR,))
        if cur.fetchone()[0] != 1:
            raise SystemExit(
                f"\nABORTED — expected exactly one '{SURVIVOR}'. "
                "Do not delete the duplicate until the survivor is confirmed.\n"
            )
        print(f"\n  survivor present: {SURVIVOR}")

        # ---- 1. delete the duplicate -------------------------------------
        cur.execute(
            'SELECT id FROM "Asset" WHERE name = %s', (DUPLICATE,))
        dup_rows = cur.fetchall()
        print(f"\n1. DELETE asset '{DUPLICATE}' — {len(dup_rows)} row(s)")
        for (aid,) in dup_rows:
            print(f"     {aid}")

        if APPLY and dup_rows:
            cur.execute('DELETE FROM "Asset" WHERE name = %s', (DUPLICATE,))
            print(f"     deleted {cur.rowcount}")

        # ---- 2. deactivate the seeded locations --------------------------
        cur.execute('''
            SELECT id, name, "isActive" FROM "Location"
            WHERE name = ANY(%s) ORDER BY name
        ''', (SEED_NAMES,))
        locs = cur.fetchall()

        print(f"\n2. DEACTIVATE locations — {len(locs)} row(s)")
        for lid, name, active in locs:
            print(f"     {name:<22} isActive {active} -> False")

        if len(locs) != 3:
            raise SystemExit(
                f"\nABORTED — expected 3 seeded locations, found {len(locs)}.\n"
            )

        if APPLY:
            cur.execute('''
                UPDATE "Location" SET "isActive" = false
                WHERE name = ANY(%s)
            ''', (SEED_NAMES,))
            print(f"     updated {cur.rowcount}")

        # ---- commit or roll back ------------------------------------------
        if APPLY:
            conn.commit()
            print("\nCommitted.\n")
        else:
            conn.rollback()
            print("\nDry run complete — nothing written.")
            print("Re-run with --apply to commit.\n")

except Exception:
    conn.rollback()
    raise
finally:
    conn.close()