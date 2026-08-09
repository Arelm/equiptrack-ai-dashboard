"""EquipTrack fault report.

Run with a date range. Fleet counts are taken at the moment the script runs,
not at PERIOD_END - so run it at month end for an accurate fleet number.

Faults come from filed reports only, because that is the only place a
diagnosis exists. Jobs closed without a report are counted separately so the
numbers reconcile.

Filters
-------
  --start / --end   explicit date range (YYYY-MM-DD)
  --month YYYY-MM   whole calendar month
  --year YYYY       whole calendar year
  --site NAME       one site, matched on name (partial, case-insensitive)
  --asset NAME      one asset or group, matched on name (partial)

Examples
--------
  python monthly_report.py --month 2026-08
  python monthly_report.py --year 2026
  python monthly_report.py --month 2026-08 --site 266
  python monthly_report.py --start 2026-01-01 --end 2026-06-30 --asset Daikin
"""

import argparse
import calendar
import os
import sys
from datetime import date

import psycopg2


# --- Arguments ------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="EquipTrack fault report")
    p.add_argument("--start", help="Start date, YYYY-MM-DD")
    p.add_argument("--end", help="End date, YYYY-MM-DD (inclusive)")
    p.add_argument("--month", help="Whole calendar month, YYYY-MM")
    p.add_argument("--year", help="Whole calendar year, YYYY")
    p.add_argument("--site", help="Filter to one site, matched on name")
    p.add_argument("--asset", help="Filter to assets whose name contains this")
    return p.parse_args()


def resolve_period(args):
    """Work out the reporting window. Defaults to the current month."""
    if args.month:
        y, m = (int(x) for x in args.month.split("-"))
        last = calendar.monthrange(y, m)[1]
        return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"

    if args.year:
        y = int(args.year)
        return f"{y:04d}-01-01", f"{y:04d}-12-31"

    if args.start and args.end:
        return args.start, args.end

    if args.start or args.end:
        sys.exit("Give both --start and --end, or use --month / --year.")

    today = date.today()
    last = calendar.monthrange(today.year, today.month)[1]
    return (
        f"{today.year:04d}-{today.month:02d}-01",
        f"{today.year:04d}-{today.month:02d}-{last:02d}",
    )


args = parse_args()
PERIOD_START, PERIOD_END = resolve_period(args)

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


# --- Resolve the site / asset filter to a list of asset ids ---------------
# Every query below then filters the same way, so the sections stay
# consistent with each other no matter which filter is applied.
FILTERED = bool(args.site or args.asset)
location_ids = None
asset_ids = None

if args.site:
    cur.execute(
        'SELECT id, name FROM "Location" WHERE name ILIKE %s ORDER BY name;',
        (f"%{args.site}%",),
    )
    hits = cur.fetchall()
    if not hits:
        sys.exit(f"No site matches '{args.site}'.")
    location_ids = [h[0] for h in hits]
    site_label = ", ".join(h[1] for h in hits)
else:
    site_label = "all sites"

asset_sql = 'SELECT id FROM "Asset" WHERE TRUE'
asset_params = []
if location_ids:
    asset_sql += ' AND "locationId" = ANY(%s)'
    asset_params.append(location_ids)
if args.asset:
    asset_sql += " AND name ILIKE %s"
    asset_params.append(f"%{args.asset}%")

if FILTERED:
    cur.execute(asset_sql + ";", asset_params)
    asset_ids = [r[0] for r in cur.fetchall()]
    if not asset_ids:
        sys.exit("No assets match that filter.")
    params["assets"] = asset_ids

# SQL fragments that are empty when no filter is active.
ML_F = ' AND ml."assetId" = ANY(%(assets)s)' if FILTERED else ""
WO_F = ' AND wo."assetId" = ANY(%(assets)s)' if FILTERED else ""

asset_label = args.asset if args.asset else "all assets"

print(f"Period : {PERIOD_START} to {PERIOD_END}")
print(f"Site   : {site_label}")
print(f"Asset  : {asset_label}")

# --- 1. Fleet -------------------------------------------------------------
show("Fleet")
if FILTERED:
    cur.execute('SELECT count(*) FROM "Asset" WHERE id = ANY(%(assets)s);', params)
else:
    cur.execute('SELECT count(*) FROM "Asset";')
total_assets = cur.fetchone()[0]
print(f"Total units under care: {total_assets}")

if FILTERED:
    cur.execute(
        'SELECT status, count(*) FROM "Asset" WHERE id = ANY(%(assets)s)'
        " GROUP BY status ORDER BY 2 DESC;",
        params,
    )
else:
    cur.execute('SELECT status, count(*) FROM "Asset" GROUP BY status ORDER BY 2 DESC;')
for status, n in cur.fetchall():
    print(f"  {status:<20} {n}")

cur.execute(
    f"""
    SELECT count(DISTINCT ml."assetId") FROM "MaintenanceLog" ml
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
      AND ml."assetId" IS NOT NULL{ML_F};
""",
    params,
)
touched = cur.fetchone()[0]
pct = (touched / total_assets * 100) if total_assets else 0
print(f"\nUnits that needed attention this period: {touched} ({pct:.1f}% of fleet)")

# --- 2. Activity ----------------------------------------------------------
show("Activity")
cur.execute(
    f"""
    SELECT count(*) FROM "MaintenanceLog" ml
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s{ML_F};
""",
    params,
)
print(f"Reports filed: {cur.fetchone()[0]}")

cur.execute(
    f"""
    SELECT count(*) FROM "WorkOrder" wo
    WHERE wo."completedAt" BETWEEN %(start)s AND %(end)s{WO_F};
""",
    params,
)
completed = cur.fetchone()[0]
print(f"Jobs completed: {completed}")

cur.execute(
    f"""
    SELECT count(*) FROM "WorkOrder" wo
    WHERE wo."completedAt" BETWEEN %(start)s AND %(end)s{WO_F}
      AND NOT EXISTS (
        SELECT 1 FROM "MaintenanceLog" ml WHERE ml."workOrderId" = wo.id
      );
""",
    params,
)
print(f"Closed without a report: {cur.fetchone()[0]}")

# --- 3. Fault ranking -----------------------------------------------------
show("Most recurring faults")
cur.execute(
    f"""
    SELECT ml."faultCategory", count(*) AS n
    FROM "MaintenanceLog" ml
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
      AND ml."faultCategory" IS NOT NULL{ML_F}
    GROUP BY ml."faultCategory"
    ORDER BY n DESC;
""",
    params,
)
rows = cur.fetchall()
if not rows:
    print("No categorised reports in this period.")
for i, (fault, n) in enumerate(rows, 1):
    print(f"{i:>2}. {fault:<24} {n}")

# --- 4. Repeat offenders --------------------------------------------------
show("Repeat offenders - same fault, same unit")
cur.execute(
    f"""
    SELECT a.name, l.name, ml."faultCategory", count(*) AS n
    FROM "MaintenanceLog" ml
    JOIN "Asset" a ON a.id = ml."assetId"
    LEFT JOIN "Location" l ON l.id = a."locationId"
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s
      AND ml."faultCategory" IS NOT NULL{ML_F}
    GROUP BY a.name, l.name, ml."faultCategory"
    HAVING count(*) > 1
    ORDER BY n DESC;
""",
    params,
)
rows = cur.fetchall()
if not rows:
    print("None in this period.")
for asset, loc, fault, n in rows:
    print(f"{n}x  {fault:<24} {asset}  [{loc or 'no location'}]")

# --- 5. Workload ----------------------------------------------------------
show("Units by total jobs")
cur.execute(
    f"""
    SELECT a.name, l.name, count(*) AS n
    FROM "MaintenanceLog" ml
    JOIN "Asset" a ON a.id = ml."assetId"
    LEFT JOIN "Location" l ON l.id = a."locationId"
    WHERE ml."createdAt" BETWEEN %(start)s AND %(end)s{ML_F}
    GROUP BY a.name, l.name
    ORDER BY n DESC
    LIMIT 20;
""",
    params,
)
for i, (asset, loc, n) in enumerate(cur.fetchall(), 1):
    print(f"{i:>2}. {n:>3} jobs  {asset}  [{loc or 'no location'}]")

# --- 6. By location -------------------------------------------------------
show("By location")
loc_sql = 'SELECT l.id, l.name, l.client FROM "Location" l WHERE l."isActive" IS NOT FALSE'
loc_params = []
if location_ids:
    loc_sql += " AND l.id = ANY(%s)"
    loc_params.append(location_ids)
loc_sql += " ORDER BY l.name;"
cur.execute(loc_sql, loc_params)

for loc_id, loc_name, client in cur.fetchall():
    p = dict(params, loc=loc_id)

    cur.execute(
        f"""
        SELECT count(*) FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s{ML_F};
    """,
        p,
    )
    jobs = cur.fetchone()[0]

    if FILTERED:
        cur.execute(
            'SELECT count(*) FROM "Asset" WHERE "locationId" = %s'
            " AND id = ANY(%s);",
            (loc_id, asset_ids),
        )
    else:
        cur.execute('SELECT count(*) FROM "Asset" WHERE "locationId" = %s;', (loc_id,))
    units = cur.fetchone()[0]

    print(f"\n{loc_name}  ({client or 'no client'})  -  {units} units, {jobs} jobs")
    if jobs == 0:
        continue

    cur.execute(
        f"""
        SELECT ml."faultCategory", count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s
          AND ml."faultCategory" IS NOT NULL{ML_F}
        GROUP BY ml."faultCategory" ORDER BY n DESC LIMIT 5;
    """,
        p,
    )
    for fault, n in cur.fetchall():
        print(f"    {n:>3}  {fault}")

    cur.execute(
        f"""
        SELECT a.name, count(*) AS n
        FROM "MaintenanceLog" ml
        JOIN "Asset" a ON a.id = ml."assetId"
        WHERE a."locationId" = %(loc)s
          AND ml."createdAt" BETWEEN %(start)s AND %(end)s{ML_F}
        GROUP BY a.name ORDER BY n DESC LIMIT 3;
    """,
        p,
    )
    print("    worst units:")
    for asset, n in cur.fetchall():
        print(f"      {n:>3} jobs  {asset}")

print()
cur.close()
conn.close()
