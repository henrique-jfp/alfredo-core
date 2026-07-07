import sqlite3

try:
    conn = sqlite3.connect('alfredo_memory.db')
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE timers ADD COLUMN timer_type VARCHAR DEFAULT 'timer';")
    conn.commit()
    print("Success")
except Exception as e:
    print(e)
finally:
    conn.close()
