"""
Browser Analyzer

Phase 1
--------
Responsibilities

✔ Launch browser
✔ Open website
✔ Collect:
    - Final URL
    - HTML
    - Page title
    - Cookies
    - Screenshot

Future phases

✔ Console logs
✔ Network requests
✔ Downloads
✔ Popups
✔ Permissions
✔ Local Storage
✔ Session Storage
"""

from playwright.async_api import (
    ConsoleMessage,
    Download,
    Request,
    Response,
)

import time
from uuid import uuid4

from pathlib import Path

from app.models.browser_session import BrowserSession
from app.services.browser_manager import BrowserManager


class BrowserAnalyzer:

    def __init__(self):

        self.manager = BrowserManager()

    async def _activate_scroll_content(self, page) -> None:
        """Visit scroll-triggered sections before creating a full-page capture.

        Many modern sites use IntersectionObserver, lazy-loading, or scroll
        animation libraries.  A direct ``full_page`` screenshot does not make
        those sections visible first, leaving their reserved space blank.
        """
        await page.evaluate(
            """async () => {
                const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
                const root = document.documentElement;
                const step = Math.max(Math.floor(window.innerHeight * 0.75), 400);
                const maxSteps = 60;

                // Avoid a site-defined smooth-scroll animation masking the
                // actual scroll events needed by lazy loaders and observers.
                const originalBehavior = root.style.scrollBehavior;
                root.style.scrollBehavior = 'auto';

                for (let index = 0; index < maxSteps; index += 1) {
                    const before = Math.max(root.scrollHeight, document.body.scrollHeight);
                    window.scrollBy(0, step);
                    await pause(140);
                    const after = Math.max(root.scrollHeight, document.body.scrollHeight);
                    const atBottom = window.scrollY + window.innerHeight >= after - 2;
                    if (atBottom && after <= before) break;
                }

                // Let the final viewport finish loading. Keep this scroll
                // position: some animation libraries reverse elements when
                // returning to the top, which would make a full-page capture
                // blank again.
                await pause(350);
                root.style.scrollBehavior = originalBehavior;
            }"""
        )

    async def analyze(self, url: str) -> BrowserSession:
        """
        Analyze webpage using Playwright.
        """

        session = BrowserSession()

        session.original_url = url

        # --------------------------------------------------
        # Performance Timer
        # --------------------------------------------------

        start_time = time.perf_counter()

        try:

            # --------------------------------------------------
            # Start Browser
            # --------------------------------------------------

            await self.manager.start()

            page = self.manager.page

            if page is None:
                raise RuntimeError(
                    "Playwright page was not created."
                )

            # --------------------------------------------------
            # Redirect Chain
            # --------------------------------------------------

            session.redirect_chain = []


            async def frame_navigation(frame):

                try:

                    if frame == page.main_frame:

                        current = frame.url

                        if (
                            current
                            and current not in session.redirect_chain
                        ):

                            session.redirect_chain.append(current)

                except Exception:
                    pass


            page.on(
                "framenavigated",
                frame_navigation,
            )

            # --------------------------------------------------
            # Downloads
            # --------------------------------------------------

            async def download_listener(
                download: Download
            ):

                try:

                    session.downloads.append({

                        "suggested_filename":
                            download.suggested_filename,

                        "url":
                            download.url,

                    })

                except Exception:
                    pass


            page.on(
                "download",
                download_listener,
            )

            # --------------------------------------------------
            # Popups
            # --------------------------------------------------

            async def popup_listener(
                popup
            ):

                try:

                    await popup.wait_for_load_state()

                    session.popups.append({

                        "url": popup.url,

                        "title": await popup.title(),

                    })

                except Exception:
                    pass


            page.on(
                "popup",
                popup_listener,
            )

            # --------------------------------------------------
            # Console Events
            # --------------------------------------------------

            async def console_listener(
                message: ConsoleMessage
            ):

                session.console_logs.append({
                    "type": message.type,
                    "text": message.text,
                    "location": message.location,
                })


            page.on(
                "console",
                console_listener,
            )

            # --------------------------------------------------
            # JavaScript Errors
            # --------------------------------------------------

            async def page_error_listener(
                error
            ):

                session.javascript_errors.append(
                    str(error)
                )


            page.on(
                "pageerror",
                page_error_listener,
            )

            # --------------------------------------------------
            # Network Requests
            # --------------------------------------------------

            async def request_listener(
                request: Request
            ):

                session.network_requests.append({

                    "url": request.url,

                    "method": request.method,

                    "resource_type": request.resource_type,

                    "headers": await request.all_headers(),

                })


            page.on(
                "request",
                request_listener,
            )

            # --------------------------------------------------
            # Network Responses
            # --------------------------------------------------

            async def response_listener(
                response: Response
            ):

                try:

                    session.network_responses.append({

                        "url": response.url,

                        "status": response.status,

                        "status_text": response.status_text,

                        "headers": await response.all_headers(),

                        "content_type":
                            response.headers.get(
                                "content-type"
                            ),

                    })

                except Exception:
                    pass


            page.on(
                "response",
                response_listener,
            )

            # --------------------------------------------------
            # Failed Requests
            # --------------------------------------------------

            async def failed_request_listener(
                request: Request
            ):

                try:

                    failure = request.failure

                    session.network_requests.append({

                        "url": request.url,

                        "method": request.method,

                        "resource_type": request.resource_type,

                        "failure":
                            failure["errorText"]
                            if failure else None,

                    })

                except Exception:
                    pass


            page.on(
                "requestfailed",
                failed_request_listener,
            )

            # --------------------------------------------------
            # Open URL
            # --------------------------------------------------

            response = await self.manager.open(url)

            # --------------------------------------------------
            # Wait for DOM Ready
            # --------------------------------------------------

            try:
                await page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=10000,
                )
            except Exception:
                pass

            # --------------------------------------------------
            # Wait for Network Idle
            # --------------------------------------------------

            try:
                await page.wait_for_load_state(
                    "networkidle",
                    timeout=15000,
                )
            except Exception:
                pass

            session.browser = self.manager.browser
            session.context = self.manager.context
            session.page = page

            # --------------------------------------------------
            # Response Metadata
            # --------------------------------------------------

            if response is not None:

                session.status_code = response.status

                session.headers = dict(
                    response.headers
                )

                session.content_type = (
                    response.headers.get(
                        "content-type"
                    )
                )

            # --------------------------------------------------
            # Final URL
            # --------------------------------------------------

            session.final_url = page.url

            # --------------------------------------------------
            # Page Title
            # --------------------------------------------------

            session.title = await page.title()

            # --------------------------------------------------
            # Rendered HTML
            # --------------------------------------------------

            session.html = await page.content()

            # --------------------------------------------------
            # Cookies
            # --------------------------------------------------

            if self.manager.context:

                session.cookies = (
                    await self.manager.context.cookies()
                )

            # --------------------------------------------------
            # Screenshot Directory
            # --------------------------------------------------

            screenshot_dir = (
                Path("reports")
                / "screenshots"
            )

            screenshot_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            # Every analysis needs its own capture.  A shared `latest.png`
            # makes result pages race with later scans and can show the wrong
            # site preview.
            screenshot_name = f"{uuid4().hex}.png"
            screenshot_file = screenshot_dir / screenshot_name

            # Trigger lazy-loaded and scroll-animated content before a
            # full-page capture, otherwise the preview can contain large
            # empty sections for sites that animate on scroll.
            await self._activate_scroll_content(page)

            # Save screenshot to disk

            session.screenshot_bytes = await page.screenshot(
                full_page=True
            )

            with screenshot_file.open("wb") as f:
                f.write(session.screenshot_bytes)

            # This is relative to the /reports static-files mount, rather
            # than an OS-specific path that the browser cannot display.
            session.screenshot_path = f"screenshots/{screenshot_name}"

        except Exception as error:
            # Return a partial session so the rest of the pipeline can report
            # the unavailable source instead of losing its other evidence.
            session.error = f"{type(error).__name__}: {error}"

        # --------------------------------------------------
        # Load Time
        # --------------------------------------------------

        session.load_time_ms = round(

            (
                time.perf_counter()
                - start_time
            ) * 1000,

            2,
        )

        return session

    async def close(self):
        """
        Close browser resources.
        """

        await self.manager.close()
