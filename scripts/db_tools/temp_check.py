import sqlite3
conn = sqlite3.connect('alfredo_memory.db')
cursor = conn.cursor()
cursor.execute('SELECT input_text, output_text FROM interactions ORDER BY id DESC LIMIT 5')
for row in cursor.fetchall():
    try:
        print(row)
    except:
        print(str(row).encode('utf-8'))
