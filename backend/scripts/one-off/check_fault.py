"""Verify faultCategory persisted on the most recent report."""
import os, sys, psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("""
    SELECT "workOrderId", "faultCategory", notes, "createdAt"
    FROM "MaintenanceLog"
    ORDER BY "createdAt" DESC
    LIMIT 3;
""")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()