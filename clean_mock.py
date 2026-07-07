import sqlite3

try:
    conn = sqlite3.connect('alfredo_memory.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices WHERE device_id='mock-pc-001';")
    conn.commit()
    print("Success")
except Exception as e:
    print(e)
finally:
    conn.close()
