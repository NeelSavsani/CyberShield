"""Analyse JavaScript observed in the browser-rendered document."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.models.browser_session import BrowserSession


class JavaScriptAnalyzer:
    """Extract behavioural JavaScript evidence without executing additional code."""

    _obfuscation_markers = (
        "eval(",
        "function(",
        "atob(",
        "fromcharcode(",
        "unescape(",
    )

    async def analyze(self, browser_session: BrowserSession) -> dict:
        if not browser_session.html:
            return {
                "javascript_available": False,
                "script_count": 0,
                "obfuscated_scripts": 0,
                "error": "No rendered HTML available.",
            }

        soup = BeautifulSoup(browser_session.html, "lxml")
        scripts = soup.find_all("script")
        result = {
            "javascript_available": True,
            "script_count": len(scripts),
            "inline_script_count": 0,
            "external_script_count": 0,
            "external_script_sources": [],
            "obfuscated_scripts": 0,
            "dynamic_code_generation": 0,
            "clipboard_access_indicators": 0,
            "keyboard_event_indicators": 0,
            "network_request_indicators": 0,
            "browser_javascript_error_count": len(browser_session.javascript_errors),
            "error": None,
        }

        for script in scripts:
            source = script.get("src")
            if source:
                result["external_script_count"] += 1
                result["external_script_sources"].append(source)
                continue

            result["inline_script_count"] += 1
            text = script.get_text(" ", strip=True).lower()
            if not text:
                continue

            marker_count = sum(marker in text for marker in self._obfuscation_markers)
            high_entropy_tokens = len(re.findall(r"[a-z0-9+/]{80,}={0,2}", text))
            if marker_count >= 2 or high_entropy_tokens:
                result["obfuscated_scripts"] += 1
            result["dynamic_code_generation"] += int("eval(" in text or "function(" in text)
            result["clipboard_access_indicators"] += int("clipboard" in text)
            result["keyboard_event_indicators"] += int("keydown" in text or "keypress" in text)
            result["network_request_indicators"] += int("fetch(" in text or "xmlhttprequest" in text)

        result["external_script_sources"] = sorted(set(result["external_script_sources"]))
        return result
