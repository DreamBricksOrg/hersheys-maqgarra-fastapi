class NfceScrapperError(Exception):
    """Base exception for NFC-e scraper errors."""


class NfceInvalidUrlError(NfceScrapperError):
    """URL missing `p=` param or malformed 44-digit key."""


class NfceNetworkError(NfceScrapperError):
    """requests.RequestException wrapper."""


class NfceNotFoundError(NfceScrapperError):
    """HTTP 4xx/5xx or SEFAZ error container visible on page."""


class NfceParseError(NfceScrapperError):
    """Critical fields not found in HTML."""


class NfceCancelledError(NfceScrapperError):
    """Invoice is cancelled (hdfNotaCancelada == 'true')."""


class NfceDeniedError(NfceScrapperError):
    """Invoice is denied (hdfNotaDenegada == 'true')."""
