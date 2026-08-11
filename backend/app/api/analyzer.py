import asyncio
import sys

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.request import URLRequest
from app.models.response import AnalysisResponse
from app.orchestrator import analyze_url
from app.services.qr_decoder import QRDecodeError, decode_qr_image

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
