from __future__ import annotations


class KeywordRiskClassifier:
    def score(self, text: str) -> int:
        t = (text or "").lower()
        score = 0
        if "how to" in t:
            score += 10
        if "exploit" in t or "bypass" in t:
            score += 20
        if "malware" in t or "ransomware" in t:
            score += 20
        return min(40, score)

