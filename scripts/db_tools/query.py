import sqlite3

conn = sqlite3.connect("alfredo_memory.db")
conn.row_factory = sqlite3.Row

print("--- WEATHER CACHE ---")
try:
    for row in conn.execute("SELECT * FROM weather_cache ORDER BY id DESC LIMIT 1"):
        print(dict(row))
except Exception as e:
    print("Weather error:", e)

print("\n--- INTERACTIONS ---")
try:
    for row in conn.execute("SELECT id, device_id, input_text, output_text, timestamp FROM interactions ORDER BY id DESC LIMIT 15"):
        print(dict(row))
except Exception as e:
    print("Interactions error:", e)

conn.close()
