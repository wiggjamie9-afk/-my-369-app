"""Save-time safety filter (Stage 1, rule 5).

Never save: passwords, API keys, caller names, caller phone numbers.

Design: if a candidate memory contains a secret, it is REFUSED (not partly
saved). Phone numbers and labelled caller names are REDACTED, and if nothing
useful is left the save is refused.

Limit (be honest): free-text personal names cannot be detected reliably with
rules. This filter catches labelled names ("caller: Bob", "my name is Bob",
"called by Bob") and every phone-number shape. Stage 2's checker twin (a
different AI model) is the second line of defence for unlabelled names.
"""
from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(pass(word|wd|code)?|pwd|secret|token|api[_ -]?key|auth[_ -]?key)\b\s*(is|=|:)\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),            # OpenAI/Anthropic style
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                 # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),         # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),      # Slack tokens
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),                 # long hex blobs
]

PHONE = re.compile(r"(?<!\w)(\+?\d[\d\s().\-]{7,}\d)(?!\w)")
CALLER_NAME = [
    re.compile(r"(?i)\b(caller|customer|client|contact)(\s+name)?\s*(is|=|:)\s*(?-i:[A-Z][\w'\-]+(\s+[A-Z][\w'\-]+)*)"),
    re.compile(r"(?i)\b(my name is|this is|called by|spoke (to|with)|call from)\s+(?-i:[A-Z][\w'\-]+(\s+[A-Z][\w'\-]+)?)"),
]


class Refused(Exception):
    """The memory must not be saved."""


def sanitize(text: str) -> str:
    """Return text safe to store, or raise Refused."""
    for p in SECRET_PATTERNS:
        if p.search(text):
            raise Refused("contains a password/API key/secret")
    out = PHONE.sub("[phone removed]", text)
    for p in CALLER_NAME:
        out = p.sub("[caller removed]", out)
    stripped = re.sub(r"\[(phone|caller) removed\]", "", out).strip(" .,:;-")
    if not stripped:
        raise Refused("nothing left after removing caller details")
    return out
