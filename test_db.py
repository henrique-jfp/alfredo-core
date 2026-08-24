import sqlite3
conn=sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
for r in conn.execute('SELECT s.room_id, r.name, s.friendly_name, s.entity_id FROM smart_devices s JOIN rooms r ON s.room_id = r.room_id'): print(r)
