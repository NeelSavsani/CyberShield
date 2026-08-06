"""Convert collected URL evidence into a stable, model-ready feature set."""

from __future__ import annotations

from typing import Any


class FeatureExtractor:
    """Extract behavioural and infrastructure features, never URL character counts."""

    schema_version = "evidence-v1"

    def extract(self, evidence: dict[str, Any]) -> dict[str, Any]:
        domain = evidence.get("domain", {})
        dns = evidence.get("dns", {})
        tls = evidence.get("ssl", {})
        http = evidence.get("http", {})
        browser = evidence.get("browser", {})
        html = evidence.get("html", {})
        forms = evidence.get("form", {})
        javascript = evidence.get("javascript", {})
        reputation = evidence.get("reputation", {})

        age = self._number(domain.get("domain_age_days"))
        certificate_age = self._number(tls.get("certificate_age_days"))
        detections = self._number(reputation.get("detection_count"))

        values = {
            "domain_age_days": age,
            "certificate_age_days": certificate_age,
            "domain_age_risk": self._recency_risk(age, 365),
            "certificate_age_risk": self._recency_risk(certificate_age, 90),
            "dnssec_enabled": self._boolean(dns.get("dnssec_enabled")),
            "http_reachable": self._boolean(http.get("reachable")),
            "redirect_count": self._number(http.get("redirect_count"), default=0),
            "has_valid_tls": self._boolean(tls.get("ssl_available")),
            "password_field_count": self._number(forms.get("password_fields"), default=0),
            "otp_field_count": self._number(forms.get("otp_fields"), default=0),
            "credit_card_field_count": self._number(forms.get("credit_card_fields"), default=0),
            "cross_domain_form_actions": self._number(forms.get("cross_domain_actions"), default=0),
            "insecure_form_actions": len(forms.get("insecure_actions") or []),
            "get_login_forms": self._number(forms.get("get_login_forms"), default=0),
            "hidden_iframe_count": len(html.get("hidden_iframes") or []),
            "meta_refresh_present": self._boolean(html.get("meta_refresh")),
            "popup_count": len(browser.get("popups") or []),
            "download_count": len(browser.get("downloads") or []),
            "permission_request_count": len(browser.get("permission_requests") or []),
            "javascript_error_count": self._number(
                javascript.get("javascript_error_count"), default=len(browser.get("javascript_errors") or [])
            ),
            "obfuscated_script_count": self._number(javascript.get("obfuscated_scripts"), default=0),
            "reputation_detection_count": detections,
            "safe_browsing_flagged": self._boolean(reputation.get("safe_browsing_flagged")),
        }
        available = {
            "domain": bool(domain) and domain.get("error") is None,
            "dns": bool(dns) and dns.get("error") is None,
            "tls": bool(tls) and tls.get("error") is None,
            "http": bool(http) and http.get("error") is None,
            "browser": bool(browser) and browser.get("browser_error") is None,
            "page_content": bool(html) and html.get("html_available") is True,
            "forms": bool(forms) and forms.get("forms_available") is not False,
            "reputation": bool(reputation),
        }
        return {"schema_version": self.schema_version, "values": values, "available_sources": available}

    @staticmethod
    def _number(value: Any, default: float | int | None = None) -> float | int | None:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _boolean(value: Any) -> int:
        return int(bool(value))

    @staticmethod
    def _recency_risk(age: float | int | None, window_days: int) -> float | None:
        if age is None or age < 0:
            return None
        return round(max(0.0, 1 - (age / window_days)), 4)
