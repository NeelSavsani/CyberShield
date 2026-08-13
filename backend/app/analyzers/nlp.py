"""Explainable phishing heuristics for email and message text."""
import math
import re


class TextAnalyzer:
    RULES = [
        ("urgency_match_count", "Urgency / pressure language", 1.2, [r"\bhurry\b", r"\bimmediate(ly)?\b", r"\burgent(ly)?\b", r"\baction required\b", r"\bact now\b", r"\bsuspended\b", r"\bcompromised\b", r"\bdeactivated\b", r"\bblocked\b", r"\blast warning\b", r"\bfinal notice\b", r"\bpay now\b", r"\bexpiration\b", r"\bexpire\b", r"\bwithin \d+ hours\b", r"\bterminate\b"]),
        ("threat_match_count", "Threat or litigation keywords", 1.5, [r"\bsecurity alert\b", r"\bsuspicious activity\b", r"\bsecurity breach\b", r"\blawsuit\b", r"\bprosecution\b", r"\barrest\b", r"\bcourt\b", r"\bpenalty\b", r"\bfine\b", r"\bpolice\b", r"\birs\b", r"\btax fraud\b"]),
        ("credential_match_count", "Credential or validation request", 1.6, [r"\bpassword\b", r"\busername\b", r"\blogin\b", r"\bcredentials\b", r"\bverify (your )?account\b", r"\bupdate (your )?profile\b", r"\bpasscode\b", r"\bpin number\b", r"\bssn\b", r"\bsocial security\b", r"\bsecurity question\b"]),
        ("financial_match_count", "Financial details or prize solicitation", 1.3, [r"\bbank account\b", r"\bcredit card\b", r"\bdebit card\b", r"\brouting number\b", r"\bwire transfer\b", r"\bpayment details\b", r"\binvoice details\b", r"\bbilling information\b", r"\brefund\b", r"\bwin prize\b", r"\blottery\b", r"\bclaim reward\b", r"\bcash prize\b", r"\btransaction id\b"]),
        ("brand_mention_count", "Known brand mentions", 0.4, [r"\bpaypal\b", r"\bnetflix\b", r"\bmicrosoft\b", r"\bgoogle\b", r"\bamazon\b", r"\bapple\b", r"\bpaytm\b", r"\bmeta\b", r"\bfacebook\b", r"\bchase\b", r"\bwellsfargo\b"]),
        ("spoof_match_count", "Potential brand spelling spoofing", 2.5, [r"\bpaypa[iI1]\b", r"\bnetfl[iI1]x\b", r"\bm[i1]crosoft\b", r"\bfaceb[o0][o0]k\b", r"\bamaz[o0]n\b", r"\bappl[e3]\b"]),
    ]

    def analyze(self, text: str):
        if not text or not text.strip():
            return {"success": False, "error": "Empty text provided."}
        text = text.strip()
        lower = text.lower()
        urls = []
        for match in re.findall(r'(https?://[^\s<>"}]+|www\.[^\s<>"}]+)', text):
            value = match.rstrip(".,;)!?\"'")
            if value not in urls:
                urls.append(value)
        features = {"url_count": len(urls), "has_links": bool(urls)}
        indicators = []
        score = -3.0
        counts = {}
        for feature, reason, weight, patterns in self.RULES:
            count = sum(len(re.findall(pattern, lower)) for pattern in patterns)
            counts[feature] = count
            score += count * weight
            if count:
                impact = "high" if count * weight >= 2.5 else "medium" if count * weight >= 1.2 else "low"
                indicators.append({"reason": reason, "impact": impact, "value": count})
        features.update(counts)
        if counts["brand_mention_count"] and (counts["urgency_match_count"] or urls or counts["credential_match_count"]):
            score += counts["brand_mention_count"] * 1.1
        score += 1.0 if urls else 0.0
        probability = round(100 / (1 + math.exp(-score)), 2)
        risk = "Critical" if probability >= 80 else "High" if probability >= 60 else "Medium" if probability >= 40 else "Low" if probability >= 20 else "Safe"
        return {"success": True, "text": text, "phishing_probability": probability, "risk": risk, "indicators": indicators, "features": features, "urls_found": urls}
