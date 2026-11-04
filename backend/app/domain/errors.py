# Domain errors carry a stable machine-readable code and a Ukrainian message for
# the UI. The API layer maps each family to an HTTP status in one place.


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"


class Forbidden(DomainError):
    code = "forbidden"


class InvalidData(DomainError):
    code = "invalid_data"
