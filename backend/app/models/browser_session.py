"""
Browser Session Model

Stores everything collected during a single Playwright session.

This object is shared between analyzers so the website
is rendered only once.
"""

from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
)


@dataclass
class BrowserSession:
    """
    Browser session shared across analyzers.
    """

    # ----------------------------------------------------
    # Playwright Objects
    # ----------------------------------------------------

    browser: Browser | None = None
    context: BrowserContext | None = None
    page: Page | None = None

    # ----------------------------------------------------
    # URL Information
    # ----------------------------------------------------

    original_url: str = ""
    final_url: str = ""

    # ----------------------------------------------------
    # Page Content
    # ----------------------------------------------------

    html: str = ""
    title: str = ""

    # ----------------------------------------------------
    # Screenshot
    # ----------------------------------------------------

    screenshot_path: str | None = None
    screenshot_bytes: bytes | None = None

    # ----------------------------------------------------
    # Cookies
    # ----------------------------------------------------

    cookies: list[dict] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Local / Session Storage
    # ----------------------------------------------------

    local_storage: dict = field(
        default_factory=dict
    )

    session_storage: dict = field(
        default_factory=dict
    )

    # ----------------------------------------------------
    # Console Logs
    # ----------------------------------------------------

    console_logs: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # JavaScript Errors
    # ----------------------------------------------------

    javascript_errors: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Network Activity
    # ----------------------------------------------------

    network_requests: list[dict] = field(
        default_factory=list
    )

    network_responses: list[dict] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Redirects
    # ----------------------------------------------------

    redirect_chain: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Permissions
    # ----------------------------------------------------

    permission_requests: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Downloads
    # ----------------------------------------------------

    downloads: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Popups
    # ----------------------------------------------------

    popups: list[str] = field(
        default_factory=list
    )

    # ----------------------------------------------------
    # Metadata
    # ----------------------------------------------------

    load_time_ms: float | None = None

    error: str | None = None

    status_code: int | None = None

    content_type: str | None = None

    headers: dict[str, Any] = field(
        default_factory=dict
    )
