import sqlite3
conn = sqlite3.connect('alfredo_memory.db')
print("tv_configs:", conn.execute("SELECT * FROM tv_configs").fetchall())
