"""
Пользовательская иерархия исключений приложения.
"""


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier):
        super().__init__(404, f"{resource} с id {identifier} не найден", "NOT_FOUND")


class ValidationException(AppException):
    def __init__(self, detail: str):
        super().__init__(400, detail, "VALIDATION_ERROR")


class DuplicateError(AppException):
    def __init__(self, detail: str):
        super().__init__(409, detail, "DUPLICATE")
