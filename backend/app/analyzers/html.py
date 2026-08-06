"""
CyberShield HTML Analyzer

Phase 1
--------
Responsibilities

✓ Parse rendered HTML
✓ Extract page metadata
✓ Extract title
✓ Extract meta tags
✓ Count links
✓ Count images
✓ Count scripts
✓ Count forms

Future Phases

✓ Hidden Elements
✓ Hidden Iframes
✓ Login Forms
✓ Password Fields
✓ External Resources
✓ Meta Refresh
✓ Favicon
✓ Suspicious Keywords
"""
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.models.browser_session import BrowserSession


class HTMLAnalyzer:
    """
   Analyzes rendered HTML collected from BrowserAnalyzer.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> dict:

        html = browser_session.html

        if not html:

            return {
                "html_available": False,
                "error": "No HTML available."
            }

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        result = {

            # -----------------------------
            # General
            # -----------------------------

            "html_available": True,

            "html_size": len(html),

            # -----------------------------
            # Title
            # -----------------------------

            "title": browser_session.title,

            # -----------------------------
            # Meta
            # -----------------------------

            "meta_tags": [],

            # -----------------------------
            # Counts
            # -----------------------------

            "link_count": 0,

            "image_count": 0,

            "script_count": 0,

            "form_count": 0,

            # -----------------------------
            # Form Analysis
            # -----------------------------

            "login_forms": 0,

            "password_fields": 0,

            "email_fields": 0,

            "hidden_inputs": 0,

            "credit_card_fields": 0,

            "otp_fields": 0,

            "external_form_actions": [],

            "suspicious_forms": [],

            # -----------------------------
            # HTML Security
            # -----------------------------

            "hidden_iframes": [],

            "hidden_elements": 0,

            "meta_refresh": None,

            "external_scripts": [],

            "external_stylesheets": [],

            "inline_script_count": 0,

            "favicon": None,

            "mixed_content": [],

            # -----------------------------
            # Future
            # -----------------------------

            "error": None,

        }

        try:

            # --------------------------------
            # Meta Tags
            # --------------------------------

            meta_tags = soup.find_all("meta")

            for meta in meta_tags:

                result["meta_tags"].append({

                    "name":
                        meta.get("name"),

                    "property":
                        meta.get("property"),

                    "http_equiv":
                        meta.get("http-equiv"),

                    "content":
                        meta.get("content"),

                })

            # --------------------------------
            # Basic Counts
            # --------------------------------

            result["link_count"] = len(

                soup.find_all("a")

            )

            result["image_count"] = len(

                soup.find_all("img")

            )

            result["script_count"] = len(

                soup.find_all("script")

            )

            result["form_count"] = len(

                soup.find_all("form")

            )

            # --------------------------------
            # Form Analysis
            # --------------------------------

            forms = soup.find_all("form")

            card_keywords = [
                "credit",
                "card",
                "cvv",
                "expiry",
                "expiration",
            ]

            otp_keywords = [
                "otp",
                "code",
                "verification",
                "2fa",
                "pin",
            ]

            for form in forms:

                password_count = 0

                action = form.get("action", "")

                action_host = ""

                method = form.get(
                    "method",
                    "GET"
                ).upper()

                inputs = form.find_all("input")

                for inp in inputs:

                    input_type = (
                        inp.get("type", "")
                        .lower()
                    )

                    input_name = (
                        inp.get("name", "")
                        .lower()
                    )

                    input_id = (
                        inp.get("id", "")
                        .lower()
                    )

                    placeholder = (
                        inp.get(
                            "placeholder",
                            ""
                        ).lower()
                    )

                    searchable = " ".join([

                        input_type,

                        input_name,

                        input_id,

                        placeholder,

                    ])

                    # --------------------------
                    # Password
                    # --------------------------

                    if input_type == "password":

                        password_count += 1

                        result["password_fields"] += 1

                    # --------------------------
                    # Email
                    # --------------------------

                    if (
                        input_type == "email"
                        or "email" in searchable
                    ):

                        result["email_fields"] += 1

                    # --------------------------
                    # Hidden
                    # --------------------------

                    if input_type == "hidden":

                        result["hidden_inputs"] += 1

                    # --------------------------
                    # Credit Card
                    # --------------------------

                    if any(
                        word in searchable
                        for word in card_keywords
                    ):

                        result["credit_card_fields"] += 1

                    # --------------------------
                    # OTP
                    # --------------------------

                    if any(
                        word in searchable
                        for word in otp_keywords
                    ):

                        result["otp_fields"] += 1

                # --------------------------------
                # Login Form Detection
                # --------------------------------

                if password_count > 0:

                    result["login_forms"] += 1

                # --------------------------------
                # External Action
                # --------------------------------

                if action.startswith("http"):

                    current_host = urlparse(browser_session.final_url).netloc
                    action_host = urlparse(action).netloc

                    if action_host and action_host != current_host:

                        result[
                            "external_form_actions"
                        ].append(action)

                # --------------------------------
                # Suspicious Form
                # --------------------------------

                if (

                    password_count > 0

                    and action == ""

                ):

                    result[
                        "suspicious_forms"
                    ].append({

                        "reason":
                            "Password form without action",

                        "method":
                            method,

                    })

                elif (

                    password_count > 0

                    and action.startswith("http")

                ):


                    if action_host and action_host != current_host:

                        result["suspicious_forms"].append({

                            "reason":
                                "Password submitted to external domain",

                            "action":
                                action,

                            "method":
                                method,

                        })

            # --------------------------------
            # Hidden Iframes
            # --------------------------------

            for iframe in soup.find_all("iframe"):

                style = (
                    iframe.get("style", "")
                    .lower()
                )

                hidden = (

                    "display:none" in style

                    or "visibility:hidden" in style

                    or iframe.get("hidden") is not None

                    or iframe.get("width") == "0"

                    or iframe.get("height") == "0"

                )

                if hidden:

                    result["hidden_iframes"].append({

                        "src":
                            iframe.get("src"),

                        "style":
                            style,

                    })

            # --------------------------------
            # Hidden Elements
            # --------------------------------

            hidden_count = 0

            for tag in soup.find_all(True):

                style = (
                    tag.get("style", "")
                    .lower()
                )

                if (

                    "display:none" in style

                    or "visibility:hidden" in style

                    or tag.get("hidden") is not None

                ):

                    hidden_count += 1

            result["hidden_elements"] = hidden_count

            # --------------------------------
            # Meta Refresh
            # --------------------------------

            refresh = soup.find(

                "meta",

                attrs={
                    "http-equiv":
                    lambda x:
                    x and x.lower() == "refresh"
                }

            )

            if refresh:

                result["meta_refresh"] = {

                    "content":
                        refresh.get("content"),

                }

            # --------------------------------
            # External Scripts
            # --------------------------------

            current_host = urlparse(
                browser_session.final_url
            ).netloc

            for script in soup.find_all("script"):

                src = script.get("src")

                if not src:

                    result["inline_script_count"] += 1

                    continue

                if src.startswith("http"):

                    host = urlparse(src).netloc

                    if host != current_host:

                        result[
                            "external_scripts"
                        ].append(src)

            # --------------------------------
            # External Stylesheets
            # --------------------------------

            for css in soup.find_all(

                "link",

                rel=lambda x:
                x and "stylesheet" in x

            ):

                href = css.get("href")

                if not href:

                    continue

                if href.startswith("http"):

                    host = urlparse(href).netloc

                    if host != current_host:

                        result[
                            "external_stylesheets"
                        ].append(href)

            # --------------------------------
            # Favicon
            # --------------------------------

            icon = soup.find(

                "link",

                rel=lambda x:
                x and "icon" in x

            )

            if icon:

                result["favicon"] = icon.get(
                    "href"
                )

            # --------------------------------
            # Mixed Content
            # --------------------------------

            if browser_session.final_url.startswith(
                "https://"
            ):

                for tag in soup.find_all(

                    ["img", "script", "iframe"]

                ):

                    src = tag.get("src")

                    if (

                        src

                        and src.startswith(
                            "http://"
                        )

                    ):

                        result[
                            "mixed_content"
                        ].append(src)            

        except Exception as e:

            result["error"] = str(e)

        return result
