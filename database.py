# database.py — Semua fungsi query database
# Tidak boleh ada query langsung di app.py (lihat context.md bagian 12)

import mysql.connector
from config import (ABSENSI_GRACE_MINUTES, APP_TIMEZONE, DB_CONFIG,
                    TOLERANSI_MENIT)
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


APP_TZ = ZoneInfo(APP_TIMEZONE)


def _now_app():
    return datetime.now(APP_TZ)


def get_connection():
    """Buat koneksi baru ke MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


class DatabaseQueryError(RuntimeError):
    """Raised by strict scanner queries when the database is unavailable."""


# ══════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════

def hitung_admin():
    """Hitung jumlah admin di database. Return 0 jika gagal."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM admin")
        hasil = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return 0


def tambah_admin(username, password_hash):
    """Simpan admin baru. Return id admin atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT kelas_id FROM matakuliah WHERE id = %s",
            (matakuliah_id,)
        )
        matakuliah = cursor.fetchone()
        if not matakuliah:
            return None

        cursor.execute("""
            SELECT j.id
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE m.kelas_id = %s
              AND j.hari = %s
              AND %s < ADDTIME(j.jam_selesai, SEC_TO_TIME(%s * 60))
              AND ADDTIME(%s, SEC_TO_TIME(%s * 60)) > j.jam_mulai
            LIMIT 1
        """, (
            matakuliah['kelas_id'], hari,
            jam_mulai, ABSENSI_GRACE_MINUTES,
            jam_selesai, ABSENSI_GRACE_MINUTES
        ))
        if cursor.fetchone():
            return None

        cursor.execute(
            "INSERT INTO admin (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        conn.commit()
        admin_id = cursor.lastrowid
        cursor.close(); conn.close()
        return admin_id
    except Exception:
        return None


def get_admin_by_username(username):
    """Ambil data admin berdasarkan username. Return dict atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# KELAS
# ══════════════════════════════════════════════════════════════

def get_semua_kelas():
    """Ambil semua kelas. Return list dict atau []."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM kelas ORDER BY nama_kelas")
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def get_kelas_by_id(kelas_id):
    """Ambil satu kelas berdasarkan id. Return dict atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM kelas WHERE id = %s", (kelas_id,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return None


def tambah_kelas(nama_kelas, angkatan, dibuat_oleh=None):
    """Simpan kelas baru. Return id kelas atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO kelas (nama_kelas, angkatan, dibuat_oleh) VALUES (%s, %s, %s)",
            (nama_kelas, angkatan, dibuat_oleh)
        )
        conn.commit()
        kelas_id = cursor.lastrowid
        cursor.close(); conn.close()
        return kelas_id
    except Exception:
        return None


def update_kelas(kelas_id, nama_kelas, angkatan):
    """Update data kelas. Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE kelas SET nama_kelas = %s, angkatan = %s WHERE id = %s",
            (nama_kelas, angkatan, kelas_id)
        )
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def hapus_kelas(kelas_id):
    """Hapus kelas (CASCADE ke matakuliah/jadwal). Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kelas WHERE id = %s", (kelas_id,))
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def hitung_mahasiswa_per_kelas(kelas_id):
    """Hitung jumlah mahasiswa di satu kelas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE kelas_id = %s", (kelas_id,))
        hasil = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return 0


# ══════════════════════════════════════════════════════════════
# MATAKULIAH
# ══════════════════════════════════════════════════════════════

def get_semua_matakuliah():
    """Ambil semua matakuliah dengan nama kelas. Return list dict."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.*, k.nama_kelas
            FROM matakuliah m
            JOIN kelas k ON m.kelas_id = k.id
            ORDER BY m.nama_mk
        """)
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def get_matakuliah_by_kelas(kelas_id):
    """Ambil matakuliah berdasarkan kelas_id."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM matakuliah WHERE kelas_id = %s ORDER BY nama_mk",
            (kelas_id,)
        )
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def get_matakuliah_by_id(mk_id):
    """Ambil satu matakuliah."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM matakuliah WHERE id = %s", (mk_id,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return None


def tambah_matakuliah(nama_mk, kode_mk, kelas_id, sks=2):
    """Simpan matakuliah baru. Return id atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO matakuliah (nama_mk, kode_mk, kelas_id, sks) VALUES (%s,%s,%s,%s)",
            (nama_mk, kode_mk, kelas_id, sks)
        )
        conn.commit()
        mk_id = cursor.lastrowid
        cursor.close(); conn.close()
        return mk_id
    except Exception:
        return None


def update_matakuliah(mk_id, nama_mk, kode_mk, kelas_id, sks):
    """Update matakuliah. Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE matakuliah SET nama_mk=%s, kode_mk=%s, kelas_id=%s, sks=%s WHERE id=%s",
            (nama_mk, kode_mk, kelas_id, sks, mk_id)
        )
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def hapus_matakuliah(mk_id):
    """Hapus matakuliah (CASCADE ke jadwal). Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM matakuliah WHERE id = %s", (mk_id,))
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# JADWAL
# ══════════════════════════════════════════════════════════════

def get_semua_jadwal():
    """Ambil semua jadwal lengkap dengan nama MK dan kelas."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, m.nama_mk, m.kode_mk, k.nama_kelas
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            ORDER BY FIELD(j.hari,'Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'),
                     j.jam_mulai
        """)
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def get_jadwal_by_id(jadwal_id):
    """Ambil satu jadwal."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, m.nama_mk, m.kode_mk, m.kelas_id, k.nama_kelas
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE j.id = %s
        """, (jadwal_id,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return None


def get_jadwal_hari(hari):
    """Ambil semua jadwal pada satu hari untuk dropdown/API."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.id, j.hari, j.jam_mulai, j.jam_selesai,
                   m.nama_mk, m.kelas_id, k.nama_kelas
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE j.hari = %s
            ORDER BY j.jam_mulai
        """, (hari,))
        return cursor.fetchall()
    except Exception:
        return []

def update_jadwal(jadwal_id, matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat=None):
    """Update jadwal. Return True/False."""
    conn = None
    cursor = None
    try:
        if batas_terlambat is None:
            fmt = "%H:%M:%S" if len(str(jam_mulai)) > 5 else "%H:%M"
            mulai_dt = datetime.strptime(str(jam_mulai), fmt)
            batas_dt = mulai_dt + timedelta(minutes=TOLERANSI_MENIT)
            batas_terlambat = batas_dt.strftime("%H:%M:%S")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE jadwal
               SET matakuliah_id=%s, hari=%s, jam_mulai=%s, jam_selesai=%s, batas_terlambat=%s
               WHERE id=%s""",
            (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat, jadwal_id)
        )
        conn.commit()
        return True
    except Exception:
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()



def tambah_jadwal(matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat=None):
    """Simpan jadwal baru. batas_terlambat otomatis jika None."""
    conn = None
    cursor = None
    try:
        if batas_terlambat is None:
            # Hitung otomatis dari konfigurasi sistem.
            fmt = "%H:%M:%S" if len(str(jam_mulai)) > 5 else "%H:%M"
            mulai_dt = datetime.strptime(str(jam_mulai), fmt)
            batas_dt = mulai_dt + timedelta(minutes=TOLERANSI_MENIT)
            batas_terlambat = batas_dt.strftime("%H:%M:%S")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO jadwal (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat)
               VALUES (%s, %s, %s, %s, %s)""",
            (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat)
        )
        conn.commit()
        jadwal_id = cursor.lastrowid
        return jadwal_id
    except Exception:
        if conn:
            conn.rollback()
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def hapus_jadwal(jadwal_id):
    """Hapus jadwal. Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jadwal WHERE id = %s", (jadwal_id,))
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def get_jadwal_aktif(hari, waktu_sekarang, raise_on_error=False):
    """Cari jadwal aktif sampai batas grace period setelah kelas selesai."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, m.nama_mk, m.kelas_id
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE j.hari = %s
              AND %s >= j.jam_mulai
              AND %s <= ADDTIME(j.jam_selesai, SEC_TO_TIME(%s * 60))
            ORDER BY j.jam_mulai DESC, j.id DESC
        """, (hari, waktu_sekarang, waktu_sekarang, ABSENSI_GRACE_MINUTES))
        hasil = cursor.fetchall()
        return hasil
    except Exception as exc:
        if raise_on_error:
            raise DatabaseQueryError('get_jadwal_aktif failed') from exc
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ══════════════════════════════════════════════════════════════
# USERS (MAHASISWA)
# ══════════════════════════════════════════════════════════════

def get_semua_user():
    """Ambil semua mahasiswa dengan nama kelas."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*, k.nama_kelas
            FROM users u
            JOIN kelas k ON u.kelas_id = k.id
            ORDER BY u.nama
        """)
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def get_user_by_id(user_id, raise_on_error=False):
    """Ambil satu mahasiswa."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*, k.nama_kelas
            FROM users u
            JOIN kelas k ON u.kelas_id = k.id
            WHERE u.id = %s
        """, (user_id,))
        hasil = cursor.fetchone()
        return hasil
    except Exception as exc:
        if raise_on_error:
            raise DatabaseQueryError('get_user_by_id failed') from exc
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_user_by_nim(nim):
    """Cari mahasiswa berdasarkan NIM."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE nim = %s", (nim,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return None


def get_users_by_kelas(kelas_id):
    """Ambil semua mahasiswa di satu kelas."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE kelas_id = %s ORDER BY nama",
            (kelas_id,)
        )
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def tambah_user(nama, nim, kelas_id, foto_path=None):
    """Simpan mahasiswa baru. Return id user atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (nama, nim, kelas_id, foto_path) VALUES (%s,%s,%s,%s)",
            (nama, nim, kelas_id, foto_path)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close(); conn.close()
        return user_id
    except Exception:
        return None


def update_user(user_id, nama, nim, kelas_id, foto_path=None):
    """Update data mahasiswa. Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if foto_path:
            cursor.execute(
                "UPDATE users SET nama=%s, nim=%s, kelas_id=%s, foto_path=%s WHERE id=%s",
                (nama, nim, kelas_id, foto_path, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET nama=%s, nim=%s, kelas_id=%s WHERE id=%s",
                (nama, nim, kelas_id, user_id)
            )
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def hapus_user(user_id):
    """Hapus mahasiswa (CASCADE ke absensi). Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def nim_sudah_ada(nim):
    """Cek apakah NIM sudah terdaftar."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE nim = %s", (nim,))
        hasil = cursor.fetchone()
        cursor.close(); conn.close()
        return hasil is not None
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# ABSENSI
# ══════════════════════════════════════════════════════════════

def catat_absensi(user_id, jadwal_id, tanggal, waktu_absen, status,
                  snapshot_path=None, dibuat_manual=False, alasan=None,
                  raise_on_error=False):
    """Simpan record absensi. Return id atau None (duplikat/gagal)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO absensi
               (user_id, jadwal_id, tanggal, waktu_absen, status, alasan, snapshot_path, dibuat_manual)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, jadwal_id, tanggal, waktu_absen, status,
             alasan, snapshot_path, dibuat_manual)
        )
        conn.commit()
        absensi_id = cursor.lastrowid
        return absensi_id
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[DB] Error catat_absensi: {e}')
        if raise_on_error:
            raise DatabaseQueryError('catat_absensi failed') from e
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def catat_absensi_manual(user_id, jadwal_id, tanggal, status, alasan=None):
    """Absen manual oleh admin: insert baru atau update jika sudah ada.
    Berguna untuk izin/sakit atau koreksi status.
    Return dict {'aksi': 'insert'/'update', 'id': absensi_id} atau None.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Cek apakah sudah ada record absensi
        cursor.execute(
            "SELECT id, status FROM absensi WHERE user_id=%s AND jadwal_id=%s AND tanggal=%s",
            (user_id, jadwal_id, tanggal)
        )
        existing = cursor.fetchone()

        waktu_now = _now_app().strftime('%H:%M:%S')

        if existing:
            # Update record yang sudah ada
            cursor.execute(
                """UPDATE absensi SET status=%s, alasan=%s, dibuat_manual=TRUE,
                   waktu_absen=%s WHERE id=%s""",
                (status, alasan, waktu_now, existing['id'])
            )
            conn.commit()
            return {'aksi': 'update', 'id': existing['id'], 'status_lama': existing['status']}
        else:
            # Insert baru
            cursor.execute(
                """INSERT INTO absensi
                   (user_id, jadwal_id, tanggal, waktu_absen, status, alasan, dibuat_manual)
                   VALUES (%s, %s, %s, %s, %s, %s, TRUE)""",
                (user_id, jadwal_id, tanggal, waktu_now, status, alasan)
            )
            conn.commit()
            absensi_id = cursor.lastrowid
            return {'aksi': 'insert', 'id': absensi_id}
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[DB] Error catat_absensi_manual: {e}')
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def cek_sudah_absen(user_id, jadwal_id, tanggal, raise_on_error=False):
    """Cek apakah mahasiswa sudah absen di jadwal ini hari ini."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM absensi WHERE user_id=%s AND jadwal_id=%s AND tanggal=%s",
            (user_id, jadwal_id, tanggal)
        )
        hasil = cursor.fetchone()
        return hasil
    except Exception as exc:
        if raise_on_error:
            raise DatabaseQueryError('cek_sudah_absen failed') from exc
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_absensi_hari_ini(tanggal=None):
    """Ambil semua absensi hari ini lengkap dengan data mahasiswa."""
    tanggal = tanggal or _now_app().date()
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.nama, u.nim, k.nama_kelas,
                   m.nama_mk, j.jam_mulai, j.jam_selesai
            FROM absensi a
            JOIN users u ON a.user_id = u.id
            JOIN jadwal j ON a.jadwal_id = j.id
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE a.tanggal = %s
            ORDER BY a.waktu_absen DESC
        """, (tanggal,))
        hasil = cursor.fetchall()
        return hasil
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_rekap_absensi(kelas_id=None, tanggal_dari=None, tanggal_sampai=None,
                      matakuliah_id=None):
    """Ambil rekap absensi dengan filter opsional."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.*, u.nama, u.nim, k.nama_kelas,
                   m.nama_mk, m.kode_mk, j.hari, j.jam_mulai
            FROM absensi a
            JOIN users u ON a.user_id = u.id
            JOIN jadwal j ON a.jadwal_id = j.id
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE 1=1
        """
        params = []

        if kelas_id:
            query += " AND m.kelas_id = %s"
            params.append(kelas_id)
        if tanggal_dari:
            query += " AND a.tanggal >= %s"
            params.append(tanggal_dari)
        if tanggal_sampai:
            query += " AND a.tanggal <= %s"
            params.append(tanggal_sampai)
        if matakuliah_id:
            query += " AND j.matakuliah_id = %s"
            params.append(matakuliah_id)

        query += " ORDER BY a.tanggal DESC, a.waktu_absen DESC"

        cursor.execute(query, params)
        hasil = cursor.fetchall()
        return hasil
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def update_status_absensi(absensi_id, status_baru):
    """Update status absensi (untuk absensi manual). Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE absensi SET status = %s, dibuat_manual = TRUE WHERE id = %s",
            (status_baru, absensi_id)
        )
        conn.commit()
        cursor.close(); conn.close()
        return True
    except Exception:
        return False


def get_persentase_kehadiran(kelas_id=None, tanggal_dari=None, tanggal_sampai=None):
    """Hitung persentase kehadiran per status. Return dict."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT status, COUNT(*) as jumlah
            FROM absensi a
            JOIN jadwal j ON a.jadwal_id = j.id
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE 1=1
        """
        params = []
        if kelas_id:
            query += " AND m.kelas_id = %s"
            params.append(kelas_id)
        if tanggal_dari:
            query += " AND a.tanggal >= %s"
            params.append(tanggal_dari)
        if tanggal_sampai:
            query += " AND a.tanggal <= %s"
            params.append(tanggal_sampai)
        query += " GROUP BY status"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        total = sum(r['jumlah'] for r in rows)
        divisor = total or 1
        hasil = {s: 0 for s in ['hadir', 'terlambat', 'izin', 'sakit', 'alpha']}
        for r in rows:
            hasil[r['status']] = round(r['jumlah'] / divisor * 100, 1)
        hasil['total'] = total
        return hasil
    except Exception:
        return {'hadir': 0, 'terlambat': 0, 'izin': 0, 'sakit': 0, 'alpha': 0, 'total': 0}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# ══════════════════════════════════════════════════════════════
# SPOOFING LOG
# ══════════════════════════════════════════════════════════════

def get_ringkasan_rekap(kelas_id=None, tanggal_dari=None, tanggal_sampai=None, matakuliah_id=None):
    """Hitung jumlah record per status untuk kartu ringkasan rekap. Return dict."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT status, COUNT(*) as jumlah
            FROM absensi a
            JOIN jadwal j ON a.jadwal_id = j.id
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE 1=1
        """
        params = []
        if kelas_id:
            query += " AND m.kelas_id = %s"
            params.append(kelas_id)
        if tanggal_dari:
            query += " AND a.tanggal >= %s"
            params.append(tanggal_dari)
        if tanggal_sampai:
            query += " AND a.tanggal <= %s"
            params.append(tanggal_sampai)
        if matakuliah_id:
            query += " AND j.matakuliah_id = %s"
            params.append(matakuliah_id)
        query += " GROUP BY status"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        hasil = {'hadir': 0, 'terlambat': 0, 'izin': 0, 'sakit': 0, 'alpha': 0}
        for r in rows:
            if r['status'] in hasil:
                hasil[r['status']] = r['jumlah']
        return hasil
    except Exception:
        return {'hadir': 0, 'terlambat': 0, 'izin': 0, 'sakit': 0, 'alpha': 0}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_ranking_kelas(tanggal_dari=None, tanggal_sampai=None):
    """Hitung persentase kehadiran per kelas untuk laporan ranking. Return list dict."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        # Ambil semua kelas terlebih dahulu
        cursor.execute("SELECT id, nama_kelas, angkatan FROM kelas ORDER BY nama_kelas")
        kelas_list = cursor.fetchall()
        ranking = []
        for k in kelas_list:
            q = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN a.status = 'hadir' THEN 1 ELSE 0 END) as hadir
                FROM absensi a
                JOIN jadwal j ON a.jadwal_id = j.id
                JOIN matakuliah m ON j.matakuliah_id = m.id
                WHERE m.kelas_id = %s
            """
            params = [k['id']]
            if tanggal_dari:
                q += " AND a.tanggal >= %s"
                params.append(tanggal_dari)
            if tanggal_sampai:
                q += " AND a.tanggal <= %s"
                params.append(tanggal_sampai)
            cursor.execute(q, params)
            stat = cursor.fetchone()
            total = stat['total'] or 0
            hadir = stat['hadir'] or 0
            persen = round(hadir / total * 100, 1) if total > 0 else 0
            ranking.append({
                'id': k['id'],
                'nama_kelas': k['nama_kelas'],
                'angkatan': k['angkatan'],
                'total': total,
                'hadir': hadir,
                'persen': persen
            })
        # Urutkan dari persen tertinggi
        ranking.sort(key=lambda x: x['persen'], reverse=True)
        return ranking
    except Exception:
        return []


def get_top_mahasiswa(tanggal_dari=None, tanggal_sampai=None):
    """Cari mahasiswa dengan kehadiran tertinggi. Return dict atau None."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        q = """
            SELECT u.nama, k.nama_kelas,
                   COUNT(*) as total,
                   SUM(CASE WHEN a.status = 'hadir' THEN 1 ELSE 0 END) as hadir
            FROM absensi a
            JOIN users u ON a.user_id = u.id
            JOIN jadwal j ON a.jadwal_id = j.id
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE 1=1
        """
        params = []
        if tanggal_dari:
            q += " AND a.tanggal >= %s"
            params.append(tanggal_dari)
        if tanggal_sampai:
            q += " AND a.tanggal <= %s"
            params.append(tanggal_sampai)
        q += " GROUP BY u.id, u.nama, k.nama_kelas HAVING total > 0 ORDER BY (hadir/total) DESC LIMIT 1"
        cursor.execute(q, params)
        row = cursor.fetchone()
        if row and row['total'] > 0:
            row['persen'] = round(row['hadir'] / row['total'] * 100, 1)
        return row
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def catat_spoofing(snapshot_path, confidence_score):
    """Simpan log percobaan spoofing. Return id atau None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO spoofing_log (snapshot_path, confidence_score) VALUES (%s, %s)",
            (snapshot_path, confidence_score)
        )
        conn.commit()
        log_id = cursor.lastrowid
        cursor.close(); conn.close()
        return log_id
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# STATISTIK DASHBOARD
# ══════════════════════════════════════════════════════════════

def get_statistik_dashboard(tanggal=None):
    """Ambil statistik ringkas untuk dashboard. Return dict."""
    tanggal = tanggal or _now_app().date()
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Total mahasiswa
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_mhs = cursor.fetchone()['total']

        # Absensi hari ini per status
        cursor.execute("""
            SELECT status, COUNT(*) as jumlah
            FROM absensi WHERE tanggal = %s GROUP BY status
        """, (tanggal,))
        status_hari_ini = {r['status']: r['jumlah'] for r in cursor.fetchall()}

        # Kelas aktif hari ini (kelas yang punya jadwal hari ini)
        hari_map = {0:'Senin',1:'Selasa',2:'Rabu',3:'Kamis',4:'Jumat',5:'Sabtu',6:'Minggu'}
        hari_ini = hari_map.get(tanggal.weekday(), '')
        cursor.execute("""
            SELECT COUNT(DISTINCT m.kelas_id) as total
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE j.hari = %s
        """, (hari_ini,))
        kelas_aktif = cursor.fetchone()['total']

        cursor.close(); conn.close()

        return {
            'total_mahasiswa': total_mhs,
            'total_kelas': kelas_aktif,
            'hadir_hari_ini': status_hari_ini.get('hadir', 0),
            'terlambat_hari_ini': status_hari_ini.get('terlambat', 0),
            'alpha_hari_ini': status_hari_ini.get('alpha', 0),
        }
    except Exception:
        return {
            'total_mahasiswa': 0, 'total_kelas': 0,
            'hadir_hari_ini': 0, 'terlambat_hari_ini': 0, 'alpha_hari_ini': 0,
        }


def get_jadwal_selesai_hari_ini(hari, waktu_sekarang):
    """Ambil jadwal setelah grace period titik absensi berakhir."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.*, m.nama_mk, m.kelas_id
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE j.hari = %s
              AND ADDTIME(j.jam_selesai, SEC_TO_TIME(%s * 60)) < %s
        """, (hari, ABSENSI_GRACE_MINUTES, waktu_sekarang))
        hasil = cursor.fetchall()
        return hasil
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
def get_mahasiswa_belum_absen(jadwal_id, kelas_id, tanggal):
    """Ambil daftar user_id yang belum absen untuk jadwal tertentu hari ini."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.nama, u.nim
            FROM users u
            WHERE u.kelas_id = %s
              AND u.id NOT IN (
                  SELECT a.user_id FROM absensi a
                  WHERE a.jadwal_id = %s AND a.tanggal = %s
              )
        """, (kelas_id, jadwal_id, tanggal))
        hasil = cursor.fetchall()
        return hasil
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def bulk_catat_alpha(jadwal_id, user_ids, tanggal):
    """Insert batch record alpha untuk mahasiswa yang tidak hadir."""
    if not user_ids:
        return 0
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        count = 0
        for uid in user_ids:
            cursor.execute("""
                INSERT IGNORE INTO absensi
                    (user_id, jadwal_id, tanggal, waktu_absen, status)
                VALUES (%s, %s, %s, '00:00:00', 'alpha')
            """, (uid, jadwal_id, tanggal))
            count += cursor.rowcount
        conn.commit()
        return count
    except Exception:
        if conn:
            conn.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()



# ══════════════════════════════════════════════════════════════
# PENCARIAN MAHASISWA DAN JADWAL
# ══════════════════════════════════════════════════════════════

def cari_mahasiswa(query_str):
    """Cari mahasiswa berdasarkan nama atau NIM. Return list dict atau []."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT u.*, k.nama_kelas
            FROM users u
            JOIN kelas k ON u.kelas_id = k.id
            WHERE u.nama LIKE %s OR u.nim LIKE %s
            ORDER BY u.nama
            LIMIT 10
        """
        like_query = f"%{query_str}%"
        cursor.execute(sql, (like_query, like_query))
        hasil = cursor.fetchall()
        return hasil
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def cari_jadwal(query_str):
    """Cari jadwal berdasarkan nama MK, kode MK, hari, atau nama kelas. Return list dict atau []."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT j.*, m.nama_mk, m.kode_mk, k.nama_kelas
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE m.nama_mk LIKE %s OR m.kode_mk LIKE %s OR j.hari LIKE %s OR k.nama_kelas LIKE %s
            ORDER BY FIELD(j.hari,'Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'),
                     j.jam_mulai
            LIMIT 10
        """
        like_query = f"%{query_str}%"
        cursor.execute(sql, (like_query, like_query, like_query, like_query))
        hasil = cursor.fetchall()
        return hasil
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
