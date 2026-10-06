"""Safety gate: every model-written answer is checked before it is shown or spoken.

Checks (PRD "Runtime gate"): format, forbidden advice, verdict consistency, fact check
(rupee amounts must come from the message), allow-listed numbers and links, language.
A failed answer never reaches the user; the caller shows the template answer instead,
and the tests prove every template passes this same gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..fraud.normalize import DEVANAGARI, extract_amounts, extract_urls, fold
from ..fraud.signals import get_engine

MAX_CHARS = 420
ALLOWED_NUMBERS = {"1930", "112", "1600", "1800"}
ALLOWED_HOSTS = {"cybercrime.gov.in", "sancharsaathi.gov.in", "bank.in", "gov.in"}

# Instructions we must never give. Each is checked for negation first, so
# "do not click the link" passes while "click the link" fails.
_FORBIDDEN = [
    ("share_secret", r"(?:share|tell|send|give|batao|bhejo|bata do)\s+(?:\w+\s+){0,3}?(?:otp|pin|password|cvv)"),
    ("share_secret", r"(?:otp|ओटीपी|पिन|पासवर्ड|pin)\s+(?:\S+\s+){0,3}?(?:बताएं|बताइए|बता दें|बताओ|भेजें|शेयर करें)"),
    ("click_link", r"(?:click|tap|open)\s+(?:on\s+)?(?:the\s+|this\s+|that\s+)?link"),
    ("click_link", r"लिंक\s+(?:पर\s+)?(?:क्लिक|टैप)\s+करें"),
    ("install_app", r"(?:install|download)\s+(?:\w+\s+){0,3}?(?:app|apk|anydesk|teamviewer)"),
    ("install_app", r"(?:ऐप|app|एप)\s+(?:\S+\s+){0,2}?(?:डाउनलोड|इंस्टॉल)\s+करें"),
    ("pay_fee", r"pay\s+(?:the\s+)?(?:fee|fees|amount|charges|processing)"),
    ("pay_fee", r"(?:फीस|शुल्क|चार्ज)\s+(?:\S+\s+){0,2}?(?:भरें|दें|जमा करें)"),
    ("scan_qr", r"scan\s+(?:the\s+|this\s+|a\s+)?(?:qr|code)"),
    ("scan_qr", r"(?:qr|क्यूआर)\s+(?:\S+\s+){0,2}?स्कैन\s+करें"),
    ("enter_pin", r"enter\s+(?:your\s+)?(?:upi\s+)?pin"),
    ("enter_pin", r"(?:पिन|pin)\s+(?:\S+\s+){0,2}?डालें"),
]
_FORBIDDEN_RE = [(fid, re.compile(p)) for fid, p in _FORBIDDEN]

# Describing what a scammer wants is fine ("it asks you to share your OTP"); telling the
# person to do it is not. These markers, just before a match, make it a description.
_DESCRIPTIVE = re.compile(
    r"(?:asks?|asking|asked|wants?|wanting|tells?|telling|told|tries|trying|pressur\w*|forces?)\s+(?:you\s+)?(?:to|for)\s*$"
    r"|(?:to\s+make\s+you|get\s+you\s+to)\s*$"
    r"|(?:कहा\s+गया|कहता|कह\s+रहा|कह\s+रहे|माँग|मांग)\S*\s*$"
)


def _is_instruction(engine, text: str, m: re.Match) -> bool:
    if engine.negated(text, m.start(), m.end()):
        return False
    if engine.L["negations_pre"].search(m.group(0)):  # Hindi puts the negation inside: "OTP कभी न बताएं"
        return False
    before = text[max(0, m.start() - 40) : m.start()]
    return not _DESCRIPTIVE.search(before)

# Wording that contradicts a verdict.
_CONTRADICTS = {
    "scam": re.compile(r"not a scam|is safe|it'?s safe|genuine message|no need to worry|सुरक्षित है|ठगी नहीं है|असली मैसेज है|चिंता की कोई बात नहीं"),
    "suspicious": re.compile(r"100% safe|completely safe|definitely genuine|पूरी तरह सुरक्षित"),
    "no_signs": re.compile(r"100% safe|completely safe|definitely genuine|guaranteed safe|पूरी तरह सुरक्षित|पक्का असली"
                           r"|it'?s a scam|is a scam|this is fraud|यह ठगी है|धोखा है"),
}
_DIGIT_RUN = re.compile(r"\d[\d\s-]{3,}\d")
_DEV_LETTER = re.compile(f"[{DEVANAGARI}]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")


@dataclass
class GateResult:
    passed: bool                      # every language passed
    langs: dict[str, bool]            # per language, so one bad language can fall back alone
    checks: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "langs": self.langs, "checks": self.checks}


def _script_ok(lang: str, text: str) -> bool:
    dev, lat = len(_DEV_LETTER.findall(text)), len(_LATIN_LETTER.findall(text))
    if lang == "hi":
        return dev > 0 and dev >= 0.5 * (dev + lat)
    return lat > 0 and dev == 0


# A model saying the message has no number or no link when it plainly does (seen with qwen2.5:3b:
# "no phone number given" about a message asking you to call a mobile number).
_PHONE = re.compile(r"(?:\+91[\s-]?)?(?<!\d)(?:\d[\s-]?){9}\d(?!\d)")
_DENIALS = {
    "number": re.compile(r"\b(?:no|without(?: a| any)?|not (?:give|gave|given|include|includes|mention|mentions)(?: a| any)?)\s+"
                         r"(?:phone\s+|mobile\s+|contact\s+)?(?:number|numbers|contact)\b"
                         r"|कोई\s+(?:फोन\s+|मोबाइल\s+)?नंबर\s+नहीं|नंबर\s+नहीं\s+(?:दिया|है)"),
    "link": re.compile(r"\b(?:no|without(?: a| any)?)\s+(?:web\s+)?(?:link|links|url|website|web address)\b"
                       r"|कोई\s+लिंक\s+नहीं|लिंक\s+नहीं\s+(?:दिया|है)"),
}


def check_texts(texts: dict[str, str], verdict: str, message: str = "",
                max_chars: int | None = MAX_CHARS) -> GateResult:
    """Check model-written text in each language against the message it explains."""
    engine = get_engine()
    message_amounts = extract_amounts(fold(message)) if message else []
    message_has = {"number": bool(_PHONE.search(message)), "link": bool(message and extract_urls(fold(message)))}
    checks: list[dict[str, Any]] = []
    langs: dict[str, bool] = {}

    for lang in ("en", "hi"):
        raw = texts.get(lang)
        failed: list[str] = []

        def record(check_id: str, ok: bool, detail: str = "") -> None:
            checks.append({"id": check_id, "lang": lang, "passed": ok, "detail": detail})
            if not ok:
                failed.append(check_id)

        ok_format = isinstance(raw, str) and bool(raw.strip()) and (max_chars is None or len(raw) <= max_chars)
        record("format", ok_format)
        text = fold(raw or "")

        hits = sorted({fid for fid, rx in _FORBIDDEN_RE for m in rx.finditer(text)
                       if _is_instruction(engine, text, m)})
        record("forbidden_advice", not hits, ", ".join(hits))

        record("verdict_consistency", not _CONTRADICTS[verdict].search(text))

        stray = []
        for m in _DIGIT_RUN.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if digits not in ALLOWED_NUMBERS and len(digits) >= 5:
                stray.append(digits)
        for u in extract_urls(text):
            if u.host not in ALLOWED_HOSTS and not u.host.endswith((".gov.in", ".bank.in")):
                stray.append(u.host)
        record("allow_list", not stray, ", ".join(stray[:5]))

        invented = [f"{a:g}" for a in extract_amounts(text) if not any(abs(a - b) < 0.5 for b in message_amounts)]
        denied = [what for what, rx in _DENIALS.items() if message_has[what] and rx.search(text)]
        record("fact_check", not invented and not denied, ", ".join(invented + [f"says there is no {d}" for d in denied]))

        record("language", _script_ok(lang, raw or ""))
        langs[lang] = not failed

    return GateResult(passed=all(langs.values()), langs=langs, checks=checks)


def check_card_text(card: dict[str, Any], message: str = "") -> GateResult:
    """Run the gate over a template card's headline and actions (reasons quote evidence)."""
    texts = {lang: " ".join([card["headline"][lang], *card["actions"][lang]]) for lang in ("en", "hi")}
    return check_texts(texts, card["verdict"], message, max_chars=None)
