import sqlite3

try:
    conn = sqlite3.connect("alfredo_memory.db")
    conn.execute("ALTER TABLE weather_cache ADD COLUMN max_temp VARCHAR")
except Exception as e:
    pass
try:
    conn.execute("ALTER TABLE weather_cache ADD COLUMN min_temp VARCHAR")
except Exception as e:
    pass
try:
    conn.execute("DELETE FROM weather_cache")
    conn.commit()
except Exception as e:
    pass
print("Done")
