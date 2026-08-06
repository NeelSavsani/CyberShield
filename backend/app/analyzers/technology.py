"""
Technology Analyzer

Responsibilities
----------------
✓ Detect Web Server
✓ Detect Backend Technologies
✓ Detect Frontend Frameworks
✓ Detect CMS
✓ Detect JavaScript Libraries
✓ Detect CSS Frameworks
✓ Detect CDN
✓ Detect Analytics Services

Future Phases
-------------
✓ WAF Detection
✓ Security Headers Correlation
✓ Version Detection
✓ Fingerprint Confidence
✓ Technology Risk Score
"""

import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from app.models.browser_session import BrowserSession


class TechnologyAnalyzer:
    """
    Detect technologies used by a website.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> Dict[str, Any]:

        html = browser_session.html

        headers = browser_session.response_headers or {}

        if not html:

            return {
                "technology_available": False,
                "error": "No rendered HTML available.",
            }

        soup = BeautifulSoup(html, "lxml")

        result = {
            
            # ---------------------------------
            # Technology Assessment
            # ---------------------------------

            "versions": {},

            "technology_risk_score": 0,

            "technology_risk": "Unknown",

            "recommendations": [],

            "summary": {},
            
            # ---------------------------------
            # Fingerprint
            # ---------------------------------

            "fingerprint_confidence": 0,

            # ---------------------------------
            # General
            # ---------------------------------

            "technology_available": True,

            # ---------------------------------
            # Web Server
            # ---------------------------------

            "server": None,

            # ---------------------------------
            # Backend
            # ---------------------------------

            "backend": [],

            # ---------------------------------
            # Frontend
            # ---------------------------------

            "frontend": [],

            # ---------------------------------
            # CMS
            # ---------------------------------

            "cms": [],

            # ---------------------------------
            # JavaScript Libraries
            # ---------------------------------

            "javascript_libraries": [],

            # ---------------------------------
            # CSS Frameworks
            # ---------------------------------

            "css_frameworks": [],

            # ---------------------------------
            # Analytics
            # ---------------------------------

            "analytics": [],

            # ---------------------------------
            # CDN
            # ---------------------------------

            "cdn": [],

            # ---------------------------------
            # Security
            # ---------------------------------

            "security": [],

            # ---------------------------------
            # Raw Evidence
            # ---------------------------------

            "meta_generator": None,

            "generator_tag": None,

            "script_sources": [],

            "stylesheet_sources": [],

            # ---------------------------------
            # Future
            # ---------------------------------

            "error": None,
        }

        try:

            # ---------------------------------
            # Server Header
            # ---------------------------------

            server = headers.get("server")

            if server:

                result["server"] = server

            # ---------------------------------
            # X-Powered-By
            # ---------------------------------

            powered = headers.get("x-powered-by")

            if powered:

                result["backend"].append(powered)

            # ---------------------------------
            # Meta Generator
            # ---------------------------------

            generator = soup.find(
                "meta",
                attrs={"name": re.compile("^generator$", re.I)},
            )

            if generator:

                content = generator.get(
                    "content",
                    ""
                ).strip()

                result["generator_tag"] = content

                result["meta_generator"] = content

            # ---------------------------------
            # Script Sources
            # ---------------------------------

            for script in soup.find_all("script"):

                src = script.get("src")

                if src:

                    result["script_sources"].append(src)

            # ---------------------------------
            # Stylesheets
            # ---------------------------------

            for css in soup.find_all(
                "link",
                rel=lambda x: x and "stylesheet" in x,
            ):

                href = css.get("href")

                if href:

                    result["stylesheet_sources"].append(href)
            
            # ---------------------------------
            # Technology Detection
            # ---------------------------------

            server_lower = (result["server"] or "").lower()

            backend_text = " ".join(result["backend"]).lower()

            generator = (
                result["meta_generator"] or ""
            ).lower()

            scripts = " ".join(
                result["script_sources"]
            ).lower()

            styles = " ".join(
                result["stylesheet_sources"]
            ).lower()

            html_lower = html.lower()

            # ---------------------------------
            # Web Server Detection
            # ---------------------------------

            servers = {
                "apache": "Apache",
                "nginx": "Nginx",
                "iis": "Microsoft IIS",
                "litespeed": "LiteSpeed",
                "openresty": "OpenResty",
                "caddy": "Caddy",
                "cloudflare": "Cloudflare",
            }

            for keyword, name in servers.items():

                if keyword in server_lower:

                    result["server"] = name

                    break

            # ---------------------------------
            # Backend Technologies
            # ---------------------------------

            backend_patterns = {

                "PHP": [
                    "php",
                ],

                "ASP.NET": [
                    "asp.net",
                    "aspnet",
                ],

                "Node.js": [
                    "node",
                    "express",
                ],

                "Python": [
                    "python",
                    "gunicorn",
                    "uwsgi",
                ],

                "Java": [
                    "tomcat",
                    "jetty",
                    "servlet",
                ],

                "Go": [
                    "golang",
                ],

            }

            combined_backend = (
                backend_text
                + " "
                + server_lower
                + " "
                + generator
            )

            for tech, patterns in backend_patterns.items():

                if any(
                    pattern in combined_backend
                    for pattern in patterns
                ):

                    result["backend"].append(
                        tech
                    )

            # ---------------------------------
            # Framework Detection
            # ---------------------------------

            framework_patterns = {

                "Laravel": [
                    "laravel",
                ],

                "Django": [
                    "django",
                ],

                "Flask": [
                    "flask",
                ],

                "Express": [
                    "express",
                ],

                "Spring Boot": [
                    "spring",
                ],

                "ASP.NET MVC": [
                    "asp.net",
                ],

                "Ruby on Rails": [
                    "rails",
                ],

            }

            for framework, patterns in framework_patterns.items():

                if any(
                    pattern in combined_backend
                    for pattern in patterns
                ):

                    result["backend"].append(
                        framework
                    )

            # ---------------------------------
            # Frontend Framework Detection
            # ---------------------------------

            frontend_patterns = {

                "React": [
                    "react",
                    "_reactroot",
                    "react-dom",
                ],

                "Next.js": [
                    "__next",
                    "_next",
                ],

                "Vue.js": [
                    "vue",
                    "__vue__",
                ],

                "Nuxt.js": [
                    "_nuxt",
                ],

                "Angular": [
                    "angular",
                    "ng-version",
                ],

                "Svelte": [
                    "svelte",
                ],

            }

            combined_frontend = (
                scripts
                + " "
                + html_lower
            )

            for framework, patterns in frontend_patterns.items():

                if any(
                    pattern in combined_frontend
                    for pattern in patterns
                ):

                    result["frontend"].append(
                        framework
                    )
                    
            # ---------------------------------
            # CMS Detection
            # ---------------------------------

            cms_patterns = {

                "WordPress": [
                    "wp-content",
                    "wp-includes",
                    "wordpress",
                ],

                "Joomla": [
                    "joomla",
                    "/media/system/",
                    "com_content",
                ],

                "Drupal": [
                    "drupal",
                    "/sites/default/",
                ],

                "Shopify": [
                    "shopify",
                    "cdn.shopify.com",
                ],

                "Wix": [
                    "wix",
                    "static.wixstatic.com",
                ],

                "Squarespace": [
                    "squarespace",
                    "static1.squarespace.com",
                ],

                "Ghost": [
                    "ghost",
                    "ghost-content",
                ],

                "Blogger": [
                    "blogger",
                    "blogspot",
                ],

            }

            combined_cms = (
                html_lower
                + " "
                + scripts
                + " "
                + generator
            )

            for cms, patterns in cms_patterns.items():

                if any(
                    pattern in combined_cms
                    for pattern in patterns
                ):

                    result["cms"].append(cms)

            # ---------------------------------
            # JavaScript Library Detection
            # ---------------------------------

            javascript_patterns = {

                "jQuery": [
                    "jquery",
                ],

                "Bootstrap JS": [
                    "bootstrap.min.js",
                    "bootstrap.bundle",
                ],

                "Chart.js": [
                    "chart.js",
                ],

                "D3.js": [
                    "d3.js",
                ],

                "Three.js": [
                    "three.js",
                ],

                "Lodash": [
                    "lodash",
                ],

                "Moment.js": [
                    "moment.js",
                ],

                "Axios": [
                    "axios",
                ],

                "Alpine.js": [
                    "alpine",
                ],

            }

            for library, patterns in javascript_patterns.items():

                if any(
                    pattern in scripts
                    for pattern in patterns
                ):

                    result["javascript_libraries"].append(
                        library
                    )

            # ---------------------------------
            # CSS Framework Detection
            # ---------------------------------

            css_patterns = {

                "Bootstrap": [
                    "bootstrap",
                ],

                "Tailwind CSS": [
                    "tailwind",
                ],

                "Bulma": [
                    "bulma",
                ],

                "Foundation": [
                    "foundation",
                ],

                "Materialize CSS": [
                    "materialize",
                ],

                "Semantic UI": [
                    "semantic",
                ],

                "UIkit": [
                    "uikit",
                ],

            }

            for framework, patterns in css_patterns.items():

                if any(
                    pattern in styles
                    for pattern in patterns
                ):

                    result["css_frameworks"].append(
                        framework
                    )

            # ---------------------------------
            # CDN Detection
            # ---------------------------------

            cdn_patterns = {

                "Cloudflare": [
                    "cdnjs.cloudflare.com",
                    "cloudflare",
                ],

                "jsDelivr": [
                    "cdn.jsdelivr.net",
                ],

                "UNPKG": [
                    "unpkg.com",
                ],

                "Google CDN": [
                    "ajax.googleapis.com",
                ],

                "Bootstrap CDN": [
                    "stackpath.bootstrapcdn.com",
                    "bootstrapcdn.com",
                ],

                "Microsoft CDN": [
                    "ajax.aspnetcdn.com",
                ],

            }

            combined_assets = (
                scripts
                + " "
                + styles
            )

            for cdn, patterns in cdn_patterns.items():

                if any(
                    pattern in combined_assets
                    for pattern in patterns
                ):

                    result["cdn"].append(
                        cdn
                    )

            # ---------------------------------
            # Analytics Detection
            # ---------------------------------

            analytics_patterns = {

                "Google Analytics": [
                    "google-analytics",
                    "gtag(",
                    "analytics.js",
                    "ga(",
                ],

                "Google Tag Manager": [
                    "googletagmanager",
                    "gtm.js",
                ],

                "Meta Pixel": [
                    "connect.facebook.net",
                    "fbq(",
                ],

                "Microsoft Clarity": [
                    "clarity.ms",
                ],

                "Hotjar": [
                    "hotjar",
                ],

                "Matomo": [
                    "matomo",
                    "piwik",
                ],

            }

            combined_html = (
                html_lower
                + " "
                + scripts
            )

            for service, patterns in analytics_patterns.items():

                if any(
                    pattern in combined_html
                    for pattern in patterns
                ):

                    result["analytics"].append(
                        service
                    )

                        # ---------------------------------
            # WAF Detection
            # ---------------------------------

            waf_patterns = {

                "Cloudflare": [
                    "cloudflare",
                    "cf-ray",
                ],

                "Sucuri": [
                    "sucuri",
                    "x-sucuri-id",
                ],

                "Imperva": [
                    "imperva",
                    "incapsula",
                    "x-cdn",
                ],

                "AWS WAF": [
                    "awselb",
                    "x-amzn",
                ],

                "Akamai": [
                    "akamai",
                ],

                "Fastly": [
                    "fastly",
                ],

            }

            header_text = " ".join(
                f"{k}:{v}"
                for k, v in headers.items()
            ).lower()

            for waf, patterns in waf_patterns.items():

                if any(
                    pattern in header_text
                    for pattern in patterns
                ):

                    result["security"].append(
                        f"WAF: {waf}"
                    )

            # ---------------------------------
            # Security Headers
            # ---------------------------------

            security_headers = {

                "Content-Security-Policy":
                    "CSP",

                "Strict-Transport-Security":
                    "HSTS",

                "X-Frame-Options":
                    "Frame Protection",

                "X-Content-Type-Options":
                    "MIME Protection",

                "Referrer-Policy":
                    "Referrer Policy",

                "Permissions-Policy":
                    "Permissions Policy",

                "Cross-Origin-Opener-Policy":
                    "COOP",

                "Cross-Origin-Embedder-Policy":
                    "COEP",

                "Cross-Origin-Resource-Policy":
                    "CORP",

            }

            for header, name in security_headers.items():

                if header.lower() in {

                    h.lower()

                    for h in headers

                }:

                    result["security"].append(name)

            # ---------------------------------
            # Technology Confidence Score
            # ---------------------------------

            confidence = 0

            if result["server"]:
                confidence += 15

            confidence += min(
                len(result["backend"]) * 10,
                20,
            )

            confidence += min(
                len(result["frontend"]) * 10,
                20,
            )

            confidence += min(
                len(result["cms"]) * 15,
                15,
            )

            confidence += min(
                len(result["javascript_libraries"]) * 2,
                10,
            )

            confidence += min(
                len(result["css_frameworks"]) * 3,
                10,
            )

            confidence += min(
                len(result["analytics"]) * 2,
                5,
            )

            confidence += min(
                len(result["security"]) * 2,
                5,
            )

            result["fingerprint_confidence"] = min(
                confidence,
                100,
            )
            
            # ---------------------------------
            # Version Detection
            # ---------------------------------

            version_patterns = {

                "jQuery":
                    r"jquery(?:\.min)?-([0-9]+\.[0-9]+(?:\.[0-9]+)?)",

                "Bootstrap":
                    r"bootstrap(?:\.bundle)?(?:\.min)?-([0-9]+\.[0-9]+(?:\.[0-9]+)?)",

                "Vue":
                    r"vue(?:\.runtime)?(?:\.global)?(?:\.prod)?-([0-9]+\.[0-9]+(?:\.[0-9]+)?)",

                "React":
                    r"react(?:\.production)?(?:\.min)?-([0-9]+\.[0-9]+(?:\.[0-9]+)?)",

                "Angular":
                    r"angular(?:\.min)?-([0-9]+\.[0-9]+(?:\.[0-9]+)?)",

            }

            assets = (
                scripts
                + " "
                + styles
            )

            for tech, pattern in version_patterns.items():

                match = re.search(
                    pattern,
                    assets,
                    re.I,
                )

                if match:

                    result["versions"][tech] = match.group(1)

            # ---------------------------------
            # Technology Risk Score
            # ---------------------------------

            risk_score = 0

            recommendations = []

            if result["server"] == "Apache":

                risk_score += 5

            if result["server"] == "Microsoft IIS":

                risk_score += 5

            if "PHP" in result["backend"]:

                risk_score += 5

            if "jQuery" in result["javascript_libraries"]:

                risk_score += 5

            if "WordPress" in result["cms"]:

                risk_score += 5

            if "Bootstrap" in result["css_frameworks"]:

                risk_score += 3

            if not result["security"]:

                risk_score += 15

                recommendations.append(
                    "No major security headers detected."
                )

            if result["server"] is None:

                recommendations.append(
                    "Unable to identify the web server."
                )

            if not result["analytics"]:

                recommendations.append(
                    "No analytics platform detected."
                )

            if "WordPress" in result["cms"]:

                recommendations.append(
                    "Ensure WordPress core and plugins are fully updated."
                )

            if "PHP" in result["backend"]:

                recommendations.append(
                    "Verify the PHP version is supported."
                )

            if result["fingerprint_confidence"] < 40:

                recommendations.append(
                    "Technology fingerprint confidence is low."
                )

            result["technology_risk_score"] = min(
                risk_score,
                100,
            )

            # ---------------------------------
            # Overall Rating
            # ---------------------------------

            if risk_score >= 40:

                result["technology_risk"] = "High"

            elif risk_score >= 20:

                result["technology_risk"] = "Medium"

            else:

                result["technology_risk"] = "Low"

            result["recommendations"] = sorted(
                set(recommendations)
            )

            # ---------------------------------
            # Technology Summary
            # ---------------------------------

            result["summary"] = {

                "server": result["server"],

                "backend_count": len(
                    result["backend"]
                ),

                "frontend_count": len(
                    result["frontend"]
                ),

                "cms_count": len(
                    result["cms"]
                ),

                "javascript_library_count": len(
                    result["javascript_libraries"]
                ),

                "css_framework_count": len(
                    result["css_frameworks"]
                ),

                "analytics_count": len(
                    result["analytics"]
                ),

                "security_features": len(
                    result["security"]
                ),

                "fingerprint_confidence":
                    result["fingerprint_confidence"],

                "technology_risk":
                    result["technology_risk"],

            }

            # ---------------------------------
            # Remove Duplicates
            # ---------------------------------

            result["backend"] = sorted(
                set(result["backend"])
            )

            result["frontend"] = sorted(
                set(result["frontend"])
            )

            result["cms"] = sorted(
                set(result["cms"])
            )

            result["javascript_libraries"] = sorted(
                set(result["javascript_libraries"])
            )

            result["css_frameworks"] = sorted(
                set(result["css_frameworks"])
            )

            result["cdn"] = sorted(
                set(result["cdn"])
            )

            result["analytics"] = sorted(
                set(result["analytics"])
            )
            
            result["security"] = sorted(
                set(result["security"])
            )

        except Exception as e:

            result["error"] = str(e)

        return result