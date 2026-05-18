from services.exceptions import ValidationError
import re

# Constants (reduce magic numbers)
NAME_REGEX = r"^[A-Za-zÇçĞğİıÖöŞşÜü\s]+$"
NAME_MIN_LEN = 2
NAME_MAX_LEN = 50
PASSWORD_MIN_LEN = 4
MAX_HOURLY_RATE = 100000
FIELD_MAX_LEN = 100


def _ensure_str(value, field_name):
    """String tipi kontrol et, değilse ValidationError at."""
    if value is None:
        raise ValidationError(f"{field_name} alanı boş olamaz.")
    if not isinstance(value, str):
        # Sayısal hourly_rate başka yerde geçilecek
        raise ValidationError(f"{field_name} alanı geçersiz türde.")
    return value


def validate_name(value, field_name="Name"):
    """Ad doğrula: Sadece Türkçe+İngilizce harfler ve boşluk.

    Başarılıda kırpılmış değer döndür, başarısızda ValidationError at.
    """
    value = _ensure_str(value, field_name)
    value = value.strip()
    if not value:
        raise ValidationError(f"{field_name} alanı boş olamaz.")
    if len(value) < NAME_MIN_LEN:
        raise ValidationError(f"{field_name} en az {NAME_MIN_LEN} karakter olmalıdır.")
    if len(value) > NAME_MAX_LEN:
        raise ValidationError(f"{field_name} en fazla {NAME_MAX_LEN} karakter olabilir.")
    if not re.match(NAME_REGEX, value):
        raise ValidationError(f"{field_name} sadece harf ve boşluk içerebilir.")
    return value


def validate_email(email):
    """Email doğrula ve normalleştir. Küçük harf, kırpılmış email döndür."""
    if email is None:
        raise ValidationError("Email alanı boş olamaz.")
    if not isinstance(email, str):
        raise ValidationError("Email alanı geçersiz türde.")
    email = email.strip().lower()
    if not email:
        raise ValidationError("Email alanı boş olamaz.")
    # Basit ve pratik email regex
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    if not re.match(pattern, email):
        raise ValidationError("Geçersiz email formatı.")
    return email


def validate_hourly_rate(rate):
    """Saatlik ücret doğrula: Sayısal olmalı, > 0 ve <= MAX_HOURLY_RATE."""
    if rate is None:
        raise ValidationError("Saatlik ücret alanı boş olamaz.")
    try:
        numeric = float(rate)
    except (TypeError, ValueError):
        raise ValidationError("Saatlik ücret geçerli bir sayı olmalıdır.")
    if numeric <= 0:
        raise ValidationError("Saatlik ücret 0'dan büyük olmalıdır.")
    if numeric > MAX_HOURLY_RATE:
        raise ValidationError(f"Saatlik ücret {MAX_HOURLY_RATE} değerinden büyük olamaz.")
    return numeric


def validate_password(password):
    """Parola doğrula: Boş olmayacak, sadece boşluk olmayacak, minimum uzunluk."""
    if password is None:
        raise ValidationError("Parola alanı boş olamaz.")
    if not isinstance(password, str):
        raise ValidationError("Parola alanı geçersiz türde.")
    if not password.strip():
        raise ValidationError("Parola boş veya sadece boşluk olamaz.")
    if len(password) < PASSWORD_MIN_LEN:
        raise ValidationError(f"Parola en az {PASSWORD_MIN_LEN} karakter olmalıdır.")
    return password


def _validate_generic_field(value, field_name, max_len=FIELD_MAX_LEN):
    if value is None:
        raise ValidationError(f"{field_name} alanı boş olamaz.")
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} alanı geçersiz türde.")
    s = value.strip()
    if not s:
        raise ValidationError(f"{field_name} alanı boş olamaz.")
    if len(s) > max_len:
        raise ValidationError(f"{field_name} en fazla {max_len} karakter olabilir.")
    # Sadece özel karakterler (harf/sayı yok) olan değerleri reddet
    if not re.search(r"[A-Za-z0-9ÇçĞğİıÖöŞşÜü]", s):
        raise ValidationError(f"{field_name} geçersiz karakterler içeriyor.")
    return s


def validate_department(value):
    return _validate_generic_field(value, "Departman")


def validate_position(value):
    return _validate_generic_field(value, "Pozisyon")
