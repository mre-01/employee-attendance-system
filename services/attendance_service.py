from datetime import date
from sqlite3 import IntegrityError

from database.db import get_connection
from services.auth_helpers import require_admin, require_authenticated, ensure_self_or_admin
from services.exceptions import (
    AuthorizationError,
    DuplicateAttendanceError,
    ValidationError
)

def get_employee_attendance(current_user, employee_id):
    """
    Belirli çalışanın yoklama kayıtlarını al.
    - Admin: herhangi bir çalışan için alabilir
    - Normal kullanıcı: sadece kendi kaydını görebilir
    """
    
    # YETKİLENDİRME
    require_authenticated(current_user)
    ensure_self_or_admin(current_user, employee_id)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        attendance_id,
        work_date,
        status,
        work_hours,
        overtime_hours
    FROM attendance
    WHERE employee_id = ?
    ORDER BY work_date DESC
    """, (employee_id,))

    records = cursor.fetchall()
    conn.close()

    return records


def get_all_attendance(current_user):
    """
    Tüm yoklama kayıtlarını al. Admin erişimi gerekli.
    Admin olmayan kullanıcılar buna erişemezler.
    """
    
    # YETKİLENDİRME
    require_admin(current_user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        a.attendance_id,
        a.employee_id,
        e.first_name,
        e.last_name,
        a.work_date,
        a.status,
        a.work_hours,
        a.overtime_hours
    FROM attendance a
    JOIN employees e
    ON e.employee_id = a.employee_id
    ORDER BY a.work_date DESC, a.attendance_id DESC
    """)

    records = cursor.fetchall()
    conn.close()

    return records


def get_attendance_by_month(current_user, month, year):
    """
    Ay'a göre yoklama kayıtlarını al.
    - Admin: tüm çalışanları görebilir
    - Normal kullanıcı: sadece kendi kayıtlarını görebilir
    """
    
    # YETKİLENDİRME
    require_authenticated(current_user)
    
    from services.auth_helpers import _is_admin, _get_user_id
    is_admin = _is_admin(current_user)
    user_id = _get_user_id(current_user)

    conn = get_connection()
    cursor = conn.cursor()

    if is_admin:
        # Admin tüm yoklama kayıtlarını görebilir
        cursor.execute("""
        SELECT
            a.attendance_id,
            a.employee_id,
            e.first_name,
            e.last_name,
            a.work_date,
            a.status,
            a.work_hours,
            a.overtime_hours
        FROM attendance a
        JOIN employees e
        ON e.employee_id = a.employee_id
        WHERE strftime('%m', a.work_date) = ?
        AND strftime('%Y', a.work_date) = ?
        ORDER BY a.work_date DESC, a.attendance_id DESC
        """, (
            f"{month:02}",
            str(year),
        ))
    else:
        # Normal kullanıcı sadece kendi kayıtlarını görür
        cursor.execute("""
        SELECT
            a.attendance_id,
            a.employee_id,
            e.first_name,
            e.last_name,
            a.work_date,
            a.status,
            a.work_hours,
            a.overtime_hours
        FROM attendance a
        JOIN employees e
        ON e.employee_id = a.employee_id
        WHERE a.employee_id = ?
        AND strftime('%m', a.work_date) = ?
        AND strftime('%Y', a.work_date) = ?
        ORDER BY a.work_date DESC, a.attendance_id DESC
        """, (
            user_id,
            f"{month:02}",
            str(year),
        ))

    records = cursor.fetchall()
    conn.close()

    return records


def get_today_or_month_stats(month=None, year=None):

    conn = get_connection()
    cursor = conn.cursor()

    if month is None or year is None:
        today = date.today()
        month = today.month
        year = today.year

    cursor.execute("""
    SELECT COUNT(*) AS total_count
    FROM attendance
    WHERE strftime('%m', work_date) = ?
    AND strftime('%Y', work_date) = ?
    """, (
        f"{month:02}",
        str(year),
    ))

    result = cursor.fetchone()

    conn.close()

    return result["total_count"] if result else 0



def add_attendance(
    current_user,
    employee_id,
    work_date,
    status,
    work_hours,
    overtime_hours
):
    """Yoklama kaydı ekle. Admin erişimi gerekli."""
    
    # YETKİLENDİRME
    require_admin(current_user)

    # VALIDATION
    if work_hours < 0:
        raise ValidationError("Çalışma saati negatif olamaz.")

    if overtime_hours < 0:
        raise ValidationError("Mesai saati negatif olamaz.")

    valid_status = ["present", "absent", "leave"]

    if status not in valid_status:
        raise ValidationError("Geçersiz attendance durumu.")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO attendance (
            employee_id,
            work_date,
            status,
            work_hours,
            overtime_hours
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            employee_id,
            work_date,
            status,
            work_hours,
            overtime_hours
        ))

        conn.commit()

    except IntegrityError:
        raise DuplicateAttendanceError(
            "Bu çalışan için aynı gün attendance kaydı zaten var."
        )

    finally:
        conn.close()