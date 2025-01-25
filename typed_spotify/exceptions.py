"""Custom exceptions for the Spotify client."""


class SpotifyError(Exception):
    """Base exception for all Spotify-related errors."""

    pass


class AuthenticationError(SpotifyError):
    """Raised when there is an authentication-related error."""

    pass


class RateLimitError(SpotifyError):
    """Raised when the Spotify API rate limit is exceeded."""

    pass


class ResourceNotFoundError(SpotifyError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(SpotifyError):
    """Raised when request parameters fail validation."""

    pass


class APIError(SpotifyError):
    """Raised when the Spotify API returns an unexpected error."""

    def __init__(self, message: str, status_code: int):
        """Initialize with message and status code."""
        super().__init__(message)
        self.status_code = status_code
