import asyncio
import sys

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.request import URLRequest, TextAnalysisRequest
from app.models.response import AnalysisResponse, TextAnalysisResponse
from app.orchestrator import analyze_url
from app.services.qr_decoder import QRDecodeError, decode_qr_image
from app.analyzers.nlp import TextAnalyzer

router = APIRouter(
    prefix="/analyze",
    tags=["URL Analyzer"]
)


def _analyze_on_worker_loop(url: str) -> AnalysisResponse:
    """Run Playwright on a Windows Proactor loop.

    Uvicorn may use a Selector loop on Windows, which cannot create the
    subprocesses Playwright requires.  The dashboard calls this synchronous
    endpoint, so it needs the same worker-loop protection as queued scans.
    """
    if sys.platform == "win32":
        from asyncio.windows_events import ProactorEventLoop
        loop = ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(analyze_url(url))
    finally:
        loop.close()


@router.post(
    "",
    response_model=AnalysisResponse,
    summary="Analyze a URL"
)
async def analyze(request: URLRequest):
    """
    Analyze a website URL and return the collected results.

    Current version:
    - Receives URL
    - Passes URL to orchestrator
    - Returns response

    Future versions will:
    - Validate URL
    - Normalize URL
    - Run HTTP Analyzer
    - Run DNS Analyzer
    - Run Domain Intelligence
    - Run SSL Analysis
    - Run Browser Analysis
    - Run HTML Analysis
    - Run JavaScript Analysis
    - Run Form Analysis
    - Run Reputation Analysis
    - Run Machine Learning Classifier
    """

    try:
        result = await asyncio.to_thread(
            _analyze_on_worker_loop,
            request.url,
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post(
    "/qr",
    response_model=AnalysisResponse,
    summary="Decode and analyze a QR code URL",
)
async def analyze_qr(image: UploadFile = File(...)):
    """Decode one QR image, then run its website URL through the normal pipeline."""
    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP QR code image.")

    try:
        decoded_url = decode_qr_image(await image.read())
    except QRDecodeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        await image.close()

    try:
        result = await asyncio.to_thread(_analyze_on_worker_loop, decoded_url)
        result.data["qr"] = {"decoded_value": decoded_url, "filename": image.filename}
        return result
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/text", response_model=TextAnalysisResponse, summary="Analyze email or message text")
async def analyze_text(request: TextAnalysisRequest):
    """Run explainable text heuristics and analyze up to three embedded URLs."""
    try:
        text_result = TextAnalyzer().analyze(request.text)
        if not text_result["success"]:
            raise HTTPException(status_code=400, detail=text_result["error"])
        url_analyses = {}
        urls = text_result.get("urls_found", [])[:3]
        results = await asyncio.gather(*(asyncio.to_thread(_analyze_on_worker_loop, url) for url in urls), return_exceptions=True)
        max_probability = text_result["phishing_probability"]
        final_risk = text_result["risk"]
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                url_analyses[url] = {"success": False, "risk": "Unknown", "message": str(result)}
                continue
            data = result.model_dump()
            url_analyses[url] = data
            probability = data.get("phishing_probability") or 0
            if probability > max_probability:
                max_probability, final_risk = probability, data.get("risk", final_risk)
            if data.get("risk") in {"Medium", "High", "Critical"}:
                text_result["indicators"].append({"reason": f"Contains suspicious link ({data['risk']} risk): {url}", "impact": "high" if data["risk"] in {"High", "Critical"} else "medium", "value": 1})
        return TextAnalysisResponse(success=True, text=request.text, phishing_probability=max_probability, risk=final_risk, data={"indicators": text_result["indicators"], "features": text_result["features"], "urls_found": text_result["urls_found"], "url_analyses": url_analyses, "classification": {"model_version": "text-heuristics-v1", "contributors": text_result["indicators"]}})
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {error}") from error
