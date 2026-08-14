import asyncio
import sys
from uuid import uuid4

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

# Jobs live in the API process while a scan is running. The result is returned
# by polling, so leaving dashboard.html no longer cancels the browser work.
_jobs: dict[str, dict] = {}


async def _run_job(job_id: str, worker, *args):
    _jobs[job_id]["status"] = "running"
    try:
        result = await worker(*args)
        _jobs[job_id].update(status="complete", result=result.model_dump(mode="json") if hasattr(result, "model_dump") else result)
    except Exception as error:
        _jobs[job_id].update(status="failed", error=str(error))


def _new_job(worker, *args) -> str:
    job_id = str(uuid4())
    _jobs[job_id] = {"status": "queued", "result": None, "error": None}
    asyncio.create_task(_run_job(job_id, worker, *args))
    return job_id


async def _url_worker(url: str):
    return await asyncio.to_thread(_analyze_on_worker_loop, url)


async def _text_worker(text: str):
    # Reuse the same text pipeline as the synchronous endpoint.
    text_result = TextAnalyzer().analyze(text)
    if not text_result["success"]:
        raise ValueError(text_result["error"])
    urls = text_result.get("urls_found", [])[:3]
    results = await asyncio.gather(*(_url_worker(url) for url in urls), return_exceptions=True)
    url_analyses = {}
    max_probability = text_result["phishing_probability"]
    final_risk = text_result["risk"]
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            url_analyses[url] = {"success": False, "risk": "Unknown", "message": str(result)}
            continue
        data = result.model_dump(mode="json")
        url_analyses[url] = data
        probability = data.get("phishing_probability") or 0
        if probability > max_probability:
            max_probability, final_risk = probability, data.get("risk", final_risk)
    text_result["phishing_probability"] = max_probability
    text_result["risk"] = final_risk
    return TextAnalysisResponse(success=True, text=text, phishing_probability=max_probability, risk=final_risk, data={"indicators": text_result["indicators"], "features": text_result["features"], "urls_found": text_result["urls_found"], "url_analyses": url_analyses, "classification": {"model_version": "text-heuristics-v1", "contributors": text_result["indicators"]}})


async def _qr_worker(url: str, filename: str | None):
    result = await _url_worker(url)
    result.data["qr"] = {"decoded_value": url, "filename": filename}
    return result


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


@router.post("/jobs/url", status_code=202)
async def start_url_job(request: URLRequest):
    job_id = _new_job(_url_worker, request.url)
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/text", status_code=202)
async def start_text_job(request: TextAnalysisRequest):
    job_id = _new_job(_text_worker, request.text)
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/qr", status_code=202)
async def start_qr_job(image: UploadFile = File(...)):
    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP QR code image.")
    try:
        decoded_url = decode_qr_image(await image.read())
        filename = image.filename
    except QRDecodeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        await image.close()
    job_id = _new_job(_qr_worker, decoded_url, filename)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return {"job_id": job_id, **job}
