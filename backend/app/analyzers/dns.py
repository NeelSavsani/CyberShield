"""
DNS Analyzer

Responsibilities:
- Resolve A records
- Resolve AAAA records
- Resolve MX records
- Resolve NS records
- Resolve TXT records
- Resolve CNAME records
- Check DNSSEC
"""

from typing import Any, Dict, List

import dns.resolver
import dns.exception

from app.utils.url import get_hostname


class DNSAnalyzer:
    """
    DNS Intelligence Analyzer
    """

    def __init__(self):
        self.resolver = dns.resolver.Resolver()

        self.resolver.timeout = 5
        self.resolver.lifetime = 5

    async def analyze(self, url: str) -> Dict[str, Any]:

        hostname = get_hostname(url)

        result = {
            "hostname": hostname,
            "a_records": [],
            "aaaa_records": [],
            "mx_records": [],
            "ns_records": [],
            "txt_records": [],
            "cname_records": [],
            "dnssec_enabled": False,
            "error": None,
        }

        try:

            result["a_records"] = self._resolve(
                hostname,
                "A"
            )

            result["aaaa_records"] = self._resolve(
                hostname,
                "AAAA"
            )

            result["mx_records"] = self._resolve(
                hostname,
                "MX"
            )

            result["ns_records"] = self._resolve(
                hostname,
                "NS"
            )

            result["txt_records"] = self._resolve(
                hostname,
                "TXT"
            )

            result["cname_records"] = self._resolve(
                hostname,
                "CNAME"
            )

            result["dnssec_enabled"] = self._check_dnssec(
                hostname
            )

        except Exception as e:

            result["error"] = str(e)

        return result

    def _resolve(
        self,
        hostname: str,
        record_type: str
    ) -> List[str]:
        """
        Resolve a DNS record.
        """

        try:

            answers = self.resolver.resolve(
                hostname,
                record_type
            )

            return [
                str(answer).strip()
                for answer in answers
            ]

        except (
            dns.resolver.NoAnswer,
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
            dns.exception.Timeout,
        ):

            return []

    def _check_dnssec(
        self,
        hostname: str
    ) -> bool:
        """
        Basic DNSSEC detection.

        If DNSKEY exists,
        DNSSEC is considered enabled.
        """

        try:

            self.resolver.resolve(
                hostname,
                "DNSKEY"
            )

            return True

        except Exception:

            return False