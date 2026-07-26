import sqlite3
c=sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
c.execute("UPDATE tv_configs SET smartthings_pat='eab94ef2-cbde-4f36-932d-3047aabcbaf7', smartthings_device_id='0790dc88-66a9-455a-bd5b-99fdd43f54d6' WHERE ip_address='192.168.0.36'")
c.commit()
print("DB updated!")
