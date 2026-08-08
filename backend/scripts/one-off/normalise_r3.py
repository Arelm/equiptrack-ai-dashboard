import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()

APPLY = "--apply" in sys.argv
con = psycopg2.connect(os.environ["DATABASE_URL"])
cur = con.cursor()

cur.execute("""SELECT a.id, a.name FROM "Asset" a
               WHERE a.name LIKE '%Rm3%' ORDER BY a.name""")
rows = cur.fetchall()

print("APPLYING" if APPLY else "DRY RUN")
print("=" * 60)
for _id, name in rows:
    print(f"  {name}")
    print(f"    -> {name.replace('Rm3', 'R3')}")

print(f"\n{len(rows)} to rename")

if APPLY and rows:
    for _id, name in rows:
        cur.execute('UPDATE "Asset" SET name = %s, "updatedAt" = NOW() WHERE id = %s',
                    (name.replace("Rm3", "R3"), _id))
    con.commit()
    print("Committed.")
elif not APPLY:
    print("(re-run with --apply to write)")
con.close()
