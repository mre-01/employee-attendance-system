"""
Servis katmanı için yetkilendirme yardımcı fonksiyonları.
Merkezi yetkilendirme mantığı bypass'ı önlemek için.
"""

from services.exceptions import AuthorizationError


def _get_user_field(user, field_name, default=None):
    """Dict veya object'ten güvenli bir şekilde user field'ını al."""
    if isinstance(user, dict):
        return user.get(field_name, default)
    return getattr(user, field_name, default)


def _get_user_id(user):
    """Kullanıcı dict veya object'ten employee_id al."""
    return _get_user_field(user, "employee_id")


def _is_admin(user):
    """Kullanıcının admin olup olmadığını kontrol et."""
    is_admin = _get_user_field(user, "is_admin", 0)
    return is_admin == 1


def require_admin(user):
    """
    Kullanıcının admin yetkilerine sahip olduğunu doğrula.
    Admin değilse AuthorizationError atar.
    """
    if not _is_admin(user):
        raise AuthorizationError("Bu işlem için admin yetkisi gerekli.")
    return True


def require_authenticated(user):
    """
    Kullanıcının giriş yaptığını doğrula.
    Giriş yapılmamışsa AuthorizationError atar.
    """
    if user is None:
        raise AuthorizationError("Lütfen giriş yapınız.")
    
    user_id = _get_user_id(user)
    if user_id is None:
        raise AuthorizationError("Geçersiz kullanıcı oturumu.")
    
    return True


def ensure_self_or_admin(user, employee_id):
    """
    Kullanıcının çalışan verilerine erişebileceğini doğrula.
    Admin herkese erişebilir, normal kullanıcılar sadece kendi verisini görebilir.
    Erişim reddedilirse AuthorizationError atar.
    """
    require_authenticated(user)
    
    user_id = _get_user_id(user)
    
    if _is_admin(user):
        return True
    
    if user_id != employee_id:
        raise AuthorizationError("Bu kaynağa erişim izniniz yok.")
    
    return True


def require_user_field(user, field_name):
    """
    Kullanıcının belirli bir field'a sahip olduğunu doğrula.
    Field eksikse AuthorizationError atar.
    """
    value = _get_user_field(user, field_name)
    if value is None:
        raise AuthorizationError(f"Kullanıcı bilgisi eksik: {field_name}")
    return value
