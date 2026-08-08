import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()
cur.execute("""DELETE FROM "WorkOrder" WHERE id IN (%s, %s) RETURNING id, title""",
            ("e7c9472c-4019-4912-b679-91349c90dc4f",
             "a2a862cd-9d81-472b-820a-48f3edba2c69"))
for r in cur.fetchall():
    print("deleted", r)
con.commit(); con.close()
