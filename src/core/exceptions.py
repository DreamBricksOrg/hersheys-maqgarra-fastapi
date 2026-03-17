class AppError(Exception):
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthError(AppError):
    def __init__(self, message: str = "API key inválida ou inativa"):
        super().__init__("api_key_invalid", message, 401)
