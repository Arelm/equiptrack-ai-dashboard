"""
Quick inspection script — run this LOCALLY on your machine,
from inside your backend/ folder, where your real .env with DATABASE_URL lives.

Usage:
    cd backend
    pip install psycopg2-binary python-dotenv --break-system-packages
    python check_db.py

It prints row counts and a few sample rows for the key tables, then exits.
It never prints the connection string itself.
"""

import os
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()  # reads .env in current directory

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not found in environment. Make sure you're running this")
    print("from the backend/ folder with a .env file containing DATABASE_URL.")
    raise SystemExit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

tables = ["Organization", "Location", "Asset", "WorkOrder", "User"]

for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) AS count FROM "{table}";')
        count = cur.fetchone()["count"]
        print(f"\n{table}: {count} row(s)")

        if count > 0:
            cur.execute(f'SELECT * FROM "{table}" LIMIT 3;')
            rows = cur.fetchall()
            for row in rows:
                preview = {k: row[k] for k in list(row.keys())[:5]}
                print(f"  - {preview}")
    except Exception as e:
        print(f"\n{table}: error querying ({e})")
        conn.rollback()

cur.close()
conn.close()

print("\nDone. Paste this output back (no credentials are printed by this script).")