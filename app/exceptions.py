# Raised by services. The API turns them into HTTP errors (see main.py), the bot shows `detail` as text.
class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail


class Unauthorized(AppError):
    status_code = 401


class Forbidden(AppError):
    status_code = 403


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409