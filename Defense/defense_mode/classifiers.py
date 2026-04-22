from __future__ import annotations

import re

class KeywordRiskClassifier:
    def score(self, text: str) -> int:
        t = (text or "").lower()
        score = 0
        if "how to" in t:
            score += 10
        if any(x in t for x in ("如何", "怎么", "怎样")):
            score += 10
        if "exploit" in t or "bypass" in t:
            score += 20
        if any(x in t for x in ("绕过", "规避", "越狱", "破解")):
            score += 20
        if "malware" in t or "ransomware" in t:
            score += 20
        if any(x in t for x in ("恶意软件", "勒索软件", "木马", "病毒")):
            score += 20
        if any(x in t for x in ("privilege escalation", "提权", "横向移动", "持久化", "窃取凭证")):
            score += 15
        if re.search(r"step\s*by\s*step|完整(?:步骤|方案)|详细(?:步骤|方案)|逐步|一步一步|直接给我", t, re.I):
            score += 15
        # Intent/action cues commonly used in Chinese harmful requests.
        if any(x in t for x in ("制作", "编写", "搭建", "设立", "开展")) and any(
            x in t for x in ("赌博", "洗钱", "毒品", "爆炸物", "恶意软件", "勒索软件")
        ):
            score += 10

        persona = bool(
            re.search(
                r"扮演|模仿|口吻|语气|角色|设定为|你现在是|你就是|角色扮演|persona|role\s*play",
                t,
                re.I,
            )
        )
        rule_exempt = bool(
            re.search(
                r"不需要遵守|不必遵守|无需遵守|不受.{0,8}(?:限制|规则|约束)|无视.{0,8}(?:规则|政策|法律|道德)|"
                r"不要遵守|不遵守|没有任何限制|可自由表达|直言不讳",
                t,
                re.I,
            )
        )
        harm_intent = bool(
            re.search(
                r"非法|赌博|洗钱|毒品|爆炸物|武器|诈骗|黑客|破解|入侵|攻击|勒索软件|恶意软件|如何设立",
                t,
                re.I,
            )
        )

        if persona:
            score += 5
        if rule_exempt:
            score += 15
        if harm_intent:
            score += 20
        if persona and rule_exempt:
            score += 10
        if rule_exempt and harm_intent:
            score += 15
        if persona and rule_exempt and harm_intent:
            score += 20

        return min(80, score)
