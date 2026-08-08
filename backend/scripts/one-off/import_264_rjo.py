"""
import_264_rjo.py

Imports the AC register for two Sterling Oil sites from the
"264 & RJO" spreadsheet.

  264   already exists as a site. 67 assets are added: flats A1-A8,
        B1-B8 and BQ.

        One row is deliberately skipped. The sheet lists flat B7 Rm3
        as a York, but that unit is already in the register as
        "2HP Panasonic at 264 F7B R3" and carries the only fault
        history in the system - a refrigerant leak, one maintenance
        log and two work orders. Panasonic is the correct make, so the
        existing record stands and the sheet row is dropped rather
        than creating a second record for the same machine.

  RJO   is new. The site is created (Sterling Oil, V.I., supervisor
        Tosin Dauda, 08139112319) and 61 assets are added.

Names follow the searchable pattern already used elsewhere in the
register, so the room text can be found from the asset search box:

    264 - A1 - Ticketing - Panasonic 2HP
    RJO - 1st Floor - Hall - Panasonic 5HP (1 of 4)

Rooms holding several identical units get "(n of m)" so they stay
distinguishable instead of collapsing into duplicates.

Makes are normalised (york -> York, panasonic -> Panasonic) and flat
labels tidied (B 2 -> B2). Two spellings from the sheet are corrected
on the way in: "Comfrence Rm" -> "Conference Rm" and "Dinning" ->
"Dining".

DRY RUN BY DEFAULT. Nothing is written unless you pass --apply.

    python import_264_rjo.py            # preview
    python import_264_rjo.py --apply    # commit

Any asset whose name is already present is skipped, so re-running is
safe and will not duplicate.

Run from backend/ so it picks up .env.
"""

import os
import sys
import uuid
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL not found in .env")

APPLY = "--apply" in sys.argv

NEW_SITE = {
    "name": "RJO",
    "client": "Sterling Oil",
    "area": "V.I.",
    "supervisorName": "Tosin Dauda",
    "supervisorPhone": "08139112319",
}

ROWS = [
    ('264', '264 · A1 · Ticketing — Panasonic 2HP'),
    ('264', '264 · A1 · Office 3 — Daikin 1.5HP'),
    ('264', '264 · A1 · Conference Rm — Panasonic 2HP'),
    ('264', '264 · A1 · Madam Rose Office 1 — Panasonic 2HP'),
    ('264', '264 · A1 · Madam Rose Office 2 — Panasonic 2HP'),
    ('264', '264 · A1 · Sport Mgt office — Panasonic 2HP'),
    ('264', '264 · A2 · Office 1 — Daikin 2HP'),
    ('264', '264 · A2 · Office 2 — Daikin 1.5HP'),
    ('264', '264 · A2 · HOD Office 1 — Daikin 2HP'),
    ('264', '264 · A2 · Ass. HOD office 2 — Panasonic 1.5HP'),
    ('264', '264 · A2 · Office 3 — Panasonic 1.5HP'),
    ('264', '264 · A3 · Hall — Panasonic 2HP'),
    ('264', '264 · A3 · Rm 2 — Panasonic 1.5HP'),
    ('264', '264 · A3 · Rm 3 — Panasonic 2HP'),
    ('264', '264 · A4 · Rm1 — Panasonic 2HP'),
    ('264', '264 · A4 · Rm2 — Panasonic 2HP'),
    ('264', '264 · A4 · Store — Panasonic 2HP'),
    ('264', '264 · A4 · Rm3 — Panasonic 1.5HP'),
    ('264', '264 · A5 · Rm1 — Daikin 2HP'),
    ('264', '264 · A5 · Rm2 — Panasonic 1.5HP'),
    ('264', '264 · A5 · Rm3 — Panasonic 2HP'),
    ('264', '264 · A6 · Hall — Panasonic 2HP'),
    ('264', '264 · A6 · Rm1 — York 2HP'),
    ('264', '264 · A6 · Rm2 — Panasonic 1.5HP'),
    ('264', '264 · A6 · Rm3 — Panasonic 1.5HP'),
    ('264', '264 · A7 · Rm1 — Panasonic 1.5HP'),
    ('264', '264 · A7 · Rm2 — Panasonic 2HP'),
    ('264', '264 · A7 · Rm3 — Panasonic 2HP'),
    ('264', '264 · A8 · Rm1 — Panasonic 2HP'),
    ('264', '264 · A8 · Rm2 — Panasonic 2HP'),
    ('264', '264 · A8 · Rm3 — Panasonic 2HP'),
    ('264', '264 · A8 · Rm4 — Panasonic 2HP'),
    ('264', '264 · B1 · Electrical Store — Daikin 2HP'),
    ('264', '264 · B1 · Rm1 — Panasonic 2HP'),
    ('264', '264 · B1 · Rm2 — York 2HP'),
    ('264', '264 · B1 · Stationery Store — Panasonic 1.5HP'),
    ('264', '264 · B2 · Madam Akarba Office — Panasonic 1.5HP'),
    ('264', '264 · B2 · Rm1 — Daikin 1.5HP'),
    ('264', '264 · B2 · Rm2 — Panasonic 2HP'),
    ('264', '264 · B2 · RM3 — Panasonic 2HP'),
    ('264', '264 · B3 · Hall — Panasonic 2HP'),
    ('264', '264 · B3 · Dining — Panasonic 2HP'),
    ('264', '264 · B3 · Rm1 — Panasonic 1.5HP'),
    ('264', '264 · B3 · Rm2 — Panasonic 1.5HP'),
    ('264', '264 · B3 · Rm3 — Panasonic 1.5HP'),
    ('264', '264 · B4 · Hall — Panasonic 1.5HP'),
    ('264', '264 · B4 · Dining — Panasonic 2HP'),
    ('264', '264 · B4 · Rm1 — Panasonic 1.5HP'),
    ('264', '264 · B4 · Rm2 — Panasonic 2HP'),
    ('264', '264 · B4 · Rm3 — Panasonic 1.5HP'),
    ('264', '264 · BQ · BQ1 — York 2HP'),
    ('264', '264 · BQ · BQ2 — Daikin 1.5HP'),
    ('264', '264 · BQ · BQ3 — Daikin 1.5HP'),
    ('264', '264 · B6 · Hall — Daikin 2HP'),
    ('264', '264 · B6 · Dining — Panasonic 1.5HP'),
    ('264', '264 · B6 · R1 — York 2HP'),
    ('264', '264 · B6 · R2 — Daikin 2HP'),
    ('264', '264 · B6 · R3 — Panasonic 1.5HP'),
    ('264', '264 · B7 · Hall — Panasonic 1.5HP'),
    ('264', '264 · B7 · Dining — Panasonic 2HP'),
    ('264', '264 · B7 · R1 — Daikin 2HP'),
    ('264', '264 · B7 · R2 — Daikin 2HP'),
    ('264', '264 · B8 · Hall — Panasonic 2HP'),
    ('264', '264 · B8 · Dining — Panasonic 2HP'),
    ('264', '264 · B8 · R1 — Daikin 1.5HP'),
    ('264', '264 · B8 · R2 — Panasonic 1.5HP'),
    ('264', '264 · B8 · R3 — Panasonic 1.5HP'),
    ('RJO', 'RJO · Ground Floor - FrontSide · Hall — Panasonic 5HP (1 of 2)'),
    ('RJO', 'RJO · Ground Floor - FrontSide · Hall — Panasonic 5HP (2 of 2)'),
    ('RJO', 'RJO · Ground Floor - FrontSide · Cabin 01 — Panasonic 1.5HP'),
    ('RJO', 'RJO · Ground Floor - FrontSide · Cabin 02 — Panasonic 1.5HP'),
    ('RJO', 'RJO · Ground Floor - FrontSide · Cabin 03 — Panasonic 1.5HP'),
    ('RJO', 'RJO · Ground Floor Backside · Hall — Kenstar 3HP'),
    ('RJO', 'RJO · Ground Floor Backside · Hall — Panasonic 3HP'),
    ('RJO', 'RJO · Ground Floor Backside · cabin 01 — Daikin 1.5HP'),
    ('RJO', 'RJO · Ground Floor Backside · cabin 02 — Panasonic 1.5HP'),
    ('RJO', 'RJO · Ground Floor Backside · cabin 03 — Daikin 2HP'),
    ('RJO', 'RJO · LIFT · Lift — Panasonic 2HP (1 of 2)'),
    ('RJO', 'RJO · LIFT · Lift — Panasonic 2HP (2 of 2)'),
    ('RJO', 'RJO · 1st Floor · Conference — Panasonic 3HP'),
    ('RJO', 'RJO · 1st Floor · Hall — Panasonic 5HP (1 of 4)'),
    ('RJO', 'RJO · 1st Floor · Hall — Panasonic 5HP (2 of 4)'),
    ('RJO', 'RJO · 1st Floor · Hall — Panasonic 5HP (3 of 4)'),
    ('RJO', 'RJO · 1st Floor · Hall — Panasonic 5HP (4 of 4)'),
    ('RJO', 'RJO · 1st Floor · Cabin 01 — Daikin 2HP'),
    ('RJO', 'RJO · 1st Floor · Cabin 02 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 1st Floor · Cabin 03 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 1st Floor · Cabin 04 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 1st Floor · Cabin 05 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 2nd Floor · Conference — Panasonic 3HP'),
    ('RJO', 'RJO · 2nd Floor · HOD — Daikin 2HP'),
    ('RJO', 'RJO · 2nd Floor · Hall — Panasonic 5HP (1 of 4)'),
    ('RJO', 'RJO · 2nd Floor · Hall — Panasonic 5HP (2 of 4)'),
    ('RJO', 'RJO · 2nd Floor · Hall — Panasonic 5HP (3 of 4)'),
    ('RJO', 'RJO · 2nd Floor · Hall — Panasonic 5HP (4 of 4)'),
    ('RJO', 'RJO · 2nd Floor · Cabin 01 — Daikin 2HP'),
    ('RJO', 'RJO · 2nd Floor · Cabin 02 — Daikin 1.5HP'),
    ('RJO', 'RJO · 2nd Floor · Cabin 03 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 2nd Floor · Cabin 04 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 2nd Floor · Cabin 05 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 2nd Floor · Server Room — Daikin 2HP'),
    ('RJO', 'RJO · 3rd Floor · HOD — York 2HP'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 3HP (1 of 4)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 3HP (2 of 4)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 3HP (3 of 4)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 3HP (4 of 4)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 5HP (1 of 3)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 5HP (2 of 3)'),
    ('RJO', 'RJO · 3rd Floor · Hall — Panasonic 5HP (3 of 3)'),
    ('RJO', 'RJO · 3rd Floor · Cabin 01 — Daikin 2HP'),
    ('RJO', 'RJO · 3rd Floor · Cabin 02 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 3rd Floor · Cabin 03 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 3rd Floor · Cabin 04 — Panasonic 1.5HP'),
    ('RJO', 'RJO · 3rd Floor · Store — Daikin 1.5HP'),
    ('RJO', 'RJO · 4th Floor · Conference — Daikin 5HP (1 of 2)'),
    ('RJO', 'RJO · 4th Floor · Conference — Daikin 5HP (2 of 2)'),
    ('RJO', 'RJO · 4th Floor · Conference — Panasonic 2HP (1 of 2)'),
    ('RJO', 'RJO · 4th Floor · Conference — Panasonic 2HP (2 of 2)'),
    ('RJO', 'RJO · 4th Floor · Conference — York 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 01 — Daikin 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 02 — Daikin 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 02 — Panasonic 5HP'),
    ('RJO', 'RJO · 4th Floor · Office 02 — York 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 03 — York 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 04 — Daikin 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 04 — York 2HP'),
    ('RJO', 'RJO · 4th Floor · Office 04 — Panasonic 3HP'),
    ('RJO', 'RJO · 4th Floor · HOD — Panasonic 2HP'),
]


conn = psycopg2.connect(url)
conn.autocommit = False

try:
    with conn.cursor() as cur:

        print("\n" + ("APPLYING" if APPLY else "DRY RUN - nothing will be written"))
        print("=" * 56)

        # ---- organisation -------------------------------------------------
        cur.execute('SELECT id, name FROM "Organization"')
        orgs = cur.fetchall()
        if len(orgs) != 1:
            raise SystemExit(
                f"\nExpected exactly one organisation, found {len(orgs)}.\n"
                "Nothing written."
            )
        org_id, org_name = orgs[0]
        print(f"\n  organisation: {org_name}")

        # ---- sites --------------------------------------------------------
        cur.execute('SELECT id, name FROM "Location" WHERE name = ANY(%s)',
                    (["264", NEW_SITE["name"]],))
        found = {name: lid for lid, name in cur.fetchall()}

        if "264" not in found:
            raise SystemExit(
                "\nSite 264 not found. It was expected to already exist.\n"
                "Nothing written."
            )
        print(f"  site 264:     {found['264']}")

        rjo_id = found.get(NEW_SITE["name"])
        if rjo_id:
            print(f"  site RJO:     {rjo_id} (already exists)")
        else:
            rjo_id = str(uuid.uuid4())
            print(f"  site RJO:     {rjo_id} (will be created)")
            print(f"                {NEW_SITE['client']}, {NEW_SITE['area']}, "
                  f"{NEW_SITE['supervisorName']} {NEW_SITE['supervisorPhone']}")
            if APPLY:
                cur.execute(
                    '''INSERT INTO "Location"
                       (id, name, "organizationId", client, area,
                        "supervisorName", "supervisorPhone", "isActive")
                       VALUES (%s,%s,%s,%s,%s,%s,%s, true)''',
                    (rjo_id, NEW_SITE["name"], org_id, NEW_SITE["client"],
                     NEW_SITE["area"], NEW_SITE["supervisorName"],
                     NEW_SITE["supervisorPhone"]),
                )

        site_ids = {"264": found["264"], NEW_SITE["name"]: rjo_id}

        # ---- assets -------------------------------------------------------
        cur.execute('SELECT name FROM "Asset"')
        existing = {r[0] for r in cur.fetchall()}

        to_add = [(loc, name) for loc, name in ROWS if name not in existing]
        skipped = len(ROWS) - len(to_add)

        print(f"\n  {len(ROWS)} rows in the sheet")
        if skipped:
            print(f"  {skipped} already in the register - skipping those")
        print(f"  {len(to_add)} to insert\n")

        for loc in ("264", NEW_SITE["name"]):
            n = len([1 for l, _ in to_add if l == loc])
            print(f"    {loc:<5} {n}")

        print("\n  first three:")
        for _, name in to_add[:3]:
            print(f"    {name}")
        print("  last three:")
        for _, name in to_add[-3:]:
            print(f"    {name}")

        if APPLY and to_add:
            for loc, name in to_add:
                cur.execute(
                    '''INSERT INTO "Asset"
                       (id, name, category, status, "organizationId",
                        "locationId", "custodyStatus", "createdAt", "updatedAt")
                       VALUES (%s,%s,'HVAC','OPERATIONAL',%s,%s,'ON_SITE',
                               now(), now())''',
                    (str(uuid.uuid4()), name, org_id, site_ids[loc]),
                )
            print(f"\n  inserted {len(to_add)}")

        if APPLY:
            conn.commit()
            print("\nCommitted.\n")
        else:
            conn.rollback()
            print("\nDry run complete - nothing written.")
            print("Re-run with --apply to commit.\n")

except Exception:
    conn.rollback()
    raise
finally:
    conn.close()