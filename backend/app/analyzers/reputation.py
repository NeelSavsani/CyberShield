"""Opt-in reputation intelligence from supported threat feeds."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class ReputationAnalyzer:
    """Query configured providers; absent API keys simply leave a source unavailable."""

    async def analyze(self, url: str) -> dict[str, Any]:
        providers: dict[str, Any] = {
            "virustotal": {"configured": bool(settings.virus_total_api_key), "flagged": None, "detections": None},
            "google_safe_browsing": {"configured": bool(settings.google_safe_browsing_api_key), "flagged": None},
            "openphish": {"configured": False, "flagged": None, "reason": "Feed integration pending"},
            "urlhaus": {"configured": False, "flagged": None, "reason": "Feed integration pending"},
        }
        if settings.virus_total_api_key:
            providers["virustotal"] = await self._virus_total(url)
        if settings.google_safe_browsing_api_key:
            providers["google_safe_browsing"] = await self._safe_browsing(url)

        detections = providers["virustotal"].get("detections")
        safe_browsing_flagged = providers["google_safe_browsing"].get("flagged")
        return {
            "providers": providers,
            "detection_count": detections,
            "safe_browsing_flagged": safe_browsing_flagged,
        }

    async def _virus_total(self, url: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers={"x-apikey": settings.virus_total_api_key or ""},
                    data={"url": url},
                )
            if response.status_code >= 400:
                return {"configured": True, "flagged": None, "detections": None, "error": f"HTTP {response.status_code}"}
            # VirusTotal URL analysis is asynchronous. The submission ID is kept
            # for a later polling worker rather than pretending it is a verdict.
            return {"configured": True, "flagged": None, "detections": None, "analysis_id": response.json().get("data", {}).get("id")}
        except httpx.HTTPError as error:
            return {"configured": True, "flagged": None, "detections": None, "error": str(error)}

    async def _safe_browsing(self, url: str) -> dict[str, Any]:
        request_body = {
            "client": {"clientId": "cybershield", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(
                    "https://safebrowsing.googleapis.com/v4/threatMatches:find",
                    params={"key": settings.google_safe_browsing_api_key},
                    json=request_body,
                )
            if response.status_code >= 400:
                return {"configured": True, "flagged": None, "error": f"HTTP {response.status_code}"}
            return {"configured": True, "flagged": bool(response.json().get("matches"))}
        except httpx.HTTPError as error:
            return {"configured": True, "flagged": None, "error": str(error)}
