import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from app.services.screenshot_analyzer import ScreenshotAnalyzer, ScreenshotValidationError


class ScreenshotAnalyzerTests(unittest.TestCase):
    def _png(self):
        image = Image.new("RGB", (600, 400), "white")
        ImageDraw.Draw(image).rectangle((60, 100, 540, 160), outline="black", width=3)
        stream = io.BytesIO()
        image.save(stream, "PNG")
        return stream.getvalue()

    def test_rejects_non_image_signature(self):
        with self.assertRaises(ScreenshotValidationError):
            ScreenshotAnalyzer().analyze(b"not an image")

    def test_rejects_declared_type_that_does_not_match_signature(self):
        with self.assertRaises(ScreenshotValidationError):
            ScreenshotAnalyzer().analyze(self._png(), declared_content_type="image/jpeg")

    @patch.object(ScreenshotAnalyzer, "_store_sanitized_asset", return_value={"asset_id": "asset", "object_ref": "asset"})
    @patch.object(ScreenshotAnalyzer, "_read_qr", return_value=["https://bit.ly/hidden"])
    @patch.object(ScreenshotAnalyzer, "_ocr", return_value={
        "text": "PayPal Account suspended Enter your username and password Act now",
        "confidence": 93, "words": [], "available": True,
    })
    def test_ocr_and_qr_evidence_has_provenance(self, *_):
        result = ScreenshotAnalyzer().analyze(self._png())
        contributors = result["data"]["classification"]["contributors"]
        self.assertGreater(result["phishing_probability"], 40)
        self.assertTrue(any(item["source"] == "qr" for item in contributors))
        self.assertTrue(any(item["source"] in {"ocr", "visual", "linked_nlp"} for item in contributors))
        self.assertEqual(result["data"]["ocr"]["confidence"], 93)
