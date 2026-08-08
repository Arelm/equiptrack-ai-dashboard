import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
cur = psycopg2.connect(os.environ["DATABASE_URL"]).cursor()
cur.execute("SELECT typname FROM pg_type WHERE typname = 'FaultCategory'")
print("type exists:", cur.fetchall())
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name = 'MaintenanceLog' ORDER BY ordinal_position""")
print("MaintenanceLog:", [r[0] for r in cur.fetchall()])
