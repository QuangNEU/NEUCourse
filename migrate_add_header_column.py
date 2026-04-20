#!/usr/bin/env python
"""
Script para adicionar coluna header_content à tabela de_cuong_chi_tiet
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'neu_course.db')

if not os.path.exists(db_path):
    print(f"❌ Database não encontrada em {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar se coluna já existe
    cursor.execute("PRAGMA table_info(de_cuong_chi_tiet)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'header_content' in columns:
        print("✅ Coluna header_content já existe")
    else:
        print("Adicionando coluna header_content...")
        cursor.execute("""
            ALTER TABLE de_cuong_chi_tiet 
            ADD COLUMN header_content TEXT DEFAULT ''
        """)
        conn.commit()
        print("✅ Coluna header_content adicionada com sucesso")
    
    conn.close()
except sqlite3.Error as e:
    print(f"❌ Erro: {e}")
    exit(1)
