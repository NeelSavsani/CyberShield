"""
Domain Intelligence Analyzer

Responsibilities:
- Registered domain
- WHOIS lookup
- Registrar
- Registration date
- Expiration date
- Updated date
- Domain age
- Days until expiration
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import whois
from dateutil.parser import parse

from app.utils.url import get_registered_domain


class DomainAnalyzer:
    """
    Domain Intelligence Analyzer
    """

    async def analyze(self, url: str) -> Dict[str, Any]:

        domain = get_registered_domain(url)

        result = {
            "domain": domain,
            "whois_found": False,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "updated_date": None,
            "domain_age_days": None,
            "days_until_expiration": None,
            "name_servers": [],
            "dnssec": None,      # Filled later by DNS analyzer
            "error": None,
        }

        if not domain:
            result["error"] = "Unable to determine registered domain."
            return result

        try:

            w = whois.whois(domain)

            result["whois_found"] = True

            result["registrar"] = self._safe_string(
                w.registrar
            )

            creation = self._first_date(
                w.creation_date
            )

            expiration = self._first_date(
                w.expiration_date
            )

            updated = self._first_date(
                w.updated_date
            )

            result["creation_date"] = self._date_to_string(
                creation
            )

            result["expiration_date"] = self._date_to_string(
                expiration
            )

            result["updated_date"] = self._date_to_string(
                updated
            )

            if creation:
                result["domain_age_days"] = (
                    datetime.now(timezone.utc) - creation
                ).days

            if expiration:
                result["days_until_expiration"] = (
                    expiration - datetime.now(timezone.utc)
                ).days

            result["name_servers"] = self._normalize_nameservers(
                w.name_servers
            )

        except Exception as e:

            result["error"] = str(e)

        return result

    def _first_date(self, value) -> Optional[datetime]:
        """
        WHOIS libraries sometimes return
        a single datetime or a list of datetimes.
        """

        if value is None:
            return None

        if isinstance(value, list):
            value = value[0]

        if isinstance(value, str):
            value = parse(value)

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return value

    def _date_to_string(
        self,
        value: Optional[datetime]
    ) -> Optional[str]:

        if value is None:
            return None

        return value.isoformat()

    def _safe_string(self, value):

        if value is None:
            return None

        if isinstance(value, list):
            if len(value) == 0:
                return None

            return str(value[0])

        return str(value)

    def _normalize_nameservers(self, value):

        if value is None:
            return []

        if not isinstance(value, list):
            value = [value]

        return sorted(
            list(
                {
                    str(ns).lower()
                    for ns in value
                }
            )
        )