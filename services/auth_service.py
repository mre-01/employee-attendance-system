import bcrypt

from database.db import get_connection


REQUIRED_USER_FIELDS = [
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "position",
    "is_admin",
]


def hash_password(password):
    """Şifreyi bcrypt ile hashle."""
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()


def verify_password(password, hashed_password):
    """Şifreyi doğrula."""
    return bcrypt.checkpw(
        password.encode(),
        hashed_password.encode()
    )


def get_user_id(user):
    """Kullanıcı dict, sqlite3.Row veya object'ten employee_id çıkar."""
    if user is None:
        return None
    
    if isinstance(user, dict):
        return user.get("employee_id")
    
    # sqlite3.Row (has .keys() method)
    if hasattr(user, "keys") and callable(getattr(user, "keys")):
        try:
            return user["employee_id"]
        except (KeyError, TypeError):
            return None
    
    return getattr(user, "employee_id", None)


def normalize_user(user):
    """
    Kullanıcı object'ini (sqlite3.Row, dict veya object) standart dict'e dönüştür.
    
    Tüm gerekli alanların mevcut olmasını sağlar.
    Kullanıcı None ise veya employee_id yoksa ValueError atar.
    """
    if user is None:
        raise ValueError("Kullanıcı nesnesi None'dur.")

    user_dict = {}

    # dict işle
    if isinstance(user, dict):
        user_dict = dict(user)
    # sqlite3.Row işle (.keys() methoduna sahip)
    elif hasattr(user, "keys") and callable(getattr(user, "keys")):
        user_dict = {key: user[key] for key in user.keys()}
    # Normal object'leri işle
    else:
        for field in REQUIRED_USER_FIELDS:
            user_dict[field] = getattr(user, field, None)

    if not user_dict.get("employee_id"):
        raise ValueError("Kullanıcı verisinde Employee ID bulunamadı.")

    for field in REQUIRED_USER_FIELDS:
        if field not in user_dict:
            user_dict[field] = None

    return user_dict


def login(email, password):
    """Giriş yap ve kullanıcı döndür. Başarısızsa None döndür."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM employees
    WHERE email = ?
    """, (
        email.strip().lower(),
    ))

    user = cursor.fetchone()

    conn.close()

    if not user:
        return None

    if verify_password(
        password,
        user["password_hash"]
    ):
        return normalize_user(user)

    return None