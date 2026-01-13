from typing import Any, Optional


class BracketSDKError(Exception):
    """Base class for SDK errors."""


class ApiError(BracketSDKError):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AuthenticationError(ApiError):
    """Raised when API key authentication fails."""


class RateLimitError(ApiError):
    """Raised when the API rate limit is exceeded."""


class NotFoundError(ApiError):
    """Raised when a resource cannot be found."""


class NetworkError(BracketSDKError):
    """Raised when a network error occurs."""
