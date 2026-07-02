"""Migração: cria tabela saved_locations e migra endereços antigos dos settings."""
import sqlite3
import os

db_path = os.path.expanduser("~/alfredo-core/alfredo_memory.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Criar tabela saved_locations se não existir
cursor.execute("""
CREATE TABLE IF NOT EXISTS saved_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    latitude VARCHAR NOT NULL,
    longitude VARCHAR NOT NULL,
    icon VARCHAR DEFAULT 'pin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("✓ Tabela saved_locations criada (ou já existia).")

# 2. Migrar endereços antigos dos settings
settings = {}
for row in cursor.execute("SELECT key, value FROM settings WHERE key IN ('home_lat', 'home_lon', 'work_lat', 'work_lon')"):
    settings[row[0]] = row[1]

if settings.get('home_lat') and settings.get('home_lon'):
    # Verifica se já não foi migrado
    existing = cursor.execute("SELECT id FROM saved_locations WHERE name = 'Casa'").fetchone()
    if not existing:
        cursor.execute(
            "INSERT INTO saved_locations (name, latitude, longitude, icon) VALUES (?, ?, ?, ?)",
            ('Casa', settings['home_lat'], settings['home_lon'], 'home')
        )
        print(f"✓ Migrado: Casa ({settings['home_lat']}, {settings['home_lon']})")
    else:
        print("→ Casa já existe, pulando.")

if settings.get('work_lat') and settings.get('work_lon'):
    existing = cursor.execute("SELECT id FROM saved_locations WHERE name = 'Trabalho'").fetchone()
    if not existing:
        cursor.execute(
            "INSERT INTO saved_locations (name, latitude, longitude, icon) VALUES (?, ?, ?, ?)",
            ('Trabalho', settings['work_lat'], settings['work_lon'], 'work')
        )
        print(f"✓ Migrado: Trabalho ({settings['work_lat']}, {settings['work_lon']})")
    else:
        print("→ Trabalho já existe, pulando.")

conn.commit()
conn.close()
print("\n✓ Migração concluída com sucesso!")
