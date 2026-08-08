import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()
cur.execute("""UPDATE "Asset"
               SET name = REPLACE(name, 'RM3', 'R3'), "updatedAt" = NOW()
               WHERE name LIKE '%RM3%'
               RETURNING name""")
for r in cur.fetchall():
    print("renamed ->", r[0])
con.commit(); con.close()
