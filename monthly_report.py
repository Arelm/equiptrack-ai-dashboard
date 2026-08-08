"""EquipTrack fault report.

Run with a date range. Fleet counts are taken at the moment the script runs,
not at PERIOD_END — so run it at month end for an accurate fleet number.

Faults come from filed reports only, because that is the only place a
diagnosis exists. Jobs closed without a report are counted separately so the
numbers reconcile.
"""
import os
import sys
import psycopg2

# --- Set the period here -------------------------------------------------
PERIOD_START = "2026-08-01"
PERIOD_END   = "2026-08-31"
# -------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# End date is inclusive of the whole day.
params = {"start": PERIOD_START, "end": PERIOD_END + " 23:59:59"}


def show(title):
    print("\n" + "=" * 62)
    print(title.upper())
    print("=" * 62)


# --- 1. Fleet ------------------------------------------------------------
show("Fleet")
cur.execute('SELECT count(*) FROM "Asset";')
total_assets = cur.fetchone()[0]
print(f"Total units under care: {total_assets}")

cur.execute('SELECT status, count(*) FROM "Asset" GROUP BY status ORDER BY 2 DESC;')
for status, n in cur.fetchall():
    print(f"  {status:<20} {n}")

cur.execute("""
    SELECT count(DISTINCT "assetId") FROM "MaintenanceLog"
    WHERE "createdAt" BETWEEN %(start)s AND %(end)s AND "assetId" IS NOT NULL;
""", params)
touched = cur.fetchone()[0]
pct = (touched / total_assets * 100) if total_assets else 0
print(f"\nUnits that needed attention this period: {touched} ({pct:.1f}% of fleet)")

# --- 2. Activity ---------------------------------------------------------
show("Activity")
cur.execute("""
    SELECT count(*) FROM "MaintenanceLog"
    WHERE "createdAt" BETWEEN %(start)s AND %(end)s;
""", params)
print(f"Reports filed: {cur.fetchone()[0]}")

cur.execute("""
    SELECT count(*) FROM "WorkOrder"
    WHERE "completedAt" BETWEEN %(start)s AND %(end)s;
""", params)
completed = cur.fetchone()[0]
print(f"Jobs completed: {completed}")

cur.execute("""
    SELECT count(*) FROM "WorkOrder" wo
    WHERE wo."completedAt" BETWEEN %(start)s AND %(end)s
      AND NOT EXISTS (
        SELECT 1 FROM "MaintenanceLog" ml WHERE ml."workOrderId" = wo.id
      );
""", params)
print(f"Closed without a report: {cur.fetchone()[0]}")

# --- 3. Fault ranking ----------------------------------------------------
show("Most recurring faults")
cur.execute("""
    SELECT "faultCategory", count(*) AS n
    FROM "MaintenanceLog"
    WHERE "createdAt" BETWEEN %(start)s AND %(end)s
      AND "faultCategory" IS NOT NULL
    GROUP BY "faultCategory"
    ORDER BY n DESC;
""", params)
rows = cur.fetchall()
if not rows:
    print("No categorised reports in this period.")
for i, (fault, n) in enumerate(rows, 1):
    print(f"{i:>2}. {fault:<24} {n}")

# --- 4. Repeat offenders -------------------------------------------------
show("Repeat offenders — same fault, same unit")
cur.execute("""
    SELECT a.name, l.name, ml."faultCategory", count(*) AS n
    FROM "MaintenanceLog" ml
    JOIN "Asset" a ON a.id = ml."assetId"
    LEFT JOIN "Location" l ON l.id = a."locationId"
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
      AND ml."faultCategory" IS NOT NULL
    GROUP BY a.name, l.name, ml."faultCategory"
    HAVING count(*) > 1
    ORDER BY n DESC;
""", params)
rows = cur.fetchall()
if not rows:
    print("None in this period.")
for asset, loc, fault, n in rows:
    print(f"{n}x  {fault:<24} {asset}  [{loc or 'no location'}]")

# --- 5. Workload ---------------------------------------------------------
show("Units by total jobs")
cur.execute("""
    SELECT a.name, l.name, count(*) AS n
    FROM "MaintenanceLog" ml
    JOIN "Asset" a ON a.id = ml."assetId"
    LEFT JOIN "Location" l ON l.id = a."locationId"
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
    GROUP BY a.name, l.name
    ORDER BY n DESC
    LIMIT 20;
""", params)
for i, (asset, loc, n) in enumerate(cur.fetchall(), 1):
    print(f"{i:>2}. {n:>3} jobs  {asset}  [{loc or 'no location'}]")

# --- 6. By location ------------------------------------------------------
show("By location")
cur.execute("""
    SELECT l.id, l.name, l.client
    FROM "Location" l
    WHERE l."isActive" IS NOT FALSE
    ORDER BY l.name;
""")
for loc_id, loc_name, client in cur.fetchall():
    p = dict(params, loc=loc_id)

    cur.execute("""
        SELECT count(*) FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s;
    """, p)
    jobs = cur.fetchone()[0]

    cur.execute('SELECT count(*) FROM "Asset" WHERE "locationId" = %s;', (loc_id,))
    units = cur.fetchone()[0]

    print(f"\n{loc_name}  ({client or 'no client'})  —  {units} units, {jobs} jobs")
    if jobs == 0:
        continue

    cur.execute("""
        SELECT ml."faultCategory", count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s
          AND ml."faultCategory" IS NOT NULL
        GROUP BY ml."faultCategory" ORDER BY n DESC LIMIT 5;
    """, p)
    for fault, n in cur.fetchall():
        print(f"    {n:>3}  {fault}")

    cur.execute("""
        SELECT a.name, count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s
        GROUP BY a.name ORDER BY n DESC LIMIT 3;
    """, p)
    print("    worst units:")
    for asset, n in cur.fetchall():
        print(f"      {n:>3} jobs  {asset}")

print()
cur.close()
conn.close()