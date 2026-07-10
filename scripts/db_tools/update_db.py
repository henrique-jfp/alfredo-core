import sqlite3
c = sqlite3.connect('alfredo_memory.db')
c.execute("UPDATE tv_configs SET smartthings_pat = 'a0808afb-8716-44fb-98aa-4c018dba1752' WHERE id = 1")
c.commit()
print("Atualizado")
