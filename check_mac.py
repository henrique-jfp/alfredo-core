import sqlite3
c=sqlite3.connect('/home/pvserver/alfredo-core/alfredo_memory.db')
mac = c.execute("SELECT mac_address FROM tv_configs WHERE ip_address='192.168.0.36'").fetchone()
print(f"MAC: {mac}")
