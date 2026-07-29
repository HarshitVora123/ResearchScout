"""Custom exception classes for ResearchScout."""


class ResearchScoutError(Exception):
    """Base exception for all ResearchScout errors."""

    def __init__(self, message: str = "An error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(ResearchScoutError):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            status_code=404,
        )


class AuthenticationError(ResearchScoutError):
    """Authentication failed."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, status_code=401)


class AuthorizationError(ResearchScoutError):
    """User not authorized for this action."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=403)


class ValidationError(ResearchScoutError):
    """Input validation failed."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message=message, status_code=422)


class RateLimitError(ResearchScoutError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message=message, status_code=429)


class ExternalServiceError(ResearchScoutError):
    """External service (LLM, search API, etc.) failed."""

    def __init__(self, service: str, message: str = ""):
        super().__init__(
            message=f"External service error ({service}): {message}",
            status_code=502,
        )


class CrawlError(ResearchScoutError):
    """Crawling a URL failed."""

    def __init__(self, url: str, message: str = ""):
        super().__init__(
            message=f"Crawl failed for {url}: {message}",
            status_code=502,
        )


class ExtractionError(ResearchScoutError):
    """Information extraction from content failed."""

    def __init__(self, message: str = "Failed to extract structured data"):
        super().__init__(message=message, status_code=500)
