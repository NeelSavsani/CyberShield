"""Generate a clearly labelled synthetic evidence dataset for the college demo.

It models observed evidence fields, never URL-string character counts. It is
not a substitute for a real-world benchmark dataset.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from train import FEATURE_COLUMNS


def row(label: int, randomizer: random.Random) -> dict[str, float | int]:
    phishing = bool(label)
    values = {
        "domain_age_risk": randomizer.uniform(.45, 1) if phishing else randomizer.uniform(0, .25),
        "certificate_age_risk": randomizer.uniform(.25, 1) if phishing else randomizer.uniform(0, .3),
        "dnssec_enabled": int(not phishing and randomizer.random() > .35),
        "http_reachable": 1,
        "redirect_count": randomizer.randint(1, 6) if phishing else randomizer.randint(0, 2),
        "has_valid_tls": int(randomizer.random() > (.18 if phishing else .03)),
        "password_field_count": randomizer.randint(0, 2) if phishing else randomizer.choices([0, 1], [8, 2])[0],
        "otp_field_count": randomizer.choices([0, 1], [6, 4])[0] if phishing else 0,
        "credit_card_field_count": randomizer.choices([0, 1], [7, 3])[0] if phishing else 0,
        "cross_domain_form_actions": randomizer.choices([0, 1], [2, 8])[0] if phishing else 0,
        "insecure_form_actions": randomizer.choices([0, 1], [5, 5])[0] if phishing else 0,
        "get_login_forms": randomizer.choices([0, 1], [6, 4])[0] if phishing else 0,
        "hidden_iframe_count": randomizer.randint(0, 3) if phishing else randomizer.choices([0, 1], [9, 1])[0],
        "meta_refresh_present": randomizer.choices([0, 1], [5, 5])[0] if phishing else 0,
        "popup_count": randomizer.randint(0, 2) if phishing else 0,
        "download_count": randomizer.choices([0, 1], [8, 2])[0] if phishing else 0,
        "permission_request_count": randomizer.choices([0, 1], [5, 5])[0] if phishing else randomizer.choices([0, 1], [9, 1])[0],
        "javascript_error_count": randomizer.randint(0, 3) if phishing else randomizer.randint(0, 1),
        "obfuscated_script_count": randomizer.randint(0, 3) if phishing else 0,
        "reputation_detection_count": randomizer.randint(0, 8) if phishing else 0,
        "safe_browsing_flagged": randomizer.choices([0, 1], [4, 6])[0] if phishing else 0,
        "label": label,
    }
    return values


if __name__ == "__main__":
    output = Path(__file__).parents[1] / "datasets" / "demo_evidence.csv"
    output.parent.mkdir(exist_ok=True)
    randomizer = random.Random(20260805)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[*FEATURE_COLUMNS, "label"])
        writer.writeheader()
        for label in (0, 1):
            for _ in range(300):
                writer.writerow(row(label, randomizer))
    print(output)
