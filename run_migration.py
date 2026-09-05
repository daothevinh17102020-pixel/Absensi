# run_migration.py — Jalankan migration.sql via mysql-connector-python
# Penggunaan: python run_migration.py

import os
import re

import mysql.connector
from config import DB_CONFIG


def _safe_database_name():
    database_name = DB_CONFIG.get('database', '')
    if not re.fullmatch(r'[A-Za-z0-9_]+', database_name):
        raise ValueError('DB_NAME hanya boleh berisi huruf, angka, dan underscore.')
    return database_name


def _upgrade_absensi_schema(cursor, database_name):
    """Upgrade aman untuk database lama; boleh dijalankan berulang kali."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='absensi' AND COLUMN_NAME='alasan'
    """, (database_name,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE absensi ADD COLUMN alasan TEXT AFTER status")
        print("  [OK] Upgrade: absensi.alasan ditambahkan")

    cursor.execute("""
        SELECT COLUMN_TYPE
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='absensi' AND COLUMN_NAME='status'
    """, (database_name,))
    row = cursor.fetchone()
    if row and "'sakit'" not in row[0]:
        cursor.execute("""
            ALTER TABLE absensi
            MODIFY status ENUM('hadir','terlambat','izin','sakit','alpha') NOT NULL
        """)
        print("  [OK] Upgrade: status 'sakit' ditambahkan")

    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='absensi' AND COLUMN_NAME='buoi_so'
    """, (database_name,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE absensi ADD COLUMN buoi_so INT NOT NULL DEFAULT 1 AFTER status")
        print("  [OK] Upgrade: absensi.buoi_so ditambahkan")


def _upgrade_users_schema(cursor, database_name):
    """Pastikan kolom stt tersedia pada tabel users."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'
          AND COLUMN_NAME='stt'
    """, (database_name,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN stt INT DEFAULT NULL AFTER id
        """)
        print("  [OK] Upgrade: users.stt ditambahkan")


def _upgrade_jadwal_schema(cursor, database_name):
    """Pastikan kolom buoi_bat_dau tersedia pada tabel jadwal."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='jadwal'
          AND COLUMN_NAME='buoi_bat_dau'
    """, (database_name,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE jadwal
            ADD COLUMN buoi_bat_dau INT NOT NULL DEFAULT 1 AFTER batas_terlambat
        """)
        print("  [OK] Upgrade: jadwal.buoi_bat_dau ditambahkan")


def _upgrade_admin_schema(cursor, database_name):
    """Pastikan hanya satu akun admin awal dapat dibuat, termasuk saat race."""
    cursor.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME='admin'
          AND COLUMN_NAME='singleton_key'
    """, (database_name,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            ALTER TABLE admin
            ADD COLUMN singleton_key TINYINT NOT NULL DEFAULT 1 UNIQUE AFTER id
        """)
        print("  [OK] Upgrade: admin singleton constraint ditambahkan")

def run():
    # Koneksi tanpa database dulu (untuk CREATE DATABASE)
    cfg = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()

        database_name = _safe_database_name()
        try:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        except mysql.connector.Error as create_error:
            # Hosting terkelola sering melarang CREATE DATABASE, tetapi
            # database target sudah disediakan dan tetap boleh dipakai.
            try:
                cursor.execute(f"USE `{database_name}`")
            except mysql.connector.Error:
                raise create_error
        else:
            cursor.execute(f"USE `{database_name}`")
        print(f"  [OK] Database {database_name} siap")

        migration_path = os.path.join(os.path.dirname(__file__), 'migration.sql')
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql = f.read()

        # Pisah per statement berdasarkan semicolon
        statements = [s.strip() for s in sql.split(';') if s.strip()]

        failures = []
        for i, stmt in enumerate(statements, 1):
            # Bersihkan komentar baris
            lines = [l for l in stmt.split('\n') if not l.strip().startswith('--')]
            clean = '\n'.join(lines).strip()
            if not clean:
                continue
            try:
                cursor.execute(clean)
                conn.commit()
                if 'CREATE TABLE' in clean.upper():
                    # Ekstrak nama tabel
                    upper = clean.upper()
                    idx = upper.find('EXISTS') + 6 if 'EXISTS' in upper else upper.find('TABLE') + 5
                    nama = clean[idx:].strip().split('(')[0].strip()
                    print(f"  [OK] Tabel: {nama}")
                elif 'CREATE DATABASE' in clean.upper():
                    print(f"  [OK] Database {database_name} siap")
                elif 'USE ' in clean.upper():
                    print(f"  [OK] Menggunakan {database_name}")
            except mysql.connector.Error as e:
                print(f"  [!] Statement {i}: {e.msg}")
                failures.append((i, e.msg))

        if not failures:
            _upgrade_admin_schema(cursor, database_name)
            _upgrade_absensi_schema(cursor, database_name)
            _upgrade_users_schema(cursor, database_name)
            _upgrade_jadwal_schema(cursor, database_name)
            conn.commit()

        if failures:
            raise RuntimeError(f'Migration gagal pada {len(failures)} statement.')
        print("\n[DONE] Migration selesai!")
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    print("=" * 45)
    print("  MIGRATION - Sistem Absensi Face Recognition")
    print("=" * 45)
    run()
