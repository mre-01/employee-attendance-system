from sqlite3 import IntegrityError

from database.db import get_connection

from services.auth_service import hash_password
from services.auth_helpers import require_admin, require_authenticated
from services.exceptions import (
    AuthorizationError,
    ValidationError,
    EmployeeNotFoundError,
    DatabaseError,
    NotFoundError,
)
from services.validators import (
    validate_name,
    validate_email,
    validate_hourly_rate,
    validate_password,
    validate_department,
    validate_position,
)


def create_employee(
    current_user,
    first_name,
    last_name,
    email,
    department,
    position,
    hourly_rate,
    password,
    is_admin=0
):
    """Yeni çalışan oluştur. Admin erişimi gerekli."""
    
    # YETKİLENDİRME
    require_admin(current_user)

    # DOĞRULAMA
    # Merkezi validatörleri kullan (ValidationError atar başarısızda)
    first_name_clean = validate_name(first_name, "Ad")
    last_name_clean = validate_name(last_name, "Soyad")
    email_clean = validate_email(email)
    department_clean = validate_department(department)
    position_clean = validate_position(position)
    hourly_rate_clean = validate_hourly_rate(hourly_rate)
    password_clean = validate_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    password_hash = hash_password(password_clean)

    try:
        cursor.execute("""
        INSERT INTO employees (
            first_name,
            last_name,
            email,
            department,
            position,
            hourly_rate,
            active,
            is_admin,
            password_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            first_name_clean,
            last_name_clean,
            email_clean,
            department_clean,
            position_clean,
            hourly_rate_clean,
            1,
            is_admin,
            password_hash
        ))

        conn.commit()
        return True

    except IntegrityError:
        raise ValidationError("Bu email adresi zaten kullanımda.")

    finally:
        conn.close()


def get_all_employees(current_user):
    """
    Tüm çalışanları al. Admin erişimi gerekli.
    Admin olmayan kullanıcılar buna erişemezler.
    """
    
    # YETKİLENDİRME
    require_admin(current_user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        employee_id,
        first_name,
        last_name,
        email,
        department,
        position,
        hourly_rate,
        active,
        is_admin
    FROM employees
    ORDER BY employee_id ASC
    """)

    employees = cursor.fetchall()
    conn.close()

    return employees


def get_active_employees(current_user):
    """
    Tüm aktif çalışanları al. Admin erişimi gerekli.
    Admin olmayan kullanıcılar buna erişemezler.
    """
    
    # YETKİLENDİRME
    require_admin(current_user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        employee_id,
        first_name,
        last_name,
        email,
        department,
        position
    FROM employees
    WHERE active = 1
    ORDER BY employee_id ASC
    """)

    employees = cursor.fetchall()
    conn.close()

    return employees


def deactivate_employee(
    current_user,
    employee_id
):
    """Çalışanı devre dışı bırak. Admin erişimi gerekli."""
    # YETKİLENDİRME
    require_admin(current_user)

    # DOĞRULAMA
    try:
        eid = int(employee_id)
    except Exception:
        raise ValidationError("Geçersiz employee_id.")

    if eid <= 0:
        raise ValidationError("Geçersiz employee_id.")

    # Admin'in kendisini devre dışı bırakmasını engelle
    current_id = None
    try:
        if isinstance(current_user, dict):
            current_id = int(current_user.get("employee_id", None)) if current_user.get("employee_id", None) is not None else None
        else:
            current_id = int(getattr(current_user, "employee_id", None))
    except Exception:
        current_id = None

    if current_id is not None and current_id == eid:
        raise AuthorizationError("Kendi admin hesabınızı devre dışı bırakamazsınız.")

    # Varlığını kontrol et
    if not employee_exists(eid):
        raise EmployeeNotFoundError(f"Çalışan bulunamadı: {eid}")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE employees
        SET active = 0
        WHERE employee_id = ?
        """, (eid,))

        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Veritabanı hatası: {exc}")
    finally:
        conn.close()


def activate_employee(current_user, employee_id):
    """Çalışanı etkinleştir. Admin erişimi gerekli."""
    require_admin(current_user)

    try:
        eid = int(employee_id)
    except Exception:
        raise ValidationError("Geçersiz employee_id.")

    if eid <= 0:
        raise ValidationError("Geçersiz employee_id.")

    if not employee_exists(eid):
        raise EmployeeNotFoundError(f"Çalışan bulunamadı: {eid}")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE employees
        SET active = 1
        WHERE employee_id = ?
        """, (eid,))
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Veritabanı hatası: {exc}")
    finally:
        conn.close()


def get_employee_by_id(current_user, employee_id):
    """Id'ye göre çalışan satırını döndür. Yoksa EmployeeNotFoundError atar."""
    # yetkilendirme: admin erişimine izin ver
    require_authenticated(current_user)

    try:
        eid = int(employee_id)
    except Exception:
        raise ValidationError("Geçersiz employee_id.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT
            employee_id,
            first_name,
            last_name,
            email,
            department,
            position,
            hourly_rate,
            active,
            is_admin
        FROM employees
        WHERE employee_id = ?
        LIMIT 1
        """, (eid,))

        row = cursor.fetchone()
        if not row:
            raise EmployeeNotFoundError(f"Çalışan bulunamadı: {eid}")
        return row
    except EmployeeNotFoundError:
        raise
    except Exception as exc:
        raise DatabaseError(f"Veritabanı hatası: {exc}")
    finally:
        conn.close()


def employee_exists(employee_id):
    """Çalışan varsa True döndür, yoksa False."""
    try:
        eid = int(employee_id)
    except Exception:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM employees WHERE employee_id = ? LIMIT 1", (eid,))
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()





def _email_exists(email, exclude_employee_id=None):
    """Email var mı kontrol et (güncellemelerde belirli çalışanı hariç tut)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if exclude_employee_id:
            cursor.execute(
                "SELECT 1 FROM employees WHERE LOWER(email) = LOWER(?) AND employee_id != ? LIMIT 1",
                (email.strip().lower(), exclude_employee_id)
            )
        else:
            cursor.execute(
                "SELECT 1 FROM employees WHERE LOWER(email) = LOWER(?) LIMIT 1",
                (email.strip().lower(),)
            )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def update_employee(current_user, employee_id, updated_data):
    """
    Çalışan bilgisini güncelle. Admin erişimi gerekli.
    
    Parametreler:
    - current_user: Mevcut kimlik doğrulanan kullanıcı (admin gerekli)
    - employee_id: Güncellenecek çalışan
    - updated_data: Güncellenecek alanlar içeren dict
      Desteklenen: first_name, last_name, email, department, position, hourly_rate, active, is_admin
    
    Dönüş: Başarılıysa True
    Hata: ValidationError, AuthorizationError, EmployeeNotFoundError, DatabaseError
    """
    
    # YETKİLENDİRME
    require_admin(current_user)
    
    # employee_id doğrula
    try:
        eid = int(employee_id)
    except Exception:
        raise ValidationError("Geçersiz employee_id.")
    
    if eid <= 0:
        raise ValidationError("Geçersiz employee_id.")
    
    # Çalışanın var olup olmadığını kontrol et
    if not employee_exists(eid):
        raise EmployeeNotFoundError(f"Çalışan bulunamadı: {eid}")
    
    # Admin'in kendisini devre dışı bırakmasını engelle
    try:
        if isinstance(current_user, dict):
            current_id = current_user.get("employee_id")
        else:
            current_id = getattr(current_user, "employee_id", None)
        
        current_id = int(current_id) if current_id else None
    except Exception:
        current_id = None
    
    # Kendisini devre dışı bırakmaya çalışıyor mu kontrol et
    if current_id is not None and current_id == eid:
        if updated_data.get("active") == 0:
            raise AuthorizationError("Kendi hesabınızı devre dışı bırakamazsınız.")
    
    # DOĞRULAMA
    update_fields = {}
    
    # Alanları doğrula ve topla
    if "first_name" in updated_data:
        value = updated_data["first_name"]
        update_fields["first_name"] = validate_name(value, "Ad")
    
    if "last_name" in updated_data:
        value = updated_data["last_name"]
        update_fields["last_name"] = validate_name(value, "Soyad")
    
    if "email" in updated_data:
        value = updated_data["email"]
        email = validate_email(value)
        # Çoğaltılmış olup olmadığını kontrol et (mevcut çalışanı hariç tut)
        if _email_exists(email, exclude_employee_id=eid):
            raise ValidationError("Bu email adresi zaten kullanımda.")
        update_fields["email"] = email
    
    if "department" in updated_data:
        value = updated_data["department"]
        update_fields["department"] = validate_department(value)
    
    if "position" in updated_data:
        value = updated_data["position"]
        update_fields["position"] = validate_position(value)
    
    if "hourly_rate" in updated_data:
        update_fields["hourly_rate"] = validate_hourly_rate(updated_data["hourly_rate"])
    
    if "active" in updated_data:
        try:
            active = int(updated_data["active"])
            if active not in (0, 1):
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError("active alanı 0 veya 1 olmalıdır.")
        update_fields["active"] = active
    
    if "is_admin" in updated_data:
        try:
            is_admin = int(updated_data["is_admin"])
            if is_admin not in (0, 1):
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError("is_admin alanı 0 veya 1 olmalıdır.")
        update_fields["is_admin"] = is_admin
    
    # Güncellenecek alan yoksa
    if not update_fields:
        raise ValidationError("Güncellenecek alan yok.")
    
    # BUILD UPDATE QUERY
    set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(eid)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"""
        UPDATE employees
        SET {set_clause}
        WHERE employee_id = ?
        """, values)
        
        conn.commit()
        return True
    
    except IntegrityError as exc:
        conn.rollback()
        if "email" in str(exc).lower():
            raise ValidationError("Bu email adresi zaten kullanımda.")
        raise DatabaseError(f"Veritabanı hatası: {exc}")
    
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Veritabanı hatası: {exc}")
    
    finally:
        conn.close()