"""
HTTP Cookie Security Analyzer

Responsibilities
----------------
✓ Detect all cookies
✓ Secure cookies
✓ HttpOnly cookies
✓ SameSite cookies
✓ Session cookies
✓ Persistent cookies
✓ Expired cookies
✓ Cookie Prefixes
✓ Cookie Statistics
✓ Cookie Security Score

Future
------
✓ Third-party Cookies
✓ Cookie Entropy
✓ Cookie Risk Score
✓ Supercookies
✓ Cookie Correlation
"""

from datetime import datetime, timezone
from typing import Any, Dict

from app.models.browser_session import BrowserSession


class CookiesAnalyzer:
    """
    Analyze cookies received from the website.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> Dict[str, Any]:

        cookies = browser_session.cookies or []

        result = {

            # ---------------------------------
            # General
            # ---------------------------------

            "cookies_available": bool(cookies),

            "total_cookies": 0,

            # ---------------------------------
            # Security
            # ---------------------------------

            "secure_cookies": 0,

            "httponly_cookies": 0,

            "missing_secure": 0,

            "missing_httponly": 0,

            # ---------------------------------
            # SameSite
            # ---------------------------------

            "samesite_strict": 0,

            "samesite_lax": 0,

            "samesite_none": 0,

            "missing_samesite": 0,

            # ---------------------------------
            # Lifetime
            # ---------------------------------

            "session_cookies": 0,

            "persistent_cookies": 0,

            "expired_cookies": 0,

            # ---------------------------------
            # Prefixes
            # ---------------------------------

            "host_prefix_cookies": 0,

            "secure_prefix_cookies": 0,

            # ---------------------------------
            # Analysis
            # ---------------------------------

            "recommendations": [],

            "cookie_score": 100,

            "grade": "A",

            # ---------------------------------
            # Details
            # ---------------------------------

            "cookies": [],

            # ---------------------------------
            # Future
            # ---------------------------------

            "error": None,
            
            # ---------------------------------
            # Summary
            # ---------------------------------

            "security_summary": {},

            "security_level": None,

            "passes_basic_security": False,

            "summary": None,
        }

        try:

            result["total_cookies"] = len(cookies)
            
            # ---------------------------------
            # Analyze Cookies
            # ---------------------------------

            for cookie in cookies:

                name = cookie.get("name") or ""

                domain = cookie.get("domain")

                path = cookie.get("path")

                secure = bool(
                    cookie.get("secure")
                )

                http_only = bool(
                    cookie.get("httpOnly")
                )

                same_site = (
                    cookie.get("sameSite") or ""
                ).lower()

                expires = cookie.get("expires")

                # -----------------------------
                # Secure
                # -----------------------------

                if secure:

                    result["secure_cookies"] += 1

                else:

                    result["missing_secure"] += 1

                    result["cookie_score"] -= 3

                    result["recommendations"].append(
                        f"Cookie '{name}' should use the Secure attribute."
                    )

                # -----------------------------
                # HttpOnly
                # -----------------------------

                if http_only:

                    result["httponly_cookies"] += 1

                else:

                    result["missing_httponly"] += 1

                    result["cookie_score"] -= 3

                    result["recommendations"].append(
                        f"Cookie '{name}' should use the HttpOnly attribute."
                    )

                # -----------------------------
                # SameSite
                # -----------------------------

                if same_site == "strict":

                    result["samesite_strict"] += 1

                elif same_site == "lax":

                    result["samesite_lax"] += 1

                elif same_site == "none":

                    result["samesite_none"] += 1

                    if not secure:

                        result["cookie_score"] -= 3

                        result["recommendations"].append(
                            f"Cookie '{name}' uses SameSite=None without Secure."
                        )

                else:

                    result["missing_samesite"] += 1

                    result["cookie_score"] -= 2

                    result["recommendations"].append(
                        f"Cookie '{name}' should define SameSite."
                    )
                    
                # -----------------------------
                # Session / Persistent Cookie
                # -----------------------------

                if expires in (
                    None,
                    "",
                    -1,
                ):

                    result["session_cookies"] += 1

                    persistent = False

                else:

                    result["persistent_cookies"] += 1

                    persistent = True

                # -----------------------------
                # Expiration Check
                # -----------------------------

                expired = False

                if persistent:

                    try:

                        expiry_time = datetime.fromtimestamp(
                            float(expires),
                            tz=timezone.utc,
                        )

                        if expiry_time < datetime.now(
                            timezone.utc
                        ):

                            expired = True

                            result["expired_cookies"] += 1

                            result["cookie_score"] -= 2

                            result["recommendations"].append(
                                f"Cookie '{name}' is expired."
                            )

                    except Exception:

                        pass

                # -----------------------------
                # Cookie Prefix Validation
                # -----------------------------

                if name.startswith("__Host-"):

                    result["host_prefix_cookies"] += 1

                    if (
                        not secure
                        or domain
                        or path != "/"
                    ):

                        result["cookie_score"] -= 5

                        result["recommendations"].append(
                            f"Cookie '{name}' violates __Host- prefix requirements."
                        )

                if name.startswith("__Secure-"):

                    result["secure_prefix_cookies"] += 1

                    if not secure:

                        result["cookie_score"] -= 5

                        result["recommendations"].append(
                            f"Cookie '{name}' violates __Secure- prefix requirements."
                        )

                # -----------------------------
                # Cookie Details
                # -----------------------------

                result["cookies"].append(
                    {
                        "name": name,
                        "domain": domain,
                        "path": path,
                        "secure": secure,
                        "http_only": http_only,
                        "same_site": same_site or None,
                        "expires": expires,
                        "persistent": persistent,
                        "expired": expired,
                        "host_prefix": name.startswith("__Host-"),
                        "secure_prefix": name.startswith("__Secure-"),
                    }
                )
                
            # ---------------------------------
            # Final Cookie Score
            # ---------------------------------

            result["cookie_score"] = max(
                0,
                min(100, result["cookie_score"])
            )

            # ---------------------------------
            # Grade Calculation
            # ---------------------------------

            score = result["cookie_score"]

            if score >= 95:

                result["grade"] = "A+"

            elif score >= 90:

                result["grade"] = "A"

            elif score >= 80:

                result["grade"] = "B"

            elif score >= 70:

                result["grade"] = "C"

            elif score >= 60:

                result["grade"] = "D"

            else:

                result["grade"] = "F"

            # ---------------------------------
            # Security Summary
            # ---------------------------------

            result["security_summary"] = {

                "secure_percentage": round(

                    (
                        result["secure_cookies"]
                        / result["total_cookies"]
                    ) * 100,

                    2,

                ) if result["total_cookies"] else 0,

                "httponly_percentage": round(

                    (
                        result["httponly_cookies"]
                        / result["total_cookies"]
                    ) * 100,

                    2,

                ) if result["total_cookies"] else 0,

                "expired_percentage": round(

                    (
                        result["expired_cookies"]
                        / result["total_cookies"]
                    ) * 100,

                    2,

                ) if result["total_cookies"] else 0,

            }

            # ---------------------------------
            # Remove Duplicates
            # ---------------------------------

            result["recommendations"] = sorted(
                set(result["recommendations"])
            )

            # ---------------------------------
            # Sort Cookies
            # ---------------------------------

            result["cookies"] = sorted(

                result["cookies"],

                key=lambda cookie: (

                    not cookie["secure"],

                    not cookie["http_only"],

                    cookie["expired"],

                    cookie["name"].lower(),

                )

            )
            
            # ---------------------------------
            # Overall Security Level
            # ---------------------------------

            if result["grade"] in (
                "A+",
                "A",
            ):

                result["security_level"] = "Excellent"

            elif result["grade"] == "B":

                result["security_level"] = "Good"

            elif result["grade"] == "C":

                result["security_level"] = "Fair"

            elif result["grade"] == "D":

                result["security_level"] = "Poor"

            else:

                result["security_level"] = "Critical"

            # ---------------------------------
            # Pass / Fail
            # ---------------------------------

            result["passes_basic_security"] = (

                result["cookie_score"] >= 80

            )

            # ---------------------------------
            # Summary
            # ---------------------------------

            if result["total_cookies"] == 0:

                result["summary"] = (

                    "No cookies were set by the website."

                )

            elif result["cookie_score"] >= 90:

                result["summary"] = (

                    "Cookie security configuration is excellent."

                )

            elif result["cookie_score"] >= 80:

                result["summary"] = (

                    "Cookie security configuration is good with minor improvements recommended."

                )

            elif result["cookie_score"] >= 60:

                result["summary"] = (

                    "Cookie security configuration has several weaknesses."

                )

            else:

                result["summary"] = (

                    "Cookie security configuration is poor and requires immediate attention."

                )

        except Exception as e:

            result["error"] = str(e)

        return result