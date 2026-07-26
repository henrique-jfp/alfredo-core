import sqlite3
c = sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
c.execute('''
UPDATE tv_configs 
SET mac_address = 'cc:20:ac:a0:74:b2',
    smartthings_device_id = '9254e132-ec14-186d-a217-04e978a30efd'
WHERE room_id = 'ROOM_LIVING'
''')
c.commit()
print("Updated DB!")
