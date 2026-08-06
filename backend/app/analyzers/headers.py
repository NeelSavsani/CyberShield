"""
HTTP Security Headers Analyzer

Responsibilities
----------------
✓ Detect security headers
✓ Detect missing security headers
✓ Validate HSTS
✓ Validate CSP
✓ Validate X-Frame-Options
✓ Validate X-Content-Type-Options
✓ Validate Referrer-Policy
✓ Validate Permissions-Policy
✓ Validate COOP
✓ Validate COEP
✓ Validate CORP
✓ Detect CORS configuration
✓ Detect information leakage
✓ Calculate header security score

Future
------
✓ CSP Deep Inspection
✓ HSTS Preload Validation
✓ Header Recommendations
✓ Cookie Correlation
"""

from typing import Any, Dict

from app.models.browser_session import BrowserSession


class HeadersAnalyzer:
    """
    Analyze HTTP response security headers.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> Dict[str, Any]:

        headers = browser_session.response_headers or {}

        result = {
            # ---------------------------------
            # General
            # ---------------------------------
            "headers_available": bool(headers),
            # ---------------------------------
            # Security Headers
            # ---------------------------------
            "strict_transport_security": None,
            "content_security_policy": None,
            "x_frame_options": None,
            "x_content_type_options": None,
            "referrer_policy": None,
            "permissions_policy": None,
            "cross_origin_embedder_policy": None,
            "cross_origin_opener_policy": None,
            "cross_origin_resource_policy": None,
            # ---------------------------------
            # CORS
            # ---------------------------------
            "access_control_allow_origin": None,
            # ---------------------------------
            # Information Leakage
            # ---------------------------------
            "server": None,
            "x_powered_by": None,
            "x_aspnet_version": None,
            "x_generator": None,
            # ---------------------------------
            # Analysis
            # ---------------------------------
            "present_headers": [],
            "missing_headers": [],
            "misconfigured_headers": [],
            "recommendations": [],
            # ---------------------------------
            # Scoring
            # ---------------------------------
            "header_score": 100,
            "grade": "A",
            # ---------------------------------
            # Future
            # ---------------------------------
            "error": None,
        }

        try:
            # Normalize headers first
            normalized = {key.lower(): value for key, value in headers.items()}

            # Read security headers
            result["strict_transport_security"] = normalized.get(
                "strict-transport-security"
            )
            result["content_security_policy"] = normalized.get(
                "content-security-policy"
            )
            result["x_frame_options"] = normalized.get("x-frame-options")
            result["x_content_type_options"] = normalized.get("x-content-type-options")
            result["referrer_policy"] = normalized.get("referrer-policy")
            result["permissions_policy"] = normalized.get("permissions-policy")
            result["cross_origin_embedder_policy"] = normalized.get(
                "cross-origin-embedder-policy"
            )
            result["cross_origin_opener_policy"] = normalized.get(
                "cross-origin-opener-policy"
            )
            result["cross_origin_resource_policy"] = normalized.get(
                "cross-origin-resource-policy"
            )

            # Read CORS and information-leakage headers
            result["access_control_allow_origin"] = normalized.get(
                "access-control-allow-origin"
            )
            result["server"] = normalized.get("server")
            result["x_powered_by"] = normalized.get("x-powered-by")
            result["x_aspnet_version"] = normalized.get("x-aspnet-version")
            result["x_generator"] = normalized.get("x-generator")

            # Required security headers
            required_headers = {
                "Strict-Transport-Security": result["strict_transport_security"],
                "Content-Security-Policy": result["content_security_policy"],
                "X-Frame-Options": result["x_frame_options"],
                "X-Content-Type-Options": result["x_content_type_options"],
                "Referrer-Policy": result["referrer_policy"],
                "Permissions-Policy": result["permissions_policy"],
                "Cross-Origin-Embedder-Policy": result["cross_origin_embedder_policy"],
                "Cross-Origin-Opener-Policy": result["cross_origin_opener_policy"],
                "Cross-Origin-Resource-Policy": result["cross_origin_resource_policy"],
            }

            # Present / missing detection
            for header_name, value in required_headers.items():
                if value:
                    result["present_headers"].append(header_name)
                else:
                    result["missing_headers"].append(header_name)
                    result["recommendations"].append(f"Add {header_name} header.")
                    result["header_score"] -= 5

            # HSTS validation
            hsts = result["strict_transport_security"]
            if hsts:
                lower = hsts.lower()

                if "max-age=" not in lower:
                    result["misconfigured_headers"].append("Strict-Transport-Security")
                    result["recommendations"].append("Configure HSTS with max-age.")
                    result["header_score"] -= 5

                elif "max-age=0" in lower:
                    result["misconfigured_headers"].append("Strict-Transport-Security")
                    result["recommendations"].append("Avoid max-age=0 in HSTS.")
                    result["header_score"] -= 5

            # X-Frame-Options validation
            xfo = result["x_frame_options"]
            if xfo and xfo.upper() not in ("DENY", "SAMEORIGIN"):
                result["misconfigured_headers"].append("X-Frame-Options")
                result["recommendations"].append("Use DENY or SAMEORIGIN.")
                result["header_score"] -= 5

            # X-Content-Type-Options validation
            xcto = result["x_content_type_options"]
            if xcto and xcto.lower() != "nosniff":
                result["misconfigured_headers"].append("X-Content-Type-Options")
                result["recommendations"].append(
                    "Set X-Content-Type-Options to nosniff."
                )
                result["header_score"] -= 5

            # Referrer-Policy validation
            secure_referrer = {
                "strict-origin",
                "strict-origin-when-cross-origin",
                "same-origin",
                "no-referrer",
            }

            rp = result["referrer_policy"]
            if rp and rp.lower() not in secure_referrer:
                result["misconfigured_headers"].append("Referrer-Policy")
                result["recommendations"].append("Use a stricter Referrer-Policy.")
                result["header_score"] -= 3

            # ---------------------------------
            # Content Security Policy (CSP)
            # ---------------------------------

            csp = result["content_security_policy"]

            if csp:

                lower = csp.lower()

                if "*" in lower:

                    result["misconfigured_headers"].append("Content-Security-Policy")

                    result["recommendations"].append(
                        "Avoid wildcard (*) in Content-Security-Policy."
                    )

                    result["header_score"] -= 5

                if "'unsafe-inline'" in lower:

                    result["misconfigured_headers"].append("Content-Security-Policy")

                    result["recommendations"].append(
                        "Avoid 'unsafe-inline' in Content-Security-Policy."
                    )

                    result["header_score"] -= 5

                if "'unsafe-eval'" in lower:

                    result["misconfigured_headers"].append("Content-Security-Policy")

                    result["recommendations"].append(
                        "Avoid 'unsafe-eval' in Content-Security-Policy."
                    )

                    result["header_score"] -= 5

            # ---------------------------------
            # Permissions Policy
            # ---------------------------------

            permissions = result["permissions_policy"]

            if permissions:

                lower = permissions.lower()

                dangerous_features = (
                    "camera=*",
                    "microphone=*",
                    "geolocation=*",
                )

                if any(feature in lower for feature in dangerous_features):

                    result["misconfigured_headers"].append("Permissions-Policy")

                    result["recommendations"].append(
                        "Restrict powerful browser features in Permissions-Policy."
                    )

                    result["header_score"] -= 3

            # ---------------------------------
            # COOP Validation
            # ---------------------------------

            coop = result["cross_origin_opener_policy"]

            if coop:

                if coop.lower() not in (
                    "same-origin",
                    "same-origin-allow-popups",
                ):

                    result["misconfigured_headers"].append("Cross-Origin-Opener-Policy")

                    result["recommendations"].append(
                        "Use a stronger Cross-Origin-Opener-Policy."
                    )

                    result["header_score"] -= 3

            # ---------------------------------
            # COEP Validation
            # ---------------------------------

            coep = result["cross_origin_embedder_policy"]

            if coep:

                if coep.lower() != "require-corp":

                    result["misconfigured_headers"].append(
                        "Cross-Origin-Embedder-Policy"
                    )

                    result["recommendations"].append(
                        "Set Cross-Origin-Embedder-Policy to require-corp."
                    )

                    result["header_score"] -= 3

            # ---------------------------------
            # CORP Validation
            # ---------------------------------

            corp = result["cross_origin_resource_policy"]

            if corp:

                if corp.lower() not in (
                    "same-origin",
                    "same-site",
                ):

                    result["misconfigured_headers"].append(
                        "Cross-Origin-Resource-Policy"
                    )

                    result["recommendations"].append(
                        "Use same-origin or same-site for Cross-Origin-Resource-Policy."
                    )

                    result["header_score"] -= 3

            # ---------------------------------
            # CORS Validation
            # ---------------------------------

            cors = result["access_control_allow_origin"]

            if cors:

                if cors.strip() == "*":

                    result["misconfigured_headers"].append(
                        "Access-Control-Allow-Origin"
                    )

                    result["recommendations"].append(
                        "Avoid Access-Control-Allow-Origin: * for sensitive applications."
                    )

                    result["header_score"] -= 5
                    
            # ---------------------------------
            # Information Leakage Detection
            # ---------------------------------

            if result["server"]:

                result["recommendations"].append(
                    "Hide or minimize the Server header."
                )

                result["header_score"] -= 2

            if result["x_powered_by"]:

                result["recommendations"].append(
                    "Remove X-Powered-By header."
                )

                result["header_score"] -= 2

            if result["x_aspnet_version"]:

                result["recommendations"].append(
                    "Remove X-AspNet-Version header."
                )

                result["header_score"] -= 2

            if result["x_generator"]:

                result["recommendations"].append(
                    "Hide X-Generator header."
                )

                result["header_score"] -= 2

            # ---------------------------------
            # Final Score
            # ---------------------------------

            result["header_score"] = max(
                0,
                min(100, result["header_score"])
            )

            # ---------------------------------
            # Grade Calculation
            # ---------------------------------

            score = result["header_score"]

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

        except Exception as e:
            result["error"] = str(e)

        result["header_score"] = max(
            0,
            min(100, result["header_score"])
        )
        
        # Remove duplicates

        result["present_headers"] = sorted(
            set(result["present_headers"])
        )

        result["missing_headers"] = sorted(
            set(result["missing_headers"])
        )

        result["misconfigured_headers"] = sorted(
            set(result["misconfigured_headers"])
        )

        result["recommendations"] = sorted(
            set(result["recommendations"])
        )

        return result