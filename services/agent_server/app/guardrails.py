from __future__ import annotations

import re

INJECTION_PATTERNS = [
    re.compile(r"ignore (all|previous|prior) instructions", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer message", re.IGNORECASE),
    re.compile(r"tool command", re.IGNORECASE),
    re.compile(r"sudo|rm -rf|drop table", re.IGNORECASE),
]

FRAUD_PATTERNS = [
    re.compile(r"refund without return", re.IGNORECASE),
    re.compile(r"don't follow policy|bypass policy", re.IGNORECASE),
    re.compile(r"pretend it was damaged", re.IGNORECASE),
]

EXFIL_PATTERNS = [
    re.compile(r"dump (the )?database", re.IGNORECASE),
    re.compile(r"show (me )?(all )?(customer|payment) data", re.IGNORECASE),
    re.compile(r"full card number|cvv|social security", re.IGNORECASE),
]

EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*(@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
CARD_PATTERN = re.compile(r"\b\d{12,19}\b")


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_PATTERNS)


def looks_like_fraud_or_exfil(text: str) -> bool:
    patterns = FRAUD_PATTERNS + EXFIL_PATTERNS
    return any(p.search(text) for p in patterns)


def mask_text(text: str) -> str:
    text = EMAIL_PATTERN.sub(r"\1***\2", text)
    text = CARD_PATTERN.sub("[REDACTED_CARD]", text)
    return text
