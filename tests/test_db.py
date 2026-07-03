import sqlite3
import pprint

try:
    conn = sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
    cursor = conn.cursor()
    cursor.execute('SELECT key, value FROM settings')
    settings = cursor.fetchall()
    for row in settings:
        print(f"{row[0]}: {row[1]}")
except Exception as e:
    print('Erro:', e)
