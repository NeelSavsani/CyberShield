"""
Browser Manager

Responsibilities:
- Start Playwright
- Launch Chromium
- Create browser context
- Create page
- Open URL
- Close browser
"""

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from app.services.url_safety import UnsafeTargetError, ensure_safe_analysis_target


class BrowserManager:
    """
    Manages the Playwright browser lifecycle.
    """

    def __init__(self):

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self):
        """
        Start Playwright and launch Chromium.
        """

        # Start Playwright
        self.playwright = await async_playwright().start()

        # Launch Chromium
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
            ],
        )

        # Create Browser Context
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            viewport={
                "width": 1366,
                "height": 768,
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139.0.0.0 "
                "Safari/537.36"
            ),
        )

        async def block_private_network_requests(route):
            request_url = route.request.url
            if request_url.startswith(("http://", "https://")):
                try:
                    await ensure_safe_analysis_target(request_url)
                except UnsafeTargetError:
                    await route.abort("blockedbyclient")
                    return
            await route.continue_()

        await self.context.route("**/*", block_private_network_requests)

        # Create Page
        self.page = await self.context.new_page()

        # Default timeout
        self.page.set_default_timeout(30000)

        # Default navigation timeout
        self.page.set_default_navigation_timeout(30000)

    async def open(self, url: str):
        """
        Open a webpage.
        """

        if self.page is None:
            raise RuntimeError(
                "Browser page was not initialized."
            )

        response = await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        # Wait a little so JavaScript can execute
        await self.page.wait_for_timeout(1500)

        return response

    async def close(self):
        """
        Close browser resources.
        """

        try:

            if self.page:
                await self.page.close()

        except Exception:
            pass

        try:

            if self.context:
                await self.context.close()

        except Exception:
            pass

        try:

            if self.browser:
                await self.browser.close()

        except Exception:
            pass

        try:

            if self.playwright:
                await self.playwright.stop()

        except Exception:
            pass
