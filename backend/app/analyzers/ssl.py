"""
SSL/TLS Intelligence Analyzer

Responsibilities:
- Check HTTPS certificate
- Certificate issuer
- Certificate subject
- Certificate validity
- Certificate age
- Days until expiration
- TLS version
- Cipher suite
- Subject Alternative Names (SAN)
"""

from datetime import datetime, timezone
from typing import Dict, Any
import socket
import ssl

from app.utils.url import get_hostname


class SSLAnalyzer:
    """
    SSL/TLS Intelligence Analyzer
    """

    async def analyze(self, url: str) -> Dict[str, Any]:

        hostname = get_hostname(url)

        result = {
            "hostname": hostname,
            "ssl_available": False,
            "issuer": None,
            "subject": None,
            "serial_number": None,
            "version": None,
            "cipher": None,
            "certificate_start": None,
            "certificate_expiry": None,
            "certificate_age_days": None,
            "days_until_expiration": None,
            "subject_alt_names": [],
            "error": None,
        }

        try:

            context = ssl.create_default_context()

            with socket.create_connection(
                (hostname, 443),
                timeout=10
            ) as sock:

                with context.wrap_socket(
                    sock,
                    server_hostname=hostname
                ) as secure_sock:

                    cert = secure_sock.getpeercert()

                    result["ssl_available"] = True

                    result["version"] = secure_sock.version()

                    cipher = secure_sock.cipher()

                    if cipher:
                        result["cipher"] = cipher[0]

                    result["serial_number"] = cert.get(
                        "serialNumber"
                    )

                    result["issuer"] = self._flatten_name(
                        cert.get("issuer", [])
                    )

                    result["subject"] = self._flatten_name(
                        cert.get("subject", [])
                    )

                    start = datetime.strptime(
                        cert["notBefore"],
                        "%b %d %H:%M:%S %Y %Z"
                    ).replace(
                        tzinfo=timezone.utc
                    )

                    expiry = datetime.strptime(
                        cert["notAfter"],
                        "%b %d %H:%M:%S %Y %Z"
                    ).replace(
                        tzinfo=timezone.utc
                    )

                    result["certificate_start"] = (
                        start.isoformat()
                    )

                    result["certificate_expiry"] = (
                        expiry.isoformat()
                    )

                    now = datetime.now(
                        timezone.utc
                    )

                    result["certificate_age_days"] = (
                        now - start
                    ).days

                    result["days_until_expiration"] = (
                        expiry - now
                    ).days

                    sans = cert.get(
                        "subjectAltName",
                        []
                    )

                    result["subject_alt_names"] = [
                        value
                        for key, value in sans
                        if key == "DNS"
                    ]

        except Exception as e:

            result["error"] = str(e)

        return result

    def _flatten_name(self, entries):

        output = {}

        for entry in entries:

            for key, value in entry:

                output[key] = value

        return output