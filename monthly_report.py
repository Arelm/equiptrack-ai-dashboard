"""EquipTrack fault report - terminal output.

Run with a date range. Fleet counts are taken at the moment the script runs,
not at the end of the period - so run it at month end for an accurate fleet
number.

The queries live in report_data.py. This file only prints.

Filters
-------
  --start / --end   explicit date range (YYYY-MM-DD)
  --month YYYY-MM   whole calendar month
  --year YYYY       whole calendar year
  --site NAME       one site, matched on name (partial, case-insensitive)
  --asset NAME      one asset or group, matched on name (partial)
  --csv PATH        also write the tables to CSV files alongside PATH

Examples
--------
  python monthly_report.py --month 2026-08
  python monthly_report.py --year 2026
  python monthly_report.py --month 2026-08 --site 266
  python monthly_report.py --start 2026-01-01 --end 2026-06-30 --asset Daikin
"""

import argparse
import csv
import os
import sys

import psycopg2

from backend.report_data import FilterError, collect_report, resolve_period


def parse_args():
    p = argparse.ArgumentParser(description="EquipTrack fault report")
    p.add_argument("--start", help="Start date, YYYY-MM-DD")
    p.add_argument("--end", help="End date, YYYY-MM-DD (inclusive)")
    p.add_argument("--month", help="Whole calendar month, YYYY-MM")
    p.add_argument("--year", help="Whole calendar year, YYYY")
    p.add_argument("--site", help="Filter to one site, matched on name")
    p.add_argument("--asset", help="Filter to assets whose name contains this")
    p.add_argument("--csv", help="Write the tables to CSV files with this prefix")
    return p.parse_args()


def show(title):
    print("\n" + "=" * 62)
    print(title.upper())
    print("=" * 62)


def render_text(d):
    print(f"Period : {d['period']['start']} to {d['period']['end']}")
    print(f"Site   : {d['filters']['site_label']}")
    print(f"Asset  : {d['filters']['asset_label']}")

    show("Fleet")
    fleet = d["fleet"]
    print(f"Total units under care: {fleet['total']}")
    for row in fleet["by_status"]:
        print(f"  {row['status']:<20} {row['count']}")
    print(
        f"\nUnits that needed attention this period: {fleet['touched']}"
        f" ({fleet['touched_pct']:.1f}% of fleet)"
    )

    show("Activity")
    act = d["activity"]
    print(f"Reports filed: {act['reports_filed']}")
    print(f"Jobs completed: {act['jobs_completed']}")
    print(f"Closed without a report: {act['closed_without_report']}")

    show("Most recurring faults")
    if not d["faults"]:
        print("No categorised reports in this period.")
    for i, row in enumerate(d["faults"], 1):
        print(f"{i:>2}. {row['category']:<24} {row['count']}")

    show("Repeat offenders - same fault, same unit")
    if not d["repeat_offenders"]:
        print("None in this period.")
    for row in d["repeat_offenders"]:
        loc = row["location"] or "no location"
        print(f"{row['count']}x  {row['category']:<24} {row['asset']}  [{loc}]")

    show("Units by total jobs")
    for i, row in enumerate(d["workload"], 1):
        loc = row["location"] or "no location"
        print(f"{i:>2}. {row['jobs']:>3} jobs  {row['asset']}  [{loc}]")

    show("By location")
    for loc in d["locations"]:
        client = loc["client"] or "no client"
        print(
            f"\n{loc['name']}  ({client})  -  {loc['units']} units, {loc['jobs']} jobs"
        )
        if not loc["jobs"]:
            continue
        for row in loc["faults"]:
            print(f"    {row['count']:>3}  {row['category']}")
        print("    worst units:")
        for row in loc["worst_units"]:
            print(f"      {row['jobs']:>3} jobs  {row['asset']}")

    print()


def write_csv(d, prefix):
    """Write each table to its own CSV file, named from the prefix."""
    base, _ = os.path.splitext(prefix)
    written = []

    tables = {
        "faults": (["category", "count"], d["faults"]),
        "repeat-offenders": (
            ["asset", "location", "category", "count"],
            d["repeat_offenders"],
        ),
        "workload": (["asset", "location", "jobs"], d["workload"]),
        "locations": (
            ["name", "client", "units", "jobs"],
            [
                {k: loc[k] for k in ("name", "client", "units", "jobs")}
                for loc in d["locations"]
            ],
        ),
    }

    for name, (fields, rows) in tables.items():
        path = f"{base}-{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        written.append(path)

    # Summary is a single row, so it gets a key/value shape instead.
    path = f"{base}-summary.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["field", "value"])
        w.writerow(["period_start", d["period"]["start"]])
        w.writerow(["period_end", d["period"]["end"]])
        w.writerow(["site", d["filters"]["site_label"]])
        w.writerow(["asset", d["filters"]["asset_label"]])
        w.writerow(["total_units", d["fleet"]["total"]])
        w.writerow(["units_touched", d["fleet"]["touched"]])
        w.writerow(["reports_filed", d["activity"]["reports_filed"]])
        w.writerow(["jobs_completed", d["activity"]["jobs_completed"]])
        w.writerow(
            ["closed_without_report", d["activity"]["closed_without_report"]]
        )
    written.append(path)

    print("CSV written:")
    for p in written:
        print(f"  {p}")


def main():
    args = parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL not set.")

    try:
        start, end = resolve_period(
            start=args.start, end=args.end, month=args.month, year=args.year
        )
    except FilterError as e:
        sys.exit(str(e))

    conn = psycopg2.connect(database_url)
    try:
        data = collect_report(conn, start, end, site=args.site, asset=args.asset)
    except FilterError as e:
        sys.exit(str(e))
    finally:
        conn.close()

    render_text(data)

    if args.csv:
        write_csv(data, args.csv)


if __name__ == "__main__":
    main()
