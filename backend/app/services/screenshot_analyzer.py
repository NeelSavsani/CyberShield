"""Safe, evidence-based screenshot phishing analysis.

This service never executes embedded image content.  It validates file magic,
decodes pixels with Pillow, re-encodes accepted images without metadata, then
uses OCR and conservative visual heuristics to produce explainable evidence.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import zxingcpp
from PIL import Image, UnidentifiedImageError

from app.analyzers.nlp import TextAnalyzer
from app.services.database import create_screenshot_asset

try:
    import pytesseract
except ImportError:  # pragma: no cover - surfaced in the API response
    pytesseract = None

def _configure_tesseract() -> str | None:
    """Resolve Tesseract for the current process, including Windows defaults."""
    if pytesseract is None:
        return None
    candidates = [
        os.getenv("TESSERACT_CMD"),
        str(Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")),
        str(Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")),
        shutil.which("tesseract"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate
    return None


def ocr_status() -> dict:
    """Return a safe readiness diagnostic; no user image/text is exposed."""
    executable = _configure_tesseract()
    if pytesseract is None:
        return {"available": False, "executable": None, "error": "Python package pytesseract is not installed."}
    if not executable:
        return {"available": False, "executable": None, "error": "Tesseract executable was not found."}
    try:
        return {"available": True, "executable": executable, "version": str(pytesseract.get_tesseract_version()).splitlines()[0]}
    except Exception as error:
        return {"available": False, "executable": executable, "error": str(error)[:300]}


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_DIMENSION = 6_000
RETENTION_DAYS = 30
ASSET_DIRECTORY = Path(__file__).resolve().parents[2] / "reports" / "screenshot_assets"

MAGIC_BYTES = {
    "PNG": b"\x89PNG\r\n\x1a\n",
    "JPEG": b"\xff\xd8\xff",
}
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
DECLARED_TYPE_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
KNOWN_BRANDS = {
    "paypal": {"paypal.com"}, "netflix": {"netflix.com"},
    "microsoft": {"microsoft.com", "live.com", "office.com"},
    "google": {"google.com", "gmail.com"}, "amazon": {"amazon.com"},
    "apple": {"apple.com", "icloud.com"}, "facebook": {"facebook.com", "fb.com"},
    "instagram": {"instagram.com"}, "whatsapp": {"whatsapp.com"},
    "paytm": {"paytm.com"}, "chase": {"chase.com"},
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "rb.gy", "is.gd", "cutt.ly", "shorturl.at", "tiny.cc"}


class ScreenshotValidationError(ValueError):
    """Raised when an upload is not a safe, supported screenshot."""


class ScreenshotAnalyzer:
    def analyze(self, raw_image: bytes, filename: str | None = None, declared_content_type: str | None = None) -> dict:
        image, image_format = self._validate_and_decode(raw_image)
        if declared_content_type and DECLARED_TYPE_FORMATS.get(declared_content_type) != image_format:
            raise ScreenshotValidationError("Declared image type does not match the file signature.")
        width, height = image.size
        sha256 = hashlib.sha256(raw_image).hexdigest()
        ocr = self._ocr(image)
        text_result = TextAnalyzer().analyze(ocr["text"]) if ocr["text"] else self._empty_text_result()
        qr_values = self._read_qr(image)
        visual = self._visual_features(image, ocr["text"])
        indicators = self._indicators(ocr, text_result, qr_values, visual)
        probability = self._score(indicators)
        risk = self._risk(probability)
        asset = self._store_sanitized_asset(image, raw_image, sha256, width, height, ocr["confidence"])

        return {
            "success": True,
            "phishing_probability": probability,
            "risk": risk,
            "data": {
                "asset": asset,
                "image": {"format": image_format, "dimensions": f"{width}x{height}", "file_size": len(raw_image)},
                "ocr": ocr,
                "text_analysis": {
                    "phishing_probability": text_result["phishing_probability"],
                    "risk": text_result["risk"],
                    "urls_found": text_result["urls_found"],
                },
                "visual": visual,
                "qr_codes": qr_values,
                "classification": {
                    "model_version": "screenshot-evidence-baseline-v1",
                    "contributors": indicators,
                    "notice": "Screenshot findings are probabilistic visual and OCR evidence; confirm against the original source before taking action.",
                },
            },
        }

    @staticmethod
    def _validate_and_decode(raw_image: bytes) -> tuple[Image.Image, str]:
        if not raw_image:
            raise ScreenshotValidationError("Upload a screenshot first.")
        if len(raw_image) > MAX_UPLOAD_BYTES:
            raise ScreenshotValidationError("Screenshots must be 5 MB or smaller.")
        if not (raw_image.startswith(MAGIC_BYTES["PNG"]) or raw_image.startswith(MAGIC_BYTES["JPEG"]) or (raw_image[:4] == b"RIFF" and raw_image[8:12] == b"WEBP")):
            raise ScreenshotValidationError("File signature is not PNG, JPEG, or WebP.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw_image)) as candidate:
                    image_format = candidate.format or ""
                    if image_format not in ALLOWED_FORMATS:
                        raise ScreenshotValidationError("Only PNG, JPEG, and WebP screenshots are accepted.")
                    width, height = candidate.size
                    if width < 1 or height < 1 or width > MAX_DIMENSION or height > MAX_DIMENSION or width * height > MAX_IMAGE_PIXELS:
                        raise ScreenshotValidationError("Screenshot dimensions exceed the allowed limit.")
                    candidate.load()  # fully decode pixels before any analysis
                    # convert also drops EXIF/XMP and avoids processing metadata later
                    return candidate.convert("RGB"), image_format
        except ScreenshotValidationError:
            raise
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError) as error:
            raise ScreenshotValidationError("The uploaded file could not be decoded as an image.") from error

    @staticmethod
    def _ocr(image: Image.Image) -> dict:
        status = ocr_status()
        if not status["available"]:
            return {"text": "", "confidence": None, "words": [], "available": False, "error": status.get("error", "Tesseract OCR is unavailable.")}
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config="--psm 6")
            words = []
            confidences = []
            for text, confidence in zip(data["text"], data["conf"]):
                text = text.strip()
                try:
                    confidence = float(confidence)
                except (TypeError, ValueError):
                    confidence = -1
                if text and confidence >= 0:
                    words.append({"text": text, "confidence": round(confidence, 1)})
                    confidences.append(confidence)
            return {
                "text": " ".join(word["text"] for word in words),
                "confidence": round(sum(confidences) / len(confidences)) if confidences else 0,
                "words": words[:300], "available": True,
            }
        except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, RuntimeError, OSError) as error:
            return {"text": "", "confidence": None, "words": [], "available": False, "error": str(error)[:300]}

    @staticmethod
    def _read_qr(image: Image.Image) -> list[str]:
        pixels = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        values: list[str] = []
        detector = cv2.QRCodeDetector()
        try:
            detected, decoded, _, _ = detector.detectAndDecodeMulti(pixels)
            if detected:
                values.extend(value.strip() for value in decoded if value and value.strip())
        except cv2.error:
            pass
        if not values:
            try:
                value, _, _ = detector.detectAndDecode(pixels)
                if value and value.strip():
                    values.append(value.strip())
            except cv2.error:
                pass
        if not values:
            try:
                values.extend(code.text.strip() for code in zxingcpp.read_barcodes(pixels) if code.text and code.text.strip())
            except Exception:
                pass
        return list(dict.fromkeys(values))[:5]

    @staticmethod
    def _visual_features(image: Image.Image, text: str) -> dict:
        pixels = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(pixels, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        width, height = image.size
        field_like = 0
        logo_like = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < 1_000:
                continue
            aspect = w / max(h, 1)
            if 2.0 <= aspect <= 12 and w >= width * 0.22 and h >= 20:
                field_like += 1
            if y < height * 0.30 and 0.4 <= aspect <= 5 and width * 0.02 <= w <= width * 0.45 and height * 0.02 <= h <= height * 0.22:
                logo_like += 1
        lower = text.lower()
        return {
            "form_like_layout": field_like >= 2,
            "form_like_field_count": min(field_like, 20),
            "logo_like_region_count": min(logo_like, 20),
            "login_prompt": bool(re.search(r"\b(log[ -]?in|sign[ -]?in|username|user ?id)\b", lower)),
            "password_or_otp_prompt": bool(re.search(r"\b(password|passcode|one[- ]?time|otp|verification code|security code)\b", lower)),
            "payment_prompt": bool(re.search(r"\b(payment|pay now|credit card|debit card|card number|bank account|billing)\b", lower)),
            "urgency_banner": bool(re.search(r"\b(urgent|immediately|act now|action required|suspended|expire[sd]?|final warning)\b", lower)),
        }

    def _indicators(self, ocr: dict, text_result: dict, qr_values: list[str], visual: dict) -> list[dict]:
        indicators: list[dict] = []
        confidence = ocr["confidence"]
        ocr_source = {"source": "ocr", "ocr_confidence": confidence}
        linked_source = {"source": "linked_nlp", "ocr_confidence": confidence}
        visual_source = {"source": "visual", "ocr_confidence": confidence}
        if visual["login_prompt"] and (visual["password_or_otp_prompt"] or visual["form_like_layout"]):
            indicators.append({"reason": "Login form or credential prompt visible", "impact": "high", "value": 1, **visual_source})
        elif visual["password_or_otp_prompt"]:
            indicators.append({"reason": "Password or one-time-code prompt visible", "impact": "medium", "value": 1, **ocr_source})
        if visual["payment_prompt"]:
            indicators.append({"reason": "Payment or financial-information prompt visible", "impact": "high", "value": 1, **ocr_source})
        if visual["urgency_banner"]:
            indicators.append({"reason": "Urgency or account-pressure banner visible", "impact": "medium", "value": 1, **ocr_source})
        brands = [brand for brand in KNOWN_BRANDS if re.search(rf"\b{re.escape(brand)}\b", ocr["text"].lower())]
        if brands:
            indicators.append({"reason": f"Brand claim visible: {', '.join(brands[:3])}", "impact": "low", "value": len(brands), **ocr_source})
        if brands and visual["logo_like_region_count"]:
            indicators.append({"reason": "Brand claim appears with logo-like visual region", "impact": "medium", "value": 1, **visual_source})
        all_links = text_result["urls_found"] + qr_values
        shortened = [link for link in all_links if self._host(link) in SHORTENERS]
        if shortened:
            indicators.append({"reason": "Shortened or obscured link detected", "impact": "medium", "value": len(shortened), "source": "qr" if any(link in qr_values for link in shortened) else "ocr", "ocr_confidence": confidence})
        if qr_values:
            indicators.append({"reason": "QR code detected; destination may conceal its target", "impact": "medium", "value": len(qr_values), "source": "qr", "ocr_confidence": confidence})
        for brand in brands:
            allowed = KNOWN_BRANDS[brand]
            if all_links and not any(
                self._host(link) == domain or self._host(link).endswith("." + domain)
                for link in all_links for domain in allowed
            ):
                indicators.append({"reason": f"Visible {brand.title()} claim does not match extracted link domain", "impact": "high", "value": 1, **linked_source})
                break
        for item in text_result["indicators"]:
            if item["reason"] in {"Credential or validation request", "Financial details or prize solicitation", "Urgency / pressure language", "Potential brand spelling spoofing"}:
                indicators.append({"reason": item["reason"], "impact": item["impact"], "value": item["value"], **linked_source})
        return indicators

    @staticmethod
    def _host(value: str) -> str:
        match = re.search(r"(?:https?://)?([^/:\s]+)", value.lower())
        return match.group(1).removeprefix("www.") if match else ""

    @staticmethod
    def _score(indicators: list[dict]) -> float:
        weights = {"low": 4, "medium": 10, "high": 18}
        raw = sum(weights.get(item["impact"], 0) * min(float(item.get("value", 1)), 2) for item in indicators)
        # Saturating score prevents a repeated OCR phrase from producing certainty.
        return round(min(95, 100 * (1 - np.exp(-raw / 50))), 2)

    @staticmethod
    def _risk(probability: float) -> str:
        if probability < 20: return "Safe"
        if probability < 40: return "Low"
        if probability < 60: return "Medium"
        if probability < 80: return "High"
        return "Critical"

    @staticmethod
    def _empty_text_result() -> dict:
        return {"phishing_probability": 0, "risk": "Unknown", "indicators": [], "urls_found": []}

    @staticmethod
    def _store_sanitized_asset(image: Image.Image, raw: bytes, sha256: str, width: int, height: int, confidence: int | None) -> dict:
        ASSET_DIRECTORY.mkdir(parents=True, exist_ok=True)
        asset_id = str(uuid4())
        object_path = ASSET_DIRECTORY / f"{asset_id}.png"
        image.save(object_path, format="PNG", optimize=True)  # new file has no executable or EXIF metadata
        expiry = datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS)
        create_screenshot_asset(asset_id, None, str(object_path), sha256, len(raw), f"{width}x{height}", confidence, expiry.isoformat())
        return {
            "asset_id": asset_id,
            "object_ref": asset_id,
            # This UUID path names only the newly encoded PNG (never the
            # original upload) and expires with the asset record.
            "preview_path": f"reports/screenshot_assets/{asset_id}.png",
            "hash": sha256,
            "retention_expiry": expiry.isoformat(),
        }
