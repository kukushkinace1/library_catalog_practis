class AppException(Exception):
    """Base application exception with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    """Base exception for missing resources."""

    def __init__(self, resource: str, identifier: object):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' not found",
            status_code=404,
        )
