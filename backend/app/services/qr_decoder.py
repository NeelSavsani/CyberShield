"""Safe QR decoding for URL-analysis uploads."""

from __future__ import annotations

import numpy as np
import cv2


class QRDecodeError(ValueError):
    """Raised when an uploaded image cannot provide one usable QR value."""


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


def decode_qr_image(raw_image: bytes) -> str:
    """Decode exactly one non-empty QR code from a PNG, JPEG, or WebP image."""
    if not raw_image:
        raise QRDecodeError("Upload a QR code image first.")
    if len(raw_image) > MAX_UPLOAD_BYTES:
        raise QRDecodeError("QR code images must be 5 MB or smaller.")

    image = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise QRDecodeError("The uploaded file is not a supported image.")
    if image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
        raise QRDecodeError("QR code image dimensions are too large.")

    detector = cv2.QRCodeDetector()
    decoded_values: list[str] = []
    try:
        detected, values, _, _ = detector.detectAndDecodeMulti(image)
        if detected:
            decoded_values = [value.strip() for value in values if value and value.strip()]
    except cv2.error:
        # Some OpenCV builds do not support multi-code decoding. Single-code
        # decoding below remains sufficient for this first QR URL workflow.
        pass

    if not decoded_values:
        value, _, _ = detector.detectAndDecode(image)
        if value and value.strip():
            decoded_values = [value.strip()]

    if not decoded_values:
        raise QRDecodeError("No readable QR code was found in this image.")
    if len(decoded_values) != 1:
        raise QRDecodeError("Upload an image containing exactly one QR code.")
    return decoded_values[0]
