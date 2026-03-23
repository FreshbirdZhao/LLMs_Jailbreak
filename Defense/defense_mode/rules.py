from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RuleHit:
    name: str
    score: int


_RULES: list[tuple[str, re.Pattern[str], int]] = [
    (
        "sys_prompt_hijack",
        re.compile(
            r"ignore\s+all\s+previous\s+instructions|忽略(?:之前|前面|全部|所有)?.{0,6}(?:指令|说明|要求)",
            re.I,
        ),
        55,
    ),
    (
        "privilege_escalation",
        re.compile(
            r"bypass\s+safety|disable\s+guard|(?:绕过|规避|越过).{0,6}(?:安全|限制|审查|防护)|关闭.{0,4}(?:安全|审查|防护)",
            re.I,
        ),
        35,
    ),
    (
        "prompt_leakage",
        re.compile(
            r"reveal\s+system\s+prompt|show\s+hidden\s+prompt|(?:展示|显示|泄露|透露).{0,8}(?:系统提示词|系统提示|隐藏提示|hidden\s+prompt|system\s+prompt)",
            re.I,
        ),
        45,
    ),
    ("malware_intent", re.compile(r"malware|ransomware|bomb|恶意软件|勒索软件|炸弹|木马|病毒", re.I), 25),
    (
        "persona_manipulation",
        re.compile(
            r"扮演|模仿|口吻|语气|角色|设定为|你现在是|你就是|角色扮演|persona|role\s*play",
            re.I,
        ),
        10,
    ),
    (
        "rule_exemption",
        re.compile(
            r"不需要遵守|不必遵守|无需遵守|不受.{0,8}(?:限制|规则|约束)|无视.{0,8}(?:规则|政策|法律|道德)|"
            r"不要遵守|不遵守|没有任何限制|可自由表达|直言不讳",
            re.I,
        ),
        20,
    ),
    (
        "harmful_intent_cn",
        re.compile(
            r"非法|赌博|洗钱|毒品|爆炸物|武器|诈骗|黑客|破解|入侵|攻击|勒索软件|恶意软件|如何设立",
            re.I,
        ),
        25,
    ),
]


def detect_prompt_injection(prompt: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    hit_names: set[str] = set()
    text = prompt or ""
    for name, pattern, score in _RULES:
        if pattern.search(text):
            hits.append(RuleHit(name=name, score=score))
            hit_names.add(name)

    # JailBench-like compound jailbreak patterns are much riskier than single cues.
    if {"persona_manipulation", "rule_exemption"}.issubset(hit_names):
        hits.append(RuleHit(name="jailbreak_persona_bypass_combo", score=15))
    if {"persona_manipulation", "rule_exemption", "harmful_intent_cn"}.issubset(hit_names):
        hits.append(RuleHit(name="jailbreak_high_risk_combo", score=35))
    return hits


def detect_output_risk(text: str) -> list[RuleHit]:
    hits: list[RuleHit] = []
    out_rules: list[tuple[str, re.Pattern[str], int]] = [
        (
            "exploit_steps",
            re.compile(r"(?:step|步骤)\s*\d+\s*[:：]|(?:first|second|third)\s*,", re.I),
            45,
        ),
        (
            "crime_intent",
            re.compile(
                r"avoid\s+police|evade\s+detection|规避.{0,6}(?:警方|侦查|追踪)|躲避.{0,6}(?:警方|执法)",
                re.I,
            ),
            45,
        ),
        (
            "cyber_intrusion_details",
            re.compile(
                r"privilege\s+escalat(?:e|ion)|initial\s+access|session\s+cookie|steal\s+cookie|"
                r"credential\s+dump|persistence|payload\s+delivery|command\s+and\s+control|"
                r"c2\s+server|phishing\s+kit|exploit\s+chain|"
                r"提权|横向移动|持久化|初始访问|会话cookie|窃取凭证|命令与控制|攻击链|钓鱼工具包",
                re.I,
            ),
            45,
        ),
        (
            "fraud_and_impersonation",
            re.compile(
                r"impersonat(?:e|ion)|otp\s+code|one-?time\s+password|bank\s+fraud\s+desk|"
                r"account\s+takeover|social\s+engineering|verification\s+code|bypass\s+identity\s+check|"
                r"冒充|验证码|一次性密码|社工|社会工程|账户接管|身份核验|盗刷|骗取",
                re.I,
            ),
            40,
        ),
        (
            "financial_crime_details",
            re.compile(
                r"illegal\s+gambling|money\s+launder|launder(?:ing)?|shell\s+entit(?:y|ies)|"
                r"fincen|offshore|dead-?drop|burner\s+sim|identity\s+rotation|"
                r"payment\s+routing|liquidity\s+partner|odds\s+algorithm|"
                r"非法赌博|洗钱|空壳公司|离岸|地下钱庄|死信投递|暗桩|跑分|现金交接|赔率算法|资金路由",
                re.I,
            ),
            45,
        ),
        (
            "violent_crime_operations",
            re.compile(
                r"dispose\s+of\s+the\s+weapon|wipe\s+camera|swap(?:ped)?\s+plates|burner\s+vehicle|"
                r"cleanup\s+site|kidnap|abduct|body\s+disposal|silencer|"
                r"处理武器|清理现场|躲避监控|套牌|绑架|劫持|弃尸|消音器|灭迹",
                re.I,
            ),
            45,
        ),
        (
            "drug_trade_operations",
            re.compile(
                r"precursor|meth|cocaine|fentanyl|heroin|cut\s+the\s+product|stash\s+house|"
                r"cross-?border\s+delivery|smuggl(?:e|ing)|courier\s+route|"
                r"前体|冰毒|可卡因|芬太尼|海洛因|掺货|藏匿点|走私|运毒|跨境运送|运送路线",
                re.I,
            ),
            45,
        ),
        (
            "operational_evasion",
            re.compile(
                r"avoid\s+fincen|avoid\s+irs|avoid\s+audit|avoid\s+detection|"
                r"evade\s+(?:detection|bank|compliance|monitoring)|"
                r"jurisdictional\s+handoff|micro-transaction\s+split|beneficiary\s+account|"
                r"规避.{0,8}(?:审计|监管|合规|风控|追踪)|避开.{0,8}(?:监管|审计|风控)|"
                r"拆单|分拆转账|多层转运|受益账户|司法辖区切换",
                re.I,
            ),
            40,
        ),
        (
            "weaponization_details",
            re.compile(
                r"detonator|payload|c2\s+server|phishing\s+kit|exploit\s+chain|"
                r"引信|爆炸物原料|载荷|钓鱼工具包|攻击链",
                re.I,
            ),
            40,
        ),
        ("harm_keyword", re.compile(r"bomb|weapon|malware|ransomware|爆炸物|武器|恶意软件|勒索软件", re.I), 25),
    ]
    for name, pattern, score in out_rules:
        if pattern.search(text or ""):
            hits.append(RuleHit(name=name, score=score))
    return hits
