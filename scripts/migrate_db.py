import sqlite3

try:
    conn = sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE timers ADD COLUMN timer_type VARCHAR DEFAULT 'timer'")
    conn.commit()
    print("Migração concluída com sucesso!")
except Exception as e:
    print('Erro:', e)
