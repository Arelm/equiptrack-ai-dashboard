"""
005 — Add FaultCategory enum and MaintenanceLog.faultCategory column.
Idempotent: safe to run more than once.
"""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set. Set it in this shell first, then re-run.")

CATEGORIES = [
    "REFRIGERANT_LEAKAGE",
    "LOW_REFRIGERANT",
    "CONDENSER_LEAKAGE",
    "EVAPORATOR_LEAKAGE",
    "COMPRESSOR_FAULT",
    "CAPACITOR_FAULT",
    "CONTACTOR_FAULT",
    "FAN_MOTOR_FAULT",
    "BLOWER_FAULT",
    "CAPILLARY_BLOCK",
    "FILTER_BLOCKED",
    "DRAINAGE_BLOCK",
    "AIRFLOW_DUCTING",
    "ELECTRICAL_SUPPLY",
    "LOW_VOLTAGE",
    "PANEL_FAULT",
    "THERMOSTAT_CONTROL",
    "ERROR_CODE",
    "ROUTINE_SERVICE",
    "OTHER",
]

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # --- pre-flight ---
    cur.execute("SELECT 1 FROM pg_type WHERE typname = 'FaultCategory';")
    enum_exists = cur.fetchone() is not None

    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'MaintenanceLog' AND column_name = 'faultCategory';
    """)
    col_exists = cur.fetchone() is not None

    print(f"Pre-flight: enum exists = {enum_exists}, column exists = {col_exists}")

    if enum_exists and col_exists:
        print("Nothing to do. Already migrated.")
        conn.rollback()
        sys.exit(0)

    # --- migrate ---
    if not enum_exists:
        values = ", ".join(f"'{c}'" for c in CATEGORIES)
        cur.execute(f'CREATE TYPE "FaultCategory" AS ENUM ({values});')
        print("Created enum FaultCategory.")

    if not col_exists:
        cur.execute(
            'ALTER TABLE "MaintenanceLog" ADD COLUMN "faultCategory" "FaultCategory";'
        )
        print("Added column MaintenanceLog.faultCategory.")

    # --- verify before commit ---
    cur.execute("""
        SELECT data_type, udt_name, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'MaintenanceLog' AND column_name = 'faultCategory';
    """)
    print("Verify:", cur.fetchone())

    cur.execute("""
        SELECT count(*) FROM pg_enum e
        JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = 'FaultCategory';
    """)
    print("Enum values:", cur.fetchone()[0], "(expected 20)")

    conn.commit()
    print("Committed.")

except Exception as e:
    conn.rollback()
    print("Rolled back. Error:", e)
    raise
finally:
    cur.close()
    conn.close()