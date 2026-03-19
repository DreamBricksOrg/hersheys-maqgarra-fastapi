class WebmaniaNfeError(Exception):
    """Base exception for WebmaniaNFe API errors."""


class WebmaniaAuthError(WebmaniaNfeError):
    """Invalid or missing API token."""


class WebmaniaNetworkError(WebmaniaNfeError):
    """HTTP/connection failure."""


class WebmaniaValidationError(WebmaniaNfeError):
    """API returned a validation/business error."""


class WebmaniaNotFoundError(WebmaniaNfeError):
    """Requested resource not found (404)."""
