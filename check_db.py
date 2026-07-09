import sqlite3
c = sqlite3.connect('alfredo_memory.db')
print(c.execute('SELECT * FROM tv_configs').fetchall())
