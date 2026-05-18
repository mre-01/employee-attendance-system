class AuthenticationError(Exception):
    """Kimlik doğrulama başarısız olduğunda atılır"""
    pass


class AuthorizationError(Exception):
    """Kullanıcının gerekli izni olmadığında atılır"""
    pass


class ValidationError(Exception):
    """Giriş doğrulaması başarısız olduğunda atılır"""
    pass


class NotFoundError(Exception):
    """İstenen kaynak bulunmadığında atılır"""
    pass


class EmployeeNotFoundError(NotFoundError):
    """Çalışan bulunamadığında atılır"""
    pass


class DuplicateAttendanceError(Exception):
    """Yinelenen yoklama kaydı bulunduğunda atılır"""
    pass


class DatabaseError(Exception):
    """Veritabanı işlemi başarısız olduğunda atılır"""
    pass