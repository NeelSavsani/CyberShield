"""
CyberShield Link Analyzer

Phase 1
--------
Responsibilities

✓ Parse rendered HTML
✓ Extract all hyperlinks
✓ Count total links
✓ Detect:
    - Internal links
    - External links
    - Empty links
    - Anchor links
    - JavaScript links
    - Mailto links
    - Telephone links

Future Phases

✓ URL Intelligence
✓ Suspicious URLs
✓ URL Shorteners
✓ Punycode
✓ IP URLs
✓ Hidden Links
✓ Download Links
✓ Redirect Links
✓ Link Risk Score
"""

import ipaddress
import re
from urllib.parse import (
    parse_qs,
    urljoin,
    urlparse,
)

from bs4 import BeautifulSoup

from app.models.browser_session import BrowserSession


class LinkAnalyzer:
    """
    Analyze hyperlinks from the rendered webpage.
    """

    async def analyze(
        self,
        browser_session: BrowserSession,
    ) -> dict:

        html = browser_session.html

        if not html:

            return {"links_available": False, "error": "No rendered HTML available."}

        soup = BeautifulSoup(html, "lxml")

        current_url = browser_session.final_url

        current_host = (urlparse(current_url).hostname or "").lower()

        result = {
            # ---------------------------------
            # General
            # ---------------------------------
            "links_available": True,
            "total_links": 0,
            # ---------------------------------
            # Link Statistics
            # ---------------------------------
            "internal_links": 0,
            "external_links": 0,
            "empty_links": 0,
            "anchor_links": 0,
            "javascript_links": 0,
            "mailto_links": 0,
            "telephone_links": 0,
            # ---------------------------------
            # URL Intelligence
            # ---------------------------------
            "http_links": 0,
            "https_links": 0,
            "ip_links": 0,
            "shortened_links": 0,
            "punycode_links": 0,
            "suspicious_tld_links": 0,
            "long_url_links": 0,
            "query_parameter_links": 0,
            "fragment_links": 0,
            "credential_links": 0,
            "custom_port_links": 0,
            # ---------------------------------
            # Phishing Detection
            # ---------------------------------
            "hidden_links": 0,
            "download_links": 0,
            "suspicious_keyword_links": 0,
            "mismatched_links": 0,
            "unsafe_target_blank_links": 0,
            "redirect_links": 0,
            "high_risk_links": 0,
            # ---------------------------------
            # Advanced Phishing Detection
            # ---------------------------------
            "unicode_links": 0,
            "encoded_links": 0,
            "multiple_subdomain_links": 0,
            "suspicious_path_links": 0,
            "executable_filename_links": 0,
            "long_hostname_links": 0,
            "double_extension_links": 0,
            # ---------------------------------
            # Link Risk Assessment
            # ---------------------------------

            "safe_links": 0,

            "medium_risk_links": 0,

            "critical_risk_links": 0,

            "average_risk_score": 0.0,

            "highest_risk_score": 0,

            "highest_risk_url": None,

            "top_risky_links": [],
            # ---------------------------------
            # Details
            # ---------------------------------
            "links": [],
            # ---------------------------------
            # Future
            # ---------------------------------
            "error": None,
        }

        try:

            links = soup.find_all("a")

            result["total_links"] = len(links)

            # ---------------------------------
            # Known URL Shorteners
            # ---------------------------------

            shorteners = {
                "bit.ly",
                "tinyurl.com",
                "goo.gl",
                "t.co",
                "is.gd",
                "buff.ly",
                "ow.ly",
                "rb.gy",
                "cutt.ly",
                "shorturl.at",
            }

            # ---------------------------------
            # Suspicious TLDs
            # ---------------------------------

            suspicious_tlds = {
                ".zip",
                ".mov",
                ".xyz",
                ".top",
                ".click",
                ".work",
                ".gq",
                ".tk",
                ".cf",
                ".ml",
                ".ga",
            }

            # ---------------------------------
            # Suspicious Keywords
            # ---------------------------------

            suspicious_keywords = {
                "login",
                "signin",
                "verify",
                "verification",
                "update",
                "secure",
                "security",
                "password",
                "account",
                "bank",
                "wallet",
                "payment",
                "invoice",
                "confirm",
                "recover",
                "unlock",
            }

            # ---------------------------------
            # Suspicious Path Keywords
            # ---------------------------------

            suspicious_paths = {
                "login",
                "signin",
                "verify",
                "verification",
                "secure",
                "account",
                "update",
                "password",
                "bank",
                "wallet",
                "invoice",
                "payment",
                "recover",
                "unlock",
            }

            download_extensions = (
                ".exe",
                ".zip",
                ".rar",
                ".7z",
                ".msi",
                ".apk",
                ".bat",
                ".cmd",
                ".scr",
                ".js",
                ".vbs",
            )

            dangerous_files = (
                ".exe",
                ".scr",
                ".bat",
                ".cmd",
                ".msi",
                ".apk",
                ".vbs",
                ".ps1",
            )

            dangerous_extensions = (
                ".exe",
                ".scr",
                ".bat",
                ".cmd",
                ".apk",
                ".vbs",
            )

            redirect_params = {
                "url",
                "redirect",
                "next",
                "target",
                "dest",
                "destination",
            }

            for index, link in enumerate(links, start=1):
                href = (link.get("href") or "").strip()
                text = link.get_text(" ", strip=True)
                title = link.get("title")
                target = link.get("target")
                rel = link.get("rel")

                absolute_url = ""
                link_type = "unknown"
                parsed = None
                hostname = None
                risk_score = 0

                hidden = False
                download = False
                mismatch = False
                unsafe_blank = False
                redirect = False
                keyword_hit = False

                unicode_link = False

                encoded_link = False

                many_subdomains = False

                suspicious_path = False

                exe_filename = False

                long_hostname = False

                double_extension = False

                style = (link.get("style") or "").lower()
                classes = " ".join(link.get("class", [])).lower()

                # Hidden-link detection
                if (
                    "display:none" in style
                    or "visibility:hidden" in style
                    or "opacity:0" in style
                    or link.get("hidden") is not None
                    or "hidden" in classes
                ):
                    hidden = True
                    result["hidden_links"] += 1
                    risk_score += 2

                # Link classification
                if href == "":
                    result["empty_links"] += 1
                    link_type = "empty"

                elif href.startswith("#"):
                    result["anchor_links"] += 1
                    link_type = "anchor"

                elif href.lower().startswith("javascript:"):
                    result["javascript_links"] += 1
                    link_type = "javascript"

                elif href.lower().startswith("mailto:"):
                    result["mailto_links"] += 1
                    link_type = "mailto"

                elif href.lower().startswith("tel:"):
                    result["telephone_links"] += 1
                    link_type = "telephone"

                else:
                    absolute_url = urljoin(current_url, href)

                    if (
                        href.lower().endswith(download_extensions)
                        or link.get("download") is not None
                    ):
                        download = True
                        result["download_links"] += 1
                        risk_score += 2

                    parsed = urlparse(absolute_url)
                    hostname = (parsed.hostname or "").lower()

                    # ---------------------------------
                    # Unicode / Homograph
                    # ---------------------------------

                    if any(ord(ch) > 127 for ch in hostname):
                        unicode_link = True
                        result["unicode_links"] += 1
                        risk_score += 3

                    if "xn--" in hostname:
                        result["punycode_links"] += 1
                        unicode_link = True
                        risk_score += 3

                    # ---------------------------------
                    # URL Encoding
                    # ---------------------------------

                    if re.search(r"%[0-9A-Fa-f]{2}", absolute_url):
                        encoded_link = True
                        result["encoded_links"] += 1
                        risk_score += 1

                    # ---------------------------------
                    # Excessive Subdomains
                    # ---------------------------------

                    labels = hostname.split(".")

                    if len(labels) > 4:

                        many_subdomains = True

                        result["multiple_subdomain_links"] += 1

                        risk_score += 2

                    # ---------------------------------
                    # Long Hostname
                    # ---------------------------------

                    if len(hostname) > 50:

                        long_hostname = True

                        result["long_hostname_links"] += 1

                        risk_score += 1

                    combined = " ".join(
                        [
                            href.lower(),
                            text.lower(),
                            (title or "").lower(),
                        ]
                    )

                    path_lower = parsed.path.lower()

                    if any(word in path_lower for word in suspicious_paths):

                        suspicious_path = True

                        result["suspicious_path_links"] += 1

                        risk_score += 1

                    filename = path_lower.split("/")[-1]

                    if filename.endswith(dangerous_files):

                        exe_filename = True

                        result["executable_filename_links"] += 1

                        risk_score += 2

                    for ext in dangerous_extensions:

                        if ext in filename:

                            prefix = filename.split(ext)[0]

                            if "." in prefix:

                                double_extension = True

                                result["double_extension_links"] += 1

                                risk_score += 3

                                break

                    if any(word in combined for word in suspicious_keywords):
                        keyword_hit = True
                        result["suspicious_keyword_links"] += 1
                        risk_score += 1

                    if parsed.scheme == "https":
                        result["https_links"] += 1
                    elif parsed.scheme == "http":
                        result["http_links"] += 1

                    try:
                        ipaddress.ip_address(hostname)
                        result["ip_links"] += 1
                        risk_score += 2
                    except ValueError:
                        pass

                    if hostname in shorteners:
                        result["shortened_links"] += 1
                        risk_score += 2

                    if any(hostname.endswith(tld) for tld in suspicious_tlds):
                        result["suspicious_tld_links"] += 1
                        risk_score += 1

                    if len(absolute_url) > 120:
                        result["long_url_links"] += 1

                    if parsed.query:

                        params = parse_qs(parsed.query)

                        if redirect_params.intersection(params):

                            redirect = True

                            result["redirect_links"] += 1

                            risk_score += 2

                        result["query_parameter_links"] += 1

                    if parsed.fragment:
                        result["fragment_links"] += 1

                    if parsed.username:
                        result["credential_links"] += 1

                    if parsed.port not in (None, 80, 443):
                        result["custom_port_links"] += 1

                    if hostname == current_host:
                        result["internal_links"] += 1
                        link_type = "internal"
                    else:
                        result["external_links"] += 1
                        link_type = "external"

                # Independent phishing checks
                if absolute_url and text.startswith(("http://", "https://")):

                    normalized_text = text.rstrip("/")

                    normalized_url = absolute_url.rstrip("/")

                    if normalized_text != normalized_url:

                        mismatch = True
                        result["mismatched_links"] += 1
                        risk_score += 2

                if target == "_blank":
                    rel_values = {value.lower() for value in (rel or [])}

                    if not ("noopener" in rel_values or "noreferrer" in rel_values):
                        unsafe_blank = True
                        result["unsafe_target_blank_links"] += 1
                        risk_score += 1

                # ---------------------------------
                # Risk Classification
                # ---------------------------------

                if risk_score >= 7:

                    result["critical_risk_links"] += 1

                elif risk_score >= 4:

                    result["high_risk_links"] += 1

                elif risk_score >= 2:

                    result["medium_risk_links"] += 1

                else:

                    result["safe_links"] += 1
                    
                # ---------------------------------
                # Highest Risk Link
                # ---------------------------------

                if risk_score > result["highest_risk_score"]:

                    result["highest_risk_score"] = risk_score

                    result["highest_risk_url"] = absolute_url
                    
                if risk_score >= 4:

                    result["top_risky_links"].append({

                        "url": absolute_url,

                        "risk_score": risk_score,

                        "type": link_type,

                    })

                # Always append exactly once per link
                result["links"].append(
                    {
                        "index": index,
                        "text": text,
                        "href": href,
                        "absolute_url": absolute_url,
                        "scheme": parsed.scheme if parsed else None,
                        "hostname": hostname if parsed else None,
                        "query": parsed.query if parsed else None,
                        "fragment": parsed.fragment if parsed else None,
                        "type": link_type,
                        "hidden": hidden,
                        "download": download,
                        "suspicious_keyword": keyword_hit,
                        "anchor_mismatch": mismatch,
                        "unsafe_target_blank": unsafe_blank,
                        "redirect_link": redirect,
                        "unicode": unicode_link,
                        "encoded": encoded_link,
                        "multiple_subdomains": many_subdomains,
                        "suspicious_path": suspicious_path,
                        "executable_filename": exe_filename,
                        "long_hostname": long_hostname,
                        "double_extension": double_extension,
                        "risk_score": risk_score,
                        "title": title,
                        "target": target,
                        "rel": rel,
                    }
                )
                
            # ---------------------------------
            # Overall Risk Statistics
            # ---------------------------------

            if result["total_links"] > 0:

                total_score = sum(

                    link["risk_score"]

                    for link in result["links"]

                )

                result["average_risk_score"] = round(

                    total_score / result["total_links"],

                    2,

                )

            # Keep only the riskiest links

            result["top_risky_links"] = sorted(

                result["top_risky_links"],

                key=lambda x: x["risk_score"],

                reverse=True,

            )[:10]

        except Exception as e:

            result["error"] = str(e)

        return result
