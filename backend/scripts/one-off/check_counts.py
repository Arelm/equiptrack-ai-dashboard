import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name = 'Asset' ORDER BY ordinal_position""")
cols = [r[0] for r in cur.fetchall()]
print("Asset columns:", ", ".join(cols))
fk = next((c for c in cols if c.lower() in ("locationid", "location_id")), None)
if not fk:
    raise SystemExit("no location FK found")
cur.execute(f'''SELECT l.name, COUNT(a.id) FROM "Location" l
                LEFT JOIN "Asset" a ON a."{fk}" = l.id
                GROUP BY l.name ORDER BY l.name''')
print()
for name, n in cur.fetchall():
    print(f"  {name:<24} {n}")
cur.execute('SELECT COUNT(*) FROM "Asset"')
print("\ntotal assets:", cur.fetchone()[0])
cur.execute('''SELECT name FROM "Asset" WHERE name ILIKE '%B7%' AND name ILIKE '%R%3%' ''')
print("B7 Rm3 matches:", [r[0] for r in cur.fetchall()] or "none")
con.close()
