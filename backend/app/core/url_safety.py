"""Validation helpers for URLs fetched by the crawler."""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse


def validate_public_http_url(url: str) -> str:
    """Return a normalized public HTTP(S) URL or raise ValueError."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise ValueError("Private network destinations are not allowed")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(record[4][0])
                for record in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
            }
        except (OSError, ValueError) as exc:
            raise ValueError("URL host could not be resolved") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Private network destinations are not allowed")
    return url


def resolve_redirect(current_url: str, location: str) -> str:
    """Resolve and validate an HTTP redirect target."""
    return validate_public_http_url(urljoin(current_url, location))
