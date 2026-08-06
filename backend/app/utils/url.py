"""
URL Utility Functions

Responsibilities:
- Normalize URLs
- Validate URL format
- Extract hostname
- Extract registered domain
- Detect IP-based URLs
"""

from urllib.parse import urlparse
import ipaddress

import tldextract
import validators


def normalize_url(url: str) -> str:
    """
    Normalize a URL.

    Example:
        google.com
        -> https://google.com

        HTTP://Google.COM
        -> http://google.com
    """

    url = url.strip()

    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc
    )

    return normalized.geturl()


def is_valid_url(url: str) -> bool:
    """
    Validate URL syntax.
    """

    return validators.url(url)


def get_hostname(url: str) -> str:
    """
    Return hostname.

    Example:

    https://sub.example.com/login

    -> sub.example.com
    """

    parsed = urlparse(normalize_url(url))

    return parsed.hostname or ""


def get_registered_domain(url: str) -> str:
    """
    Return registered domain.

    Example:

    https://mail.google.com

    -> google.com
    """

    hostname = get_hostname(url)

    extracted = tldextract.extract(hostname)

    if not extracted.domain:
        return ""

    return f"{extracted.domain}.{extracted.suffix}"


def get_subdomain(url: str) -> str:
    """
    Return subdomain.

    mail.google.com

    -> mail
    """

    hostname = get_hostname(url)

    extracted = tldextract.extract(hostname)

    return extracted.subdomain


def is_ip_address(url: str) -> bool:
    """
    Check whether hostname is an IP address.
    """

    hostname = get_hostname(url)

    try:
        ipaddress.ip_address(hostname)
        return True

    except ValueError:
        return False


def is_localhost(url: str) -> bool:
    """
    Detect localhost.
    """

    hostname = get_hostname(url)

    return hostname in (
        "localhost",
        "127.0.0.1",
        "::1"
    )