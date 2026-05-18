import json
from pathlib import Path

from database.db import get_connection
from services.auth_helpers import require_authenticated, ensure_self_or_admin, _is_admin, _get_user_id
from services.exceptions import AuthorizationError, ValidationError


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    """Konfigürasyon dosyasını yükle."""
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def calculate_salary(
    employee_id,
    month,
    year
):
    """İç maaş hesaplama (yetkilendirme kontrolü yok)."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        e.first_name,
        e.last_name,
        e.hourly_rate,

        SUM(a.work_hours) AS total_work_hours,
        SUM(a.overtime_hours) AS total_overtime_hours

    FROM employees e

    JOIN attendance a
    ON e.employee_id = a.employee_id

    WHERE e.employee_id = ?
    AND a.status = 'present'
    AND strftime('%m', a.work_date) = ?
    AND strftime('%Y', a.work_date) = ?

    GROUP BY e.employee_id
    """, (
        employee_id,
        f"{month:02}",
        str(year)
    ))

    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    config = load_config()
    overtime_multiplier = config["overtime_multiplier"]

    hourly_rate = result["hourly_rate"]
    total_work_hours = result["total_work_hours"] or 0
    total_overtime_hours = result["total_overtime_hours"] or 0

    normal_salary = (
        total_work_hours
        * hourly_rate
    )

    overtime_salary = (
        total_overtime_hours
        * hourly_rate
        * overtime_multiplier
    )

    total_salary = (
        normal_salary
        + overtime_salary
    )

    return {
        "employee_id": employee_id,

        "employee_name":
            f"{result['first_name']} "
            f"{result['last_name']}",

        "month": month,
        "year": year,

        "hourly_rate": hourly_rate,

        "total_work_hours":
            total_work_hours,

        "total_overtime_hours":
            total_overtime_hours,

        "normal_salary":
            normal_salary,

        "overtime_salary":
            overtime_salary,

        "total_salary":
            total_salary
    }


def calculate_monthly_payroll(current_user, employee_id, month, year):
    """
    Çalışanın aylık bordrosunu hesapla.
    - Admin: herhangi bir çalışan için hesaplayabilir
    - Normal kullanıcı: sadece kendi hesaplamasını yapabilir
    """
    
    # YETKİLENDİRME
    require_authenticated(current_user)
    ensure_self_or_admin(current_user, employee_id)

    return calculate_salary(employee_id, month, year)


def get_employee_monthly_payroll(current_user, employee_id, month, year):
    """
    Çalışanın aylık bordrosunu al.
    - Admin: herhangi bir çalışan için alabilir
    - Normal kullanıcı: sadece kendi bordrosunu görebilir
    """
    
    # YETKİLENDİRME
    require_authenticated(current_user)
    ensure_self_or_admin(current_user, employee_id)

    return calculate_salary(employee_id, month, year)


def get_payroll_summary(current_user, employee_id, month, year):
    """
    Bordrolu özeti al.
    - Admin: herhangi bir çalışan için alabilir
    - Normal kullanıcı: sadece kendi özetini görebilir
    """
    
    # YETKİLENDİRME
    require_authenticated(current_user)
    ensure_self_or_admin(current_user, employee_id)

    return calculate_salary(employee_id, month, year)