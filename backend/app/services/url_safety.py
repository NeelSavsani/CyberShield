"""Admission checks for URLs that CyberShield will investigate."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeTargetError(ValueError):
    """Raised when a URL would target a local or private network."""


def _is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global


def _resolve_public_addresses(hostname: str) -> list[str]:
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except socket.gaierror:
        # A non-resolving public hostname is safe to pass to the collectors; they
        # will report that it does not exist or cannot be reached.
        return []

    non_public = [address for address in addresses if not _is_public_ip(address)]
    if non_public:
        raise UnsafeTargetError(
            "CyberShield does not analyze URLs that resolve to private or local IP addresses."
        )
    return sorted(addresses)


async def ensure_safe_analysis_target(url: str) -> list[str]:
    """Block SSRF-style requests before HTTP, TLS, or browser collection begins."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise UnsafeTargetError("Only complete HTTP and HTTPS URLs can be analyzed.")

    # Credentials in a scan URL can leak secrets to logs, redirects, or the
    # browser session.  They are not needed for public-site analysis.
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeTargetError("URLs containing embedded credentials cannot be analyzed.")

    # Reject malformed/unsafe ports before any network client sees the URL.
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeTargetError("The URL contains an invalid port.") from exc
    if port is not None and not (1 <= port <= 65535):
        raise UnsafeTargetError("The URL contains an invalid port.")

    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise UnsafeTargetError("CyberShield does not analyze localhost targets.")

    try:
        if not _is_public_ip(hostname):
            raise UnsafeTargetError(
                "CyberShield does not analyze URLs that use private or local IP addresses."
            )
        return [hostname]
    except ValueError:
        return await asyncio.to_thread(_resolve_public_addresses, hostname)
