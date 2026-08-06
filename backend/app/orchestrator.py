"""
CyberShield Orchestrator

Responsibilities:
- Validate URL
- Normalize URL
- Execute analyzers
- Merge analyzer results
- Return a standard response
"""
from app.analyzers.javascript import JavaScriptAnalyzer
from app.analyzers.html import HTMLAnalyzer
from app.analyzers.forms import FormAnalyzer
from app.models.response import AnalysisResponse
from app.services.classifier import EvidenceClassifier
from app.services.feature_extractor import FeatureExtractor
from app.services.url_safety import UnsafeTargetError, ensure_safe_analysis_target
from app.utils.url import (
    normalize_url,
    is_valid_url,
)

# ----------------------------------------------------
# Import Analyzers
# ----------------------------------------------------

from app.analyzers.http import HTTPAnalyzer
from app.analyzers.dns import DNSAnalyzer
from app.analyzers.domain import DomainAnalyzer
from app.analyzers.ssl import SSLAnalyzer
from app.analyzers.browser import BrowserAnalyzer
from app.analyzers.reputation import ReputationAnalyzer


async def analyze_url(url: str) -> AnalysisResponse:
    """
    Main URL analysis pipeline.
    """

    # ----------------------------------------------------
    # Normalize URL
    # ----------------------------------------------------

    normalized_url = normalize_url(url)

    # ----------------------------------------------------
    # Validate URL
    # ----------------------------------------------------

    if not is_valid_url(normalized_url):

        return AnalysisResponse(
            success=False,
            url=url,
            normalized_url=normalized_url,
            exists=False,
            phishing_probability=None,
            risk="Unknown",
            message="Invalid URL.",
            data={}
        )

    try:
        resolved_addresses = await ensure_safe_analysis_target(normalized_url)
    except UnsafeTargetError as error:
        return AnalysisResponse(
            success=False,
            url=url,
            normalized_url=normalized_url,
            exists=False,
            phishing_probability=None,
            risk="Unknown",
            message=str(error),
            data={"safety": {"allowed": False}},
        )

    # ----------------------------------------------------
    # Initialize
    # ----------------------------------------------------

    analysis_data = {"safety": {"allowed": True, "resolved_addresses": resolved_addresses}}

    exists = False

    browser = BrowserAnalyzer()

    try:

        # ==================================================
        # HTTP Analyzer
        # ==================================================

        http = HTTPAnalyzer()

        http_result = await http.analyze(
            normalized_url
        )

        analysis_data["http"] = http_result

        exists = http_result.get(
            "reachable",
            False
        )

        # A transport failure (such as an NXDOMAIN hostname or a refused
        # connection) means there is no page to inspect. Do not feed missing
        # evidence into the classifier: its neutral defaults can otherwise
        # incorrectly produce a "Safe" verdict with a zero score.
        if not exists:
            return AnalysisResponse(
                success=False,
                url=url,
                normalized_url=normalized_url,
                exists=False,
                phishing_probability=None,
                risk="Unknown",
                message="URL not found.",
                data={"http": http_result},
            )

        # ==================================================
        # DNS Analyzer
        # ==================================================

        dns = DNSAnalyzer()

        dns_result = await dns.analyze(
            normalized_url
        )

        analysis_data["dns"] = dns_result

        # ==================================================
        # Domain Analyzer
        # ==================================================

        domain = DomainAnalyzer()

        domain_result = await domain.analyze(
            normalized_url
        )

        analysis_data["domain"] = domain_result

        # ==================================================
        # SSL Analyzer
        # ==================================================

        ssl = SSLAnalyzer()

        ssl_result = await ssl.analyze(
            normalized_url
        )

        analysis_data["ssl"] = ssl_result

        reputation_result = await ReputationAnalyzer().analyze(normalized_url)
        analysis_data["reputation"] = reputation_result

        # =========================================
        # Browser
        # =========================================

        try:

            browser_session = await browser.analyze(
                normalized_url
            )

            analysis_data["browser"] = {
                "original_url": browser_session.original_url,
                "final_url": browser_session.final_url,
                "title": browser_session.title,
                "html_length": len(browser_session.html),
                "cookies": len(browser_session.cookies),
                "redirect_chain": browser_session.redirect_chain,
                "popups": browser_session.popups,
                "downloads": browser_session.downloads,
                "permission_requests": browser_session.permission_requests,
                "javascript_errors": browser_session.javascript_errors,
                "network_request_count": len(browser_session.network_requests),
                "network_response_count": len(browser_session.network_responses),
                "screenshot": browser_session.screenshot_path,
                "browser_error": browser_session.error,
            }

            # =========================================
            # HTML Analyzer
            # =========================================

            html = HTMLAnalyzer()

            html_result = await html.analyze(
                browser_session
            )

            analysis_data["html"] = html_result

            # =========================================
            # JavaScript Analyzer
            # =========================================

            javascript = JavaScriptAnalyzer()

            javascript_result = await javascript.analyze(
                browser_session
            )

            analysis_data["javascript"] = javascript_result
            
            # =========================================
            # Form Analyzer
            # =========================================

            form = FormAnalyzer()

            form_result = await form.analyze(
                browser_session
            )

            analysis_data["form"] = form_result

        except Exception as e:

            analysis_data["browser"] = {
                "original_url": normalized_url,
                "final_url": None,
                "title": None,
                "html_length": 0,
                "cookies": 0,
                "screenshot": None,
                "browser_error": str(e),
            }

            # Browser failed, so HTML cannot be analyzed
            analysis_data["html"] = {
                "html_available": False,
                "error": "Browser analysis failed."
            }

    finally:

        try:
            await browser.close()
        except Exception:
            pass

    # ----------------------------------------------------
    # Final Response
    # ----------------------------------------------------

    features = FeatureExtractor().extract(analysis_data)
    classification = EvidenceClassifier().predict(features)
    analysis_data["features"] = features
    analysis_data["classification"] = classification

    return AnalysisResponse(
        success=True,
        url=url,
        normalized_url=normalized_url,
        exists=exists,
        phishing_probability=classification["phishing_probability"],
        risk=classification["risk"],
        message="Analysis completed successfully.",
        data=analysis_data
    )
