import sqlite3
import os

db_path = os.path.join(os.path.expanduser("~"), "alfredo-core", "alfredo_memory.db")
print("Updating", db_path)
conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE timers ADD COLUMN timer_type VARCHAR DEFAULT 'timer'")
    conn.commit()
    print("DB updated successfully")
except Exception as e:
    print(e)
