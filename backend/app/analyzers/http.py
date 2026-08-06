"""
HTTP Analyzer

Responsibilities:
- Check website availability
- Measure response time
- Collect HTTP status code
- Collect redirect information
- Collect response headers
- Collect cookies
- Collect server information
"""

import time
from typing import Dict, Any
from urllib.parse import urljoin

import httpx

from app.services.url_safety import ensure_safe_analysis_target


class HTTPAnalyzer:
    """
    HTTP Analysis Module
    """

    def __init__(self):
        self.timeout = 15

        self.headers = {
            "User-Agent": (
                "CyberShield/1.0 "
                "(Security Research Platform)"
            )
        }

    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        Analyze HTTP behaviour of a website.
        """

        result = {
            "reachable": False,
            "status_code": None,
            "response_time_ms": None,
            "final_url": None,
            "redirect_count": 0,
            "redirect_chain": [],
            "headers": {},
            "cookies": {},
            "server": None,
            "content_type": None,
            "content_length": None,
            "error": None
        }

        start_time = time.perf_counter()

        try:

            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=self.timeout,
                headers=self.headers,
            ) as client:
                current_url = url
                response = None
                for _ in range(11):
                    await ensure_safe_analysis_target(current_url)
                    response = await client.get(current_url)
                    location = response.headers.get("location")
                    if not location or response.status_code not in {301, 302, 303, 307, 308}:
                        break

                    next_url = urljoin(str(response.url), location)
                    result["redirect_chain"].append(next_url)
                    current_url = next_url
                else:
                    raise RuntimeError("Redirect limit exceeded (10 redirects).")

                if response is None:
                    raise RuntimeError("No HTTP response was received.")

            elapsed = (
                time.perf_counter() - start_time
            ) * 1000

            result["reachable"] = True
            result["status_code"] = response.status_code
            result["response_time_ms"] = round(elapsed, 2)
            result["final_url"] = str(response.url)

            result["redirect_count"] = len(result["redirect_chain"])

            result["headers"] = dict(response.headers)

            result["cookies"] = {
                cookie.name: cookie.value
                for cookie in response.cookies.jar
            }

            result["server"] = response.headers.get(
                "Server"
            )

            result["content_type"] = response.headers.get(
                "Content-Type"
            )

            result["content_length"] = response.headers.get(
                "Content-Length"
            )

        except Exception as e:

            result["error"] = str(e)

        return result
