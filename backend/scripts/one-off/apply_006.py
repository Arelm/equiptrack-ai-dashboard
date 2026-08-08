import os, psycopg2, pathlib
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()

for f in ["migrations/005_fault_category.sql", "migrations/006_workorder_client_ticket.sql"]:
    sql = pathlib.Path(f).read_text(encoding="utf-8-sig")
    cur.execute(sql)
    print("applied", f)

con.commit()
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name = 'WorkOrder' ORDER BY ordinal_position""")
print("\nWorkOrder:", ", ".join(r[0] for r in cur.fetchall()))
con.close()
