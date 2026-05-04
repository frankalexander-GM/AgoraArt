"""
Ejecuta este script para agregar la columna foto_banner a la base de datos.
Uso: python agregar_banner.py
"""
import sqlite3

db_path = 'app/art_platform_dev.db'
conn = sqlite3.connect(db_path)

# Verificar si la columna ya existe
cursor = conn.execute('PRAGMA table_info(usuarios)')
columnas = [row[1] for row in cursor.fetchall()]

if 'foto_banner' not in columnas:
    conn.execute('ALTER TABLE usuarios ADD COLUMN foto_banner VARCHAR(255)')
    conn.commit()
    print('✅ Columna foto_banner agregada correctamente')
else:
    print('ℹ️ La columna foto_banner ya existe')

conn.close()
