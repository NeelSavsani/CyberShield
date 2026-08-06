import unittest

from app.services.classifier import EvidenceClassifier
from app.services.feature_extractor import FeatureExtractor
from app.services.url_safety import UnsafeTargetError, ensure_safe_analysis_target


class DecisionPipelineTests(unittest.IsolatedAsyncioTestCase):
    def test_evidence_features_do_not_include_url_string_heuristics(self):
        features = FeatureExtractor().extract({"domain": {"domain_age_days": 8}, "http": {"reachable": True}})

        self.assertEqual(features["schema_version"], "evidence-v1")
        self.assertIn("domain_age_risk", features["values"])
        self.assertNotIn("dot_count", features["values"])
        self.assertNotIn("hyphen_count", features["values"])

    def test_cross_domain_login_evidence_increases_risk(self):
        extractor = FeatureExtractor()
        classifier = EvidenceClassifier()
        benign = classifier.predict(extractor.extract({"http": {"reachable": True}}))
        suspicious = classifier.predict(extractor.extract({
            "domain": {"domain_age_days": 3},
            "http": {"reachable": True, "redirect_count": 3},
            "form": {"password_fields": 1, "cross_domain_actions": 1, "otp_fields": 1},
            "reputation": {"safe_browsing_flagged": True, "detection_count": 3},
        }))

        self.assertGreater(suspicious["phishing_probability"], benign["phishing_probability"])
        self.assertNotEqual(suspicious["risk"], "Safe")

    async def test_localhost_is_rejected(self):
        with self.assertRaises(UnsafeTargetError):
            await ensure_safe_analysis_target("http://127.0.0.1:8000")
