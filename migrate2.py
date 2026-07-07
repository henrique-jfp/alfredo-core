import sqlite3

try:
    conn = sqlite3.connect('alfredo_memory.db')
    conn.execute('ALTER TABLE devices ADD COLUMN volume INTEGER DEFAULT 70;')
    conn.execute('ALTER TABLE devices ADD COLUMN brightness INTEGER DEFAULT 50;')
    conn.commit()
    print("Migrated devices table successfully")
except Exception as e:
    print(f"Migration error: {e}")
finally:
    conn.close()
