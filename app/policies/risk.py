import re
from dataclasses import dataclass
from dataclasses import field
from typing import List


HIGH_RISK_TERMS = (
    "人工",
    "投诉",
    "举报",
    "退款",
    "重复扣费",
    "重复收费",
    "多扣费",
    "乱收费",
    "支付异常",
    "扣款异常",
    "发票问题",
    "车辆损坏",
    "刮擦",
    "碰撞",
    "事故",
    "受伤",
    "火灾",
    "急救",
    "失物",
    "物品丢失",
    "车辆被盗",
    "法律责任",
    "律师",
    "隐私泄露",
    "账号安全",
    "human agent",
    "complaint",
    "refund",
    "double charge",
    "payment dispute",
    "accident",
    "injury",
    "vehicle damage",
    "fire",
    "lost item",
    "stolen",
    "legal",
)

UNCONFIRMED_ACTION_PATTERNS = (
    re.compile(
        r"已(?:经)?(?:完成|成功|为您)?"
        r"(?:预约|预订|取消|退款|支付|锁(?:定|住)?车位|开闸|通知人工)"
    ),
    re.compile(
        r"(?:预约|退款|支付|锁车位|开闸|通知人工)"
        r"(?:已经|已)?(?:完成|成功)"
    ),
    re.compile(
        r"(?:has been|have been) "
        r"(?:booked|reserved|cancelled|refunded|paid|unlocked)",
        re.IGNORECASE,
    ),
)

SENSITIVE_PATTERNS = (
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"(?<!\d)(?:\d[ -]?){16}(?!\d)"),
)


@dataclass
class RiskAssessment:
    requires_human: bool = False
    risk_level: str = "low"
    reasons: List[str] = field(default_factory=list)


def assess_request_risk(question: str, response: str = "") -> RiskAssessment:
    """Apply deterministic minimum-risk rules before model-based review."""
    normalized_question = (question or "").lower()
    normalized_response = response or ""
    reasons = []

    matched_terms = [
        term for term in HIGH_RISK_TERMS
        if term.lower() in normalized_question
    ]
    if matched_terms:
        reasons.append(
            "请求涉及高风险场景：" + "、".join(matched_terms[:4])
        )

    if any(
        pattern.search(normalized_response)
        for pattern in UNCONFIRMED_ACTION_PATTERNS
    ):
        reasons.append("答复声称已完成业务操作，但系统没有真实执行结果")

    if any(
        pattern.search(normalized_question)
        for pattern in SENSITIVE_PATTERNS
    ):
        reasons.append("用户消息包含不应进入普通问答流程的敏感信息")

    if not reasons:
        return RiskAssessment()

    return RiskAssessment(
        requires_human=True,
        risk_level="high",
        reasons=reasons,
    )
