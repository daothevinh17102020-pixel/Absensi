# database.py — Tất cả các hàm truy vấn cơ sở dữ liệu (Database Query Functions)
# Không được thực hiện truy vấn SQL trực tiếp trong app.py (xem context.md phần 12)

import mysql.connector
from config import (ABSENSI_GRACE_MINUTES, APP_TIMEZONE, DB_CONFIG,
                    TOLERANSI_MENIT)

# Quy chuẩn điểm danh sớm: cho phép sinh viên quét mặt trước giờ học tối đa 15 phút (GAP-01)
EARLY_CHECKIN_MINUTES = 15
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


APP_TZ = ZoneInfo(APP_TIMEZONE)


def _now_app():
    return datetime.now(APP_TZ)


def get_connection():
    """Tạo kết nối mới tới MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


class DatabaseQueryError(RuntimeError):
    """Ngoại lệ ném ra khi cơ sở dữ liệu không khả dụng trong chế độ quét nghiêm ngặt."""


# ══════════════════════════════════════════════════════════════
# QUẢN TRỊ VIÊN (ADMIN)
# ══════════════════════════════════════════════════════════════

def hitung_admin():
    """Đếm tổng số quản trị viên trong cơ sở dữ liệu. Trả về 0 nếu thất bại."""
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
    """Lưu quản trị viên mới. Trả về ID admin hoặc None."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
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
    """Lấy thông tin admin theo username. Trả về dict hoặc None."""
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
# LỚP HỌC (KELAS)
# ══════════════════════════════════════════════════════════════

def get_semua_kelas():
    """Lấy danh sách tất cả các lớp học. Trả về list dict hoặc []."""
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
    """Lấy thông tin một lớp theo id. Trả về dict hoặc None."""
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
    """Lưu lớp học mới vào cơ sở dữ liệu. Trả về id lớp hoặc None."""
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


def kelas_sudah_ada(nama_kelas, angkatan, exclude_id=None):
    """Kiểm tra lớp với tên và khóa học đã tồn tại hay chưa (GAP-08)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if exclude_id:
            cursor.execute(
                "SELECT id FROM kelas WHERE nama_kelas = %s AND angkatan = %s AND id != %s",
                (nama_kelas, angkatan, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT id FROM kelas WHERE nama_kelas = %s AND angkatan = %s",
                (nama_kelas, angkatan)
            )
        row = cursor.fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def update_kelas(kelas_id, nama_kelas, angkatan):
    """Cập nhật thông tin lớp học. Trả về True/False."""
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
    """Xóa lớp học (CASCADE tới môn học và lịch học). Trả về True/False."""
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
    """Đếm tổng số lượng sinh viên trong một lớp."""
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
# MÔN HỌC (MATAKULIAH)
# ══════════════════════════════════════════════════════════════

def get_semua_matakuliah():
    """Lấy danh sách tất cả các môn học kèm tên lớp. Trả về list dict."""
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
    """Lấy danh sách môn học thuộc về một lớp cụ thể."""
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
    """Lấy thông tin chi tiết một môn học theo id."""
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
    """Lưu môn học mới. Trả về id hoặc None."""
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
    """Cập nhật thông tin môn học. Trả về True/False."""
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


def matakuliah_memiliki_absensi(mk_id):
    """Kiểm tra xem môn học đã phát sinh ít nhất 1 bản ghi điểm danh (qua lịch học) hay chưa (GAP-10)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM absensi a
            JOIN jadwal j ON a.jadwal_id = j.id
            WHERE j.matakuliah_id = %s
            LIMIT 1
        """, (mk_id,))
        row = cursor.fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def hapus_matakuliah(mk_id):
    """Xóa môn học (CASCADE tới lịch học tương ứng). Trả về True/False."""
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
# LỊCH HỌC (JADWAL)
# ══════════════════════════════════════════════════════════════

def get_semua_jadwal():
    """Lấy danh sách tất cả các lịch học kèm thông tin môn học và lớp."""
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

def update_jadwal(jadwal_id, matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat=None, buoi_bat_dau=1):
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
               SET matakuliah_id=%s, hari=%s, jam_mulai=%s, jam_selesai=%s, batas_terlambat=%s, buoi_bat_dau=%s
               WHERE id=%s""",
            (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat, buoi_bat_dau or 1, jadwal_id)
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



def tambah_jadwal(matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat=None, buoi_bat_dau=1):
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
            """INSERT INTO jadwal (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat, buoi_bat_dau)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (matakuliah_id, hari, jam_mulai, jam_selesai, batas_terlambat, buoi_bat_dau or 1)
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
              AND %s >= SUBTIME(j.jam_mulai, SEC_TO_TIME(%s * 60))
              AND %s <= ADDTIME(j.jam_selesai, SEC_TO_TIME(%s * 60))
            ORDER BY j.jam_mulai DESC, j.id DESC
        """, (hari, waktu_sekarang, EARLY_CHECKIN_MINUTES, waktu_sekarang, ABSENSI_GRACE_MINUTES))
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
# SINH VIÊN (USERS / MAHASISWA)
# ══════════════════════════════════════════════════════════════

def get_semua_user():
    """Lấy danh sách tất cả sinh viên kèm tên lớp."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*, k.nama_kelas
            FROM users u
            LEFT JOIN kelas k ON u.kelas_id = k.id
            ORDER BY u.nama ASC
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
            LEFT JOIN kelas k ON u.kelas_id = k.id
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
    """Ambil tất cả mahasiswa di satu kelas."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*, k.nama_kelas
            FROM users u
            LEFT JOIN kelas k ON u.kelas_id = k.id
            WHERE u.kelas_id = %s
            ORDER BY u.nama ASC
        """, (kelas_id,))
        hasil = cursor.fetchall()
        cursor.close(); conn.close()
        return hasil
    except Exception:
        return []


def tambah_user(nama, nim, kelas_id, foto_path=None, stt=None):
    """Simpan mahasiswa baru. Return id user hoặc None."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (nama, nim, kelas_id, foto_path, stt) VALUES (%s,%s,%s,%s,%s)",
            (nama, nim, kelas_id, foto_path, stt)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close(); conn.close()
        return user_id
    except Exception:
        return None


def update_user(user_id, nama, nim, kelas_id, foto_path=None, stt=None):
    """Update data mahasiswa. Return True/False."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if foto_path:
            cursor.execute(
                "UPDATE users SET nama=%s, nim=%s, kelas_id=%s, foto_path=%s, stt=%s WHERE id=%s",
                (nama, nim, kelas_id, foto_path, stt, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET nama=%s, nim=%s, kelas_id=%s, stt=%s WHERE id=%s",
                (nama, nim, kelas_id, stt, user_id)
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
# ĐIỂM DANH (ABSENSI)
# ══════════════════════════════════════════════════════════════

def catat_absensi(user_id, jadwal_id, tanggal, waktu_absen, status,
                  snapshot_path=None, dibuat_manual=False, alasan=None,
                  raise_on_error=False, buoi_so=None):
    """Lưu bản ghi điểm danh vào cơ sở dữ liệu. Trả về ID bản ghi hoặc None (nếu trùng lặp hoặc lỗi)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Nếu chưa truyền buoi_so, lấy buoi_bat_dau từ lịch học hoặc mặc định là 1
        if buoi_so is None:
            try:
                cursor.execute("SELECT buoi_bat_dau FROM jadwal WHERE id=%s", (jadwal_id,))
                j_row = cursor.fetchone()
                buoi_so = (j_row[0] if j_row else 1) or 1
            except Exception:
                buoi_so = 1

        cursor.execute(
            """INSERT INTO absensi
               (user_id, jadwal_id, tanggal, waktu_absen, status, buoi_so, alasan, snapshot_path, dibuat_manual)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               status=VALUES(status), waktu_absen=VALUES(waktu_absen), buoi_so=VALUES(buoi_so),
               alasan=VALUES(alasan), snapshot_path=COALESCE(VALUES(snapshot_path), snapshot_path),
               dibuat_manual=VALUES(dibuat_manual)""",
            (user_id, jadwal_id, tanggal, waktu_absen, status, buoi_so or 1,
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


def cap_nhat_absensi_buoi(user_id, jadwal_id, buoi_so, status, alasan=None):
    """Cập nhật hoặc tạo bản ghi điểm danh cho sinh viên theo Buổi học (1-15).
    - Nếu status rỗng hoặc '-': Xóa bản ghi điểm danh buổi này (nếu có).
    - Nếu status hợp lệ ('hadir', 'terlambat', 'izin', 'alpha'): Cập nhật hoặc thêm mới.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        buoi_so = int(buoi_so)

        # Cek record absensi untuk user, jadwal, dan buoi_so
        cursor.execute(
            "SELECT id, tanggal, status FROM absensi WHERE user_id=%s AND jadwal_id=%s AND buoi_so=%s",
            (user_id, jadwal_id, buoi_so)
        )
        existing = cursor.fetchone()

        # Nếu chọn rỗng hoặc '-' -> Xóa bản ghi buổi này
        if not status or str(status).strip() in ('', '-'):
            if existing:
                cursor.execute("DELETE FROM absensi WHERE id=%s", (existing['id'],))
                conn.commit()
                return {'aksi': 'delete', 'id': existing['id'], 'buoi_so': buoi_so}
            return {'aksi': 'noop', 'buoi_so': buoi_so}

        status = str(status).strip()
        waktu_now = _now_app().strftime('%H:%M:%S')

        if existing:
            # Update record đã tồn tại
            cursor.execute(
                """UPDATE absensi SET status=%s, alasan=%s, dibuat_manual=TRUE, waktu_absen=%s
                   WHERE id=%s""",
                (status, alasan, waktu_now, existing['id'])
            )
            conn.commit()
            return {'aksi': 'update', 'id': existing['id'], 'status_lama': existing['status'], 'status': status, 'buoi_so': buoi_so}
        else:
            # Xác định ngày tương ứng cho buoi_so để không trùng uq_absensi (user_id, jadwal_id, tanggal)
            cursor.execute("SELECT MIN(tanggal) as min_t FROM absensi WHERE jadwal_id=%s", (jadwal_id,))
            row_t = cursor.fetchone()
            base_date = row_t['min_t'] if (row_t and row_t['min_t']) else _now_app().date()
            from datetime import timedelta
            target_date = base_date + timedelta(days=(buoi_so - 1) * 7)

            cursor.execute(
                """INSERT INTO absensi
                   (user_id, jadwal_id, tanggal, waktu_absen, status, buoi_so, alasan, dibuat_manual)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                   ON DUPLICATE KEY UPDATE status=VALUES(status), buoi_so=VALUES(buoi_so), dibuat_manual=TRUE, waktu_absen=VALUES(waktu_absen)""",
                (user_id, jadwal_id, target_date, waktu_now, status, buoi_so, alasan)
            )
            conn.commit()
            absensi_id = cursor.lastrowid
            return {'aksi': 'insert', 'id': absensi_id, 'status': status, 'buoi_so': buoi_so}
    except Exception as e:
        if conn:
            conn.rollback()
        print(f'[DB] Error cap_nhat_absensi_buoi: {e}')
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
    """Ambil statistik ringkas untuk dashboard theo nghiệp vụ chuẩn:
    1. Toàn bộ tính toán đối chiếu theo các lớp có lịch học hôm nay (không tính toàn trường).
    2. 'Có mặt hôm nay' = sinh viên đi đúng giờ (hadir) + sinh viên đi muộn (terlambat).
    3. 'Đi muộn' = sinh viên đi muộn (terlambat).
    4. 'Vắng không phép' = đối chiếu danh sách có mặt với tổng SV của lớp đối với các ca học ĐÃ KẾT THÚC.
    5. 'Tổng số sinh viên' = tổng sinh viên của các lớp có lịch học tương ứng hôm nay.
    """
    tanggal = tanggal or _now_app().date()
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        hari_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
        hari_ini = hari_map.get(tanggal.weekday(), '')

        # 1. Lấy tất cả lịch học của ngày hôm nay
        cursor.execute("""
            SELECT j.id as jadwal_id, j.jam_mulai, j.jam_selesai,
                   m.kelas_id, m.nama_mk
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            WHERE j.hari = %s
        """, (hari_ini,))
        jadwal_hari_ini = cursor.fetchall()

        if not jadwal_hari_ini:
            # Hôm nay không có lớp nào có lịch học -> các chỉ số đều là 0
            cursor.close()
            conn.close()
            return {
                'total_mahasiswa': 0,
                'total_kelas': 0,
                'hadir_hari_ini': 0,
                'terlambat_hari_ini': 0,
                'alpha_hari_ini': 0,
            }

        # 2. Danh sách lớp có lịch hôm nay và tổng sinh viên của các lớp này
        kelas_ids = list(dict.fromkeys([j['kelas_id'] for j in jadwal_hari_ini if j['kelas_id'] is not None]))
        total_kelas = len(kelas_ids)
        total_mhs = 0

        if kelas_ids:
            format_strings = ','.join(['%s'] * len(kelas_ids))
            cursor.execute(f"""
                SELECT COUNT(DISTINCT id) as total
                FROM users
                WHERE kelas_id IN ({format_strings})
            """, tuple(kelas_ids))
            total_mhs = cursor.fetchone()['total'] or 0

        # 3. Thống kê điểm danh hôm nay của các lịch học hôm nay
        jadwal_ids = [j['jadwal_id'] for j in jadwal_hari_ini]
        format_jadwal = ','.join(['%s'] * len(jadwal_ids))

        # Đi muộn (terlambat)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT user_id) as total
            FROM absensi
            WHERE tanggal = %s AND jadwal_id IN ({format_jadwal}) AND status = 'terlambat'
        """, (tanggal, *jadwal_ids))
        terlambat_hari_ini = cursor.fetchone()['total'] or 0

        # Có mặt hôm nay (tính cả đúng giờ 'hadir' lẫn đi muộn 'terlambat')
        cursor.execute(f"""
            SELECT COUNT(DISTINCT user_id) as total
            FROM absensi
            WHERE tanggal = %s AND jadwal_id IN ({format_jadwal}) AND status IN ('hadir', 'terlambat')
        """, (tanggal, *jadwal_ids))
        hadir_hari_ini = cursor.fetchone()['total'] or 0

        # 4. Vắng không phép: Khi buổi học kết thúc, đối chiếu danh sách có mặt với tổng SV lớp
        # Buổi học kết thúc khi thời gian hiện tại >= jam_selesai (hoặc đã qua ngày hôm nay)
        waktu_sekarang = _now_app().strftime('%H:%M:%S')
        is_past_day = tanggal < _now_app().date()
        is_today = tanggal == _now_app().date()

        alpha_hari_ini = 0
        if is_past_day or is_today:
            # Lọc các ca học đã kết thúc hôm nay
            if is_past_day:
                jadwal_da_ket_thuc = jadwal_hari_ini
            else:
                # Dùng truy vấn MySQL để so sánh giờ kết thúc an toàn tuyệt đối
                cursor.execute("""
                    SELECT j.id as jadwal_id, m.kelas_id
                    FROM jadwal j
                    JOIN matakuliah m ON j.matakuliah_id = m.id
                    WHERE j.hari = %s AND j.jam_selesai <= %s
                """, (hari_ini, waktu_sekarang))
                jadwal_da_ket_thuc = cursor.fetchall()

            # Đối chiếu sinh viên vắng trong các ca đã kết thúc
            user_alpha_set = set()
            for j in jadwal_da_ket_thuc:
                k_id = j['kelas_id']
                j_id = j['jadwal_id']
                if not k_id:
                    continue
                cursor.execute("""
                    SELECT u.id
                    FROM users u
                    WHERE u.kelas_id = %s
                      AND u.id NOT IN (
                          SELECT a.user_id FROM absensi a
                          WHERE a.jadwal_id = %s AND a.tanggal = %s
                            AND a.status IN ('hadir', 'terlambat', 'izin', 'sakit')
                      )
                """, (k_id, j_id, tanggal))
                absent_users = cursor.fetchall()
                for u in absent_users:
                    user_alpha_set.add(u['id'])

            alpha_hari_ini = len(user_alpha_set)

        cursor.close()
        conn.close()

        return {
            'total_mahasiswa': total_mhs,
            'total_kelas': total_kelas,
            'hadir_hari_ini': hadir_hari_ini,
            'terlambat_hari_ini': terlambat_hari_ini,
            'alpha_hari_ini': alpha_hari_ini,
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


def ada_mahasiswa_hadir_jadwal(jadwal_id, tanggal):
    """Cek apakah có ít nhất 1 sinh viên điểm danh hợp lệ (hadir/terlambat/izin/sakit)
    cho ca học và ngày này (dùng cho GAP-03: điều kiện kích hoạt Auto-Alpha)."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM absensi
            WHERE jadwal_id = %s AND tanggal = %s AND status IN ('hadir', 'terlambat', 'izin', 'sakit')
            LIMIT 1
        """, (jadwal_id, tanggal))
        row = cursor.fetchone()
        return row is not None
    except Exception:
        return False
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


# ══════════════════════════════════════════════════════════════
# THÔNG TIN BUỔI HỌC VÀ TÍNH SỐ BUỔI TỰ ĐỘNG
# Quy tắc nghiệp vụ: Buổi nào không có ai điểm danh = Buổi đó nghỉ
# và sẽ nhắc lại đúng số buổi đó vào lượt học sau.
# ══════════════════════════════════════════════════════════════

def get_buoi_hoc_hien_tai_cua_lop(jadwal_id, kelas_id=None, ngay_kiem_tra=None):
    """Tính số Buổi học hiện tại của một lớp học / lịch học.
    - Đếm số ngày thực tế trong quá khứ đã từng có ít nhất 1 sinh viên điểm danh hợp lệ
      (hadir, terlambat, izin, sakit).
    - Nếu buổi trước không ai điểm danh (buổi nghỉ) -> số ngày không tăng -> lần sau vẫn nhắc lại buổi đó.
    - Nếu hôm nay đã có sinh viên điểm danh: trả về buổi_so đã ghi nhận hôm nay.
    - Nếu hôm nay chưa ai điểm danh: trả về (số ngày đã có điểm danh trước đó) + 1.
    """
    conn = None
    cursor = None
    try:
        ngay_kiem_tra = ngay_kiem_tra or _now_app().date()
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Kiểm tra xem trong ngày kiểm tra (hôm nay) đã có bản ghi điểm danh nào chưa
        cursor.execute("""
            SELECT buoi_so FROM absensi
            WHERE jadwal_id = %s AND tanggal = %s AND buoi_so IS NOT NULL
            ORDER BY waktu_absen ASC LIMIT 1
        """, (jadwal_id, ngay_kiem_tra))
        row_today = cursor.fetchone()
        if row_today and row_today.get('buoi_so'):
            return int(row_today['buoi_so'])

        # 2. Đếm số ngày thực tế trong quá khứ đã từng diễn ra điểm danh hợp lệ
        cursor.execute("""
            SELECT COUNT(DISTINCT tanggal) as so_ngay_da_hoc
            FROM absensi
            WHERE jadwal_id = %s
              AND status IN ('hadir', 'terlambat', 'izin', 'sakit')
              AND tanggal < %s
        """, (jadwal_id, ngay_kiem_tra))
        row_past = cursor.fetchone()
        so_ngay_da_hoc = row_past['so_ngay_da_hoc'] if row_past else 0

        # Số buổi tiếp theo = số ngày thực tế đã học có điểm danh + 1
        buoi_tiep_theo = (so_ngay_da_hoc or 0) + 1
        return max(1, min(60, buoi_tiep_theo))
    except Exception as e:
        print(f"[DB] Lỗi khi tính số buổi học hiện tại: {e}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def get_thong_tin_buoi_hoc_hom_nay(ngay_kiem_tra=None):
    """Lấy thông tin chi tiết ca học hôm nay để hiển thị trên Popup Topbar.
    Liên kết trực tiếp từ tab Quản lý lịch học (/jadwal) đối với lịch học tương ứng.
    Bao gồm: Thứ, Ngày, Lớp học phần, Giờ bắt đầu, Giờ kết thúc, Cột Buổi, và Hạn đi muộn (Không áp dụng).
    """
    conn = None
    cursor = None
    try:
        ngay_kiem_tra = ngay_kiem_tra or _now_app().date()
        hari_map = {
            0: 'Senin', 1: 'Selasa', 2: 'Rabu',
            3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'
        }
        hari_db = hari_map.get(ngay_kiem_tra.weekday(), 'Senin')
        thu_tieng_viet_map = {
            'Senin': 'Thứ Hai', 'Selasa': 'Thứ Ba', 'Rabu': 'Thứ Tư',
            'Kamis': 'Thứ Năm', 'Jumat': 'Thứ Sáu', 'Sabtu': 'Thứ Bảy', 'Minggu': 'Chủ Nhật'
        }
        thu_vn = thu_tieng_viet_map.get(hari_db, 'Thứ Hai')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Tìm ca học của ngày hôm nay
        waktu_sekarang = _now_app().strftime('%H:%M:%S')
        cursor.execute("""
            SELECT j.*, m.nama_mk, m.kode_mk, m.kelas_id, k.nama_kelas, k.angkatan
            FROM jadwal j
            JOIN matakuliah m ON j.matakuliah_id = m.id
            JOIN kelas k ON m.kelas_id = k.id
            WHERE j.hari = %s
            ORDER BY
                CASE WHEN %s BETWEEN j.jam_mulai AND j.jam_selesai THEN 0
                     WHEN j.jam_mulai > %s THEN 1
                     ELSE 2 END,
                j.jam_mulai ASC
            LIMIT 1
        """, (hari_db, waktu_sekarang, waktu_sekarang))
        jadwal = cursor.fetchone()

        # Nếu ngày hôm nay không có lịch, lấy lịch học đầu tiên trong hệ thống làm ca tham chiếu
        if not jadwal:
            cursor.execute("""
                SELECT j.*, m.nama_mk, m.kode_mk, m.kelas_id, k.nama_kelas, k.angkatan
                FROM jadwal j
                JOIN matakuliah m ON j.matakuliah_id = m.id
                JOIN kelas k ON m.kelas_id = k.id
                ORDER BY j.id ASC LIMIT 1
            """)
            jadwal = cursor.fetchone()

        if not jadwal:
            return {
                'has_jadwal': False,
                'thu': thu_vn,
                'tanggal': ngay_kiem_tra.strftime('%Y-%m-%d'),
                'tanggal_vn': ngay_kiem_tra.strftime('%d/%m/%Y'),
                'nama_kelas': 'Chưa có lớp học',
                'lop_hoc_phan': 'Chưa có lớp học phần',
                'jam_mulai': '06:30',
                'jam_selesai': '11:30',
                'han_di_muon': 'Không có hạn đi muộn',
                'buoi_so': 1,
                'jadwal_id': None,
                'kelas_id': None
            }

        # Định dạng thời gian bắt đầu và kết thúc
        def _fmt_time(val):
            if isinstance(val, timedelta):
                sec = int(val.total_seconds())
                return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}"
            s = str(val or '')
            return s[:5] if len(s) >= 5 else s

        jam_mulai_str = _fmt_time(jadwal['jam_mulai'])
        jam_selesai_str = _fmt_time(jadwal['jam_selesai'])

        # Tính số buổi học hiện tại theo quy tắc không có ai điểm danh = buổi đó nghỉ
        buoi_so = get_buoi_hoc_hien_tai_cua_lop(jadwal['id'], jadwal.get('kelas_id'), ngay_kiem_tra)

        lop_display = f"{jadwal.get('nama_kelas', '')} — {jadwal.get('nama_mk', '')}"
        if jadwal.get('kode_mk'):
            lop_display += f" ({jadwal.get('kode_mk')})"

        return {
            'has_jadwal': True,
            'thu': thu_vn,
            'tanggal': ngay_kiem_tra.strftime('%Y-%m-%d'),
            'tanggal_vn': ngay_kiem_tra.strftime('%d/%m/%Y'),
            'nama_kelas': jadwal.get('nama_kelas', ''),
            'nama_mk': jadwal.get('nama_mk', ''),
            'lop_hoc_phan': lop_display,
            'jam_mulai': jam_mulai_str,
            'jam_selesai': jam_selesai_str,
            'han_di_muon': 'Không có hạn đi muộn',
            'buoi_so': buoi_so,
            'jadwal_id': jadwal['id'],
            'kelas_id': jadwal.get('kelas_id')
        }
    except Exception as e:
        print(f"[DB] Lỗi get_thong_tin_buoi_hoc_hom_nay: {e}")
        return {
            'has_jadwal': False,
            'thu': 'Thứ Sáu',
            'tanggal': ngay_kiem_tra.strftime('%Y-%m-%d') if ngay_kiem_tra else '2026-09-06',
            'tanggal_vn': ngay_kiem_tra.strftime('%d/%m/%Y') if ngay_kiem_tra else '06/09/2026',
            'nama_kelas': 'ML - 02',
            'lop_hoc_phan': 'ML - 02 — Máy học ứng dụng',
            'jam_mulai': '06:30',
            'jam_selesai': '11:30',
            'han_di_muon': 'Không có hạn đi muộn',
            'buoi_so': 1,
            'jadwal_id': None,
            'kelas_id': None
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

