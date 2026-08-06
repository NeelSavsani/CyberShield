"""Explainable baseline classifier for live URL evidence.

This intentionally consumes only evidence produced by collectors.  It is a
calibrated starting point, not a replacement for a model trained on labelled
phishing and benign samples.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.config import settings


class EvidenceClassifier:
    model_version = "evidence-baseline-v1"
    model_status = "baseline_not_trained"

    def __init__(self) -> None:
        self.trained_model: dict[str, Any] | None = None
        model_path: Path = settings.model_path
        if model_path.exists():
            try:
                candidate = joblib.load(model_path)
                if candidate.get("schema_version") == "evidence-v1":
                    self.trained_model = candidate
            except Exception:
                # A corrupt or incompatible model must never prevent evidence
                # collection; the explainable baseline remains available.
                self.trained_model = None

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        values = features["values"]
        score = -3.0
        contributors: list[dict[str, Any]] = []

        score = self._add(score, contributors, values.get("domain_age_risk"), 1.15, "Recently registered domain")
        score = self._add(score, contributors, values.get("certificate_age_risk"), 0.45, "Recently issued TLS certificate")
        score = self._add(score, contributors, values.get("redirect_count"), 0.15, "Redirect chain", cap=5)
        score = self._add(score, contributors, values.get("cross_domain_form_actions"), 2.1, "Credential form submits to another domain", cap=1)
        score = self._add(score, contributors, values.get("insecure_form_actions"), 1.3, "Form submits over insecure HTTP", cap=1)
        score = self._add(score, contributors, values.get("get_login_forms"), 1.0, "Password form uses GET", cap=1)
        score = self._add(score, contributors, values.get("otp_field_count"), 0.55, "Page requests one-time passcode", cap=1)
        score = self._add(score, contributors, values.get("credit_card_field_count"), 0.35, "Page requests payment-card data", cap=1)
        score = self._add(score, contributors, values.get("hidden_iframe_count"), 0.3, "Hidden iframe present", cap=2)
        score = self._add(score, contributors, values.get("meta_refresh_present"), 0.45, "Meta refresh redirect", cap=1)
        score = self._add(score, contributors, values.get("download_count"), 0.65, "Download initiated during page load", cap=1)
        score = self._add(score, contributors, values.get("permission_request_count"), 0.4, "Browser permission requested", cap=1)
        score = self._add(score, contributors, values.get("obfuscated_script_count"), 0.5, "Obfuscated script detected", cap=2)
        score = self._add(score, contributors, values.get("reputation_detection_count"), 0.75, "Threat-intelligence detections", cap=5)
        score = self._add(score, contributors, values.get("safe_browsing_flagged"), 3.2, "Flagged by Safe Browsing", cap=1)

        probability = round(100 / (1 + math.exp(-score)), 2)
        model_version = self.model_version
        model_status = self.model_status
        notice = "Baseline evidence model. Train and validate a versioned model on labelled data before using this result for automated blocking."
        if self.trained_model:
            columns = self.trained_model["feature_columns"]
            vector = pd.DataFrame(
                [[-1 if values.get(column) is None else values[column] for column in columns]],
                columns=columns,
            )
            probability = round(float(self.trained_model["model"].predict_proba(vector)[0][1]) * 100, 2)
            model_version = "evidence-demo-ml-v1"
            model_status = "trained_demo_model"
            notice = ""
        return {
            "model_version": model_version,
            "model_status": model_status,
            "phishing_probability": probability,
            "risk": self._risk(probability),
            "contributors": sorted(contributors, key=lambda item: item["impact"], reverse=True)[:8],
            "notice": notice,
        }

    @staticmethod
    def _add(score: float, contributors: list[dict[str, Any]], value: Any, weight: float, reason: str, cap: float | None = None) -> float:
        if value is None:
            return score
        magnitude = min(float(value), cap) if cap is not None else float(value)
        impact = magnitude * weight
        if impact > 0:
            contributors.append({"reason": reason, "value": value, "impact": round(impact, 3)})
        return score + impact

    @staticmethod
    def _risk(probability: float) -> str:
        if probability < 20:
            return "Safe"
        if probability < 40:
            return "Low"
        if probability < 60:
            return "Medium"
        if probability < 80:
            return "High"
        return "Critical"
