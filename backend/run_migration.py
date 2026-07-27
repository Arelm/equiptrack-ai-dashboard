"""Run a SQL migration against DATABASE_URL.

psql is not installed on this machine, so the migration goes through psycopg2
instead. Same SQL, same transaction, no install.

    railway run python backend/run_migration.py --check
    railway run python backend/run_migration.py --apply
"""

import argparse
import os
import sys

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATION = os.path.join(HERE, "migrations", "001_phase0.sql")

EXPECTED_TABLES = ["StockMovement", "AuditLog"]
EXPECTED_COLUMNS = [
    ("User", "passwordHash"),
    ("User", "phone"),
    ("User", "isActive"),
    ("WorkOrder", "assignedAt"),
    ("WorkOrder", "acceptedAt"),
    ("WorkOrder", "reportedAt"),
    ("WorkOrder", "isLegacy"),
    ("WorkOrderAssignment", "assignedBy"),
    ("WorkOrderAssignment", "acceptedAt"),
    ("WorkOrderAssignment", "unassignedAt"),
    ("WorkOrderAssignment", "reason"),
    ("MaintenanceLog", "partsUsedDeclared"),
    ("PartsUsed", "source"),
    ("PartsUsed", "partNameRaw"),
]


def report(conn) -> None:
    cur = conn.cursor()

    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY 1"
    )
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nTables in database: {len(tables)}")
    for t in tables:
        print(f"  {t}")

    print("\nMigration state:")
    for t in EXPECTED_TABLES:
        print(f"  table  {t:<24} {'present' if t in tables else 'MISSING'}")

    for table, column in EXPECTED_COLUMNS:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s",
            (table, column),
        )
        found = cur.fetchone() is not None
        print(f"  column {table}.{column:<22} {'present' if found else 'MISSING'}")

    # Row counts that matter for cutover.
    cur.execute('SELECT COUNT(*) FROM "WorkOrder"')
    print(f"\nWork orders: {cur.fetchone()[0]}")

    try:
        cur.execute('SELECT COUNT(*) FROM "WorkOrder" WHERE "isLegacy"')
        print(f"  flagged legacy: {cur.fetchone()[0]}")
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        print("  flagged legacy: (column does not exist yet)")

    cur.execute('SELECT COUNT(*) FROM "User"')
    total_users = cur.fetchone()[0]
    try:
        cur.execute('SELECT COUNT(*) FROM "User" WHERE "passwordHash" IS NOT NULL')
        print(f"\nUsers: {total_users}, with a password: {cur.fetchone()[0]}")
    except psycopg2.errors.UndefinedColumn:
        conn.rollback()
        print(f"\nUsers: {total_users} (passwordHash column does not exist yet)")

    cur.execute('SELECT COUNT(*) FROM "WorkOrderAssignment"')
    print(f"Assignment rows: {cur.fetchone()[0]}")
    cur.execute('SELECT COUNT(*) FROM "MaintenanceLog"')
    print(f"Field reports: {cur.fetchone()[0]}")
    cur.execute('SELECT COUNT(*) FROM "PartsUsed"')
    print(f"Parts-used rows: {cur.fetchone()[0]}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Report state, change nothing")
    ap.add_argument("--apply", action="store_true", help="Run the migration")
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set. Run this through: railway run python ...")
        return 1

    host = url.split("@")[-1].split("/")[0]
    print(f"Connecting to {host}")

    conn = psycopg2.connect(url)
    try:
        if not args.apply:
            report(conn)
            print("Read-only. Nothing was changed.")
            print("Re-run with --apply to run the migration.")
            return 0

        if not os.path.exists(MIGRATION):
            print(f"Migration file not found: {MIGRATION}")
            return 1

        with open(MIGRATION, encoding="utf-8") as f:
            sql = f.read()

        print(f"Applying {os.path.basename(MIGRATION)} ...")
        cur = conn.cursor()
        # The file carries its own BEGIN/COMMIT.
        cur.execute(sql)
        conn.commit()
        print("Applied and committed.\n")

        report(conn)
        return 0

    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"\nFAILED — rolled back, database unchanged.\n{type(exc).__name__}: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())