import sqlite3

try:
    conn = sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM timers')
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print('Erro:', e)
