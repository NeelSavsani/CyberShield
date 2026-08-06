"""Train a versioned evidence model from a labelled CSV dataset.

Usage: python ml/train.py datasets/labelled_evidence.csv models/phishing_model.joblib
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

FEATURE_COLUMNS = [
    "domain_age_risk", "certificate_age_risk", "dnssec_enabled", "http_reachable",
    "redirect_count", "has_valid_tls", "password_field_count", "otp_field_count",
    "credit_card_field_count", "cross_domain_form_actions", "insecure_form_actions",
    "get_login_forms", "hidden_iframe_count", "meta_refresh_present", "popup_count",
    "download_count", "permission_request_count", "javascript_error_count",
    "obfuscated_script_count", "reputation_detection_count", "safe_browsing_flagged",
]


def main(input_file: str, output_file: str) -> None:
    frame = pd.read_csv(input_file)
    missing = set(FEATURE_COLUMNS + ["label"]) - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    x = frame[FEATURE_COLUMNS].fillna(-1)
    y = frame["label"]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.2, random_state=42, stratify=y)
    # This deterministic single-process model works in constrained lab systems
    # and remains easy to explain in a college presentation.
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1_000, solver="liblinear", random_state=42))
    model.fit(x_train, y_train)
    probability = model.predict_proba(x_test)[:, 1]
    report = {"roc_auc": roc_auc_score(y_test, probability), "classification_report": classification_report(y_test, model.predict(x_test), output_dict=True)}
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": FEATURE_COLUMNS, "metrics": report, "schema_version": "evidence-v1"}, output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
