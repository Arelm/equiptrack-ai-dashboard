"""
rename_asset_capacity.py

Corrects a data-entry error in the asset register. The BQ8 window unit at
AyA Tower was recorded as 1.5HP; the unit on the wall is 1.0HP.

This is a correction, not a replacement — the same physical machine, wrongly
described. So the record is renamed rather than retired, and its id, history
and any future tickets stay attached to it.

There is no asset editor in the UI, so this does it directly.

DRY RUN BY DEFAULT. Nothing is written unless you pass --apply.

    python rename_asset_capacity.py            # preview only
    python rename_asset_capacity.py --apply    # commit

Run from backend/ so it picks up .env.
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

OLD_NAME = "BQ8 Window Unit 1.5HP AC"
NEW_NAME = "BQ8 Window Unit 1.0HP AC"

conn = psycopg2.connect(url)
conn.autocommit = False

try:
    with conn.cursor() as cur:

        print("\n" + ("APPLYING" if APPLY else "DRY RUN — nothing will be written"))
        print("=" * 52)

        # ---- find it, and show where it sits -----------------------------
        cur.execute('''
            SELECT a.id, a.name, a.status, l.name, l.client
            FROM "Asset" a
            LEFT JOIN "Location" l ON l.id = a."locationId"
            WHERE a.name = %s
        ''', (OLD_NAME,))
        rows = cur.fetchall()

        if not rows:
            raise SystemExit(
                f"\nNo asset named '{OLD_NAME}'. Nothing written.\n"
                "Check the exact spelling on the ticket page."
            )
        if len(rows) > 1:
            raise SystemExit(
                f"\nFound {len(rows)} assets with that name — expected 1.\n"
                "That is itself a duplicate problem. Nothing written."
            )

        asset_id, name, status, loc_name, loc_client = rows[0]
        print(f"\n  id       {asset_id}")
        print(f"  name     {name}")
        print(f"  status   {status}")
        print(f"  site     {loc_name} ({loc_client})")

        # ---- make sure the corrected name is not already taken -----------
        cur.execute('SELECT COUNT(*) FROM "Asset" WHERE name = %s', (NEW_NAME,))
        if cur.fetchone()[0]:
            raise SystemExit(
                f"\nAn asset named '{NEW_NAME}' already exists.\n"
                "Renaming would create a duplicate. Nothing written."
            )

        print(f"\n  rename to: {NEW_NAME}")

        if APPLY:
            cur.execute(
                'UPDATE "Asset" SET name = %s, "updatedAt" = now() WHERE id = %s',
                (NEW_NAME, asset_id),
            )
            print(f"  updated {cur.rowcount}")
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