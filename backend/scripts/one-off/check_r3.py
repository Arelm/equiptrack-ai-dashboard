import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()
cur.execute('''SELECT l.name, a.name FROM "Asset" a
               JOIN "Location" l ON a."locationId" = l.id
               WHERE a.name ILIKE '%R3%' OR a.name ILIKE '%Rm3%'
               ORDER BY l.name, a.name''')
for site, asset in cur.fetchall():
    print(f"  {site:<16} {asset}")
con.close()
