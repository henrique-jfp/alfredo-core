import sqlite3
import os

try:
    conn = sqlite3.connect('alfredo_memory.db')
    conn.execute('ALTER TABLE ai_usage ADD COLUMN latency_ms INTEGER DEFAULT 0;')
    conn.commit()
    print("Migrated successfully")
except Exception as e:
    print(f"Migration error: {e}")
finally:
    conn.close()
