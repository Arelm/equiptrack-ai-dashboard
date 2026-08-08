import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()
cur.execute('''UPDATE "Asset" SET name = %s, "updatedAt" = NOW()
               WHERE name = %s RETURNING id, name''',
            ('264 · B7 · Rm3 — Panasonic 2HP', '2HP Panasonic at 264 F7B R3'))
row = cur.fetchone()
print(row if row else "no match - nothing changed")
con.commit(); con.close()
