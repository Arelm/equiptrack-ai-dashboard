"""
Seeds Aurora with realistic Organization / Location / Asset / WorkOrder rows
so EquipTrack AI has real data to demo against, instead of the hardcoded
lib/data.ts mock array.

Run this LOCALLY from inside backend/, where your .env with DATABASE_URL lives.

Usage:
    cd backend
    pip install psycopg2-binary python-dotenv --break-system-packages   # if not already installed
    python seed_db.py

Safe to re-run: it checks for an existing "JDAEM Enterprise Limited" org first
and skips seeding if data already exists, so you won't get duplicates.
"""

import os
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not found in environment. Make sure you're running this")
    print("from the backend/ folder with a .env file containing DATABASE_URL.")
    raise SystemExit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def new_id():
    return str(uuid.uuid4())


# ---- Safety check: don't double-seed ----
cur.execute('SELECT id FROM "Organization" WHERE name = %s;', ("JDAEM Enterprise Limited",))
existing = cur.fetchone()
if existing:
    print("Seed data already exists (found 'JDAEM Enterprise Limited' org). Skipping seed.")
    print(f"Organization id: {existing['id']}")
    cur.close()
    conn.close()
    raise SystemExit(0)

print("No existing seed data found. Seeding now...\n")

try:
    # ---- Organizations (clients) ----
    orgs = {
        "JDAEM Enterprise Limited": "HVAC / MEP Engineering",
        "Aurora Health Systems": "Healthcare",
        "Cedar Foods Mfg.": "Food Manufacturing",
        "Summit Retail Group": "Retail",
    }
    org_ids = {}
    for name, industry in orgs.items():
        oid = new_id()
        now = datetime.utcnow()
        cur.execute(
            'INSERT INTO "Organization" (id, name, industry, "createdAt", "updatedAt") VALUES (%s, %s, %s, %s, %s);',
            (oid, name, industry, now, now),
        )
        org_ids[name] = oid
        print(f"  Organization: {name}")

    # ---- Locations ----
    locations = [
        ("Victoria Island HQ", "Plot 14 Adeola Odeku St, Victoria Island, Lagos", "JDAEM Enterprise Limited"),
        ("Ikorodu Site Office", "Ikorodu Industrial Layout, Lagos", "JDAEM Enterprise Limited"),
        ("St. Mary Wing B", "210 Medical Dr, Plano, TX", "Aurora Health Systems"),
        ("Imaging Center", "210 Medical Dr, Plano, TX", "Aurora Health Systems"),
        ("Plant 3 - Packaging", "900 Industrial Way, Cedar Rapids, IA", "Cedar Foods Mfg."),
        ("Plant 1 - Cold Storage", "120 Industrial Way, Cedar Rapids, IA", "Cedar Foods Mfg."),
        ("Store #214 - Denver", "88 Market St, Denver, CO", "Summit Retail Group"),
    ]
    location_ids = {}
    for name, address, org_name in locations:
        lid = new_id()
        cur.execute(
            'INSERT INTO "Location" (id, name, address, "organizationId", "createdAt") VALUES (%s, %s, %s, %s, %s);',
            (lid, name, address, org_ids[org_name], datetime.utcnow()),
        )
        location_ids[name] = lid
        print(f"  Location: {name}")

    # ---- Assets ----
    # (name, category, location_name, org_name)
    assets = [
        ("HVAC Unit RTU-04", "HVAC", "Victoria Island HQ", "JDAEM Enterprise Limited"),
        ("Forklift Charger FC-03", "Electrical", "Victoria Island HQ", "JDAEM Enterprise Limited"),
        ("Dock Leveler DL-07", "Mechanical", "Ikorodu Site Office", "JDAEM Enterprise Limited"),
        ("Backup Generator GEN-02", "Generator", "St. Mary Wing B", "Aurora Health Systems"),
        ("Boiler BLR-01", "HVAC", "St. Mary Wing B", "Aurora Health Systems"),
        ("Chiller CH-01", "HVAC", "Imaging Center", "Aurora Health Systems"),
        ("Conveyor Belt CB-11", "Mechanical", "Plant 3 - Packaging", "Cedar Foods Mfg."),
        ("Refrigeration Compressor RC-09", "Refrigeration", "Plant 1 - Cold Storage", "Cedar Foods Mfg."),
        ("Walk-in Cooler WC-02", "Refrigeration", "Store #214 - Denver", "Summit Retail Group"),
        ("Rooftop AC RTU-12", "HVAC", "Store #214 - Denver", "Summit Retail Group"),
    ]
    asset_ids = {}
    for name, category, location_name, org_name in assets:
        aid = new_id()
        now = datetime.utcnow()
        cur.execute(
            '''INSERT INTO "Asset" (id, name, category, status, "organizationId", "locationId", "createdAt", "updatedAt")
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s);''',
            (aid, name, category, "OPERATIONAL", org_ids[org_name], location_ids[location_name], now, now),
        )
        asset_ids[name] = aid
        print(f"  Asset: {name}")

    # ---- Work Orders (the tickets) ----
    # (title, description, priority, status, asset_name, location_name, org_name, days_ago)
    workorders = [
        (
            "HVAC Unit RTU-04 - Compressor overheating",
            "Compressor overheating, intermittent shutdowns during peak load.",
            "HIGH", "IN_PROGRESS",
            "HVAC Unit RTU-04", "Victoria Island HQ", "JDAEM Enterprise Limited", 8,
        ),
        (
            "Backup Generator GEN-02 - Self-test failure",
            "Generator failing weekly self-test, fault code E-17.",
            "HIGH", "OPEN",
            "Backup Generator GEN-02", "St. Mary Wing B", "Aurora Health Systems", 8,
        ),
        (
            "Conveyor Belt CB-11 - Tracking issue",
            "Belt tracking off-center, occasional product jams.",
            "MEDIUM", "OPEN",
            "Conveyor Belt CB-11", "Plant 3 - Packaging", "Cedar Foods Mfg.", 9,
        ),
        (
            "Dock Leveler DL-07 - Slow hydraulic rise",
            "Hydraulic leveler slow to rise.",
            "LOW", "COMPLETED",
            "Dock Leveler DL-07", "Ikorodu Site Office", "JDAEM Enterprise Limited", 10,
        ),
        (
            "Walk-in Cooler WC-02 - Temperature failure",
            "Cooler not holding temperature, reading 48°F.",
            "HIGH", "OPEN",
            "Walk-in Cooler WC-02", "Store #214 - Denver", "Summit Retail Group", 9,
        ),
        (
            "Chiller CH-01 - Abnormal vibration",
            "Chiller making abnormal noise, vibration alarm.",
            "MEDIUM", "IN_PROGRESS",
            "Chiller CH-01", "Imaging Center", "Aurora Health Systems", 10,
        ),
        (
            "Refrigeration Compressor RC-09 - Pressure fluctuation",
            "Pressure fluctuations on low side.",
            "MEDIUM", "OPEN",
            "Refrigeration Compressor RC-09", "Plant 1 - Cold Storage", "Cedar Foods Mfg.", 11,
        ),
        (
            "Rooftop AC RTU-12 - Routine service",
            "Routine filter replacement and inspection.",
            "LOW", "COMPLETED",
            "Rooftop AC RTU-12", "Store #214 - Denver", "Summit Retail Group", 12,
        ),
    ]
    for title, desc, priority, status, asset_name, location_name, org_name, days_ago in workorders:
        wid = new_id()
        created = datetime.utcnow() - timedelta(days=days_ago)
        now = datetime.utcnow()
        cur.execute(
            '''INSERT INTO "WorkOrder"
               (id, title, description, priority, status, "organizationId", "assetId", "locationId", "createdAt", "updatedAt")
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);''',
            (wid, title, desc, priority, status, org_ids[org_name], asset_ids[asset_name],
             location_ids[location_name], created, now),
        )
        print(f"  WorkOrder: {title}")

    conn.commit()
    print("\nSeed complete and committed.")

except Exception as e:
    conn.rollback()
    print(f"\nError during seeding, rolled back: {e}")
    raise

finally:
    cur.close()
    conn.close()

print("\nDone. Run check_db.py again to verify row counts.")