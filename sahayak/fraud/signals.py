"""Fraud-Shield signal layer: deterministic, explainable checks.

Each detector reads the folded text and the extracted parts (links, numbers, amounts)
and fires named signals defined in the fraud pack. A fired signal carries its weight,
whether it is hard (forces a Scam verdict), and the evidence that fills its reason
sentence. No model is called here; a message is checked in about a millisecond.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from ..packs import get_pack
from .normalize import DEVANAGARI, Context, _MOBILE_RE, fold

_DEV = re.compile(f"[{DEVANAGARI}]")
_CLAUSE_BREAK = re.compile(r"[,;:.!?।\n]")
_SENTENCE_BREAK = re.compile(r"[!?।\n]|\.(?:\s|$)")
# digits right after a mask ("XX4421", "**4421") are a hidden card or account number, never a code
_CODE_DIGITS = re.compile(r"(?<![\dxX*•])\d{4,8}(?!\d)")
_HELPLINE_NUMBERS = {"1930", "1800", "1600"}


def _has_code(text: str) -> bool:
    """A 4-8 digit one-time code, not a helpline number or one the reader is told to call."""
    for m in _CODE_DIGITS.finditer(text):
        if m.group(0) in _HELPLINE_NUMBERS:
            continue
        if re.search(r"(call|dial|on|कॉल)\W{0,3}$", text[max(0, m.start() - 8) : m.start()]):
            continue
        return True
    return False


def _alt(phrases: list[str]) -> str:
    words = {r"\s+".join(re.escape(w) for w in p.split()) for p in phrases}
    return "|".join(sorted(words, key=len, reverse=True))  # longest first


class Lexicon:
    """A phrase list compiled to one regex.

    Latin phrases match whole words. Devanagari phrases need a left boundary, and a right
    boundary too when short (<= 3 chars, e.g. the negation 'न'), so inflected forms of
    longer Hindi words still match.
    """

    def __init__(self, phrases: list[str]):
        latin, dev_short, dev_long = [], [], []
        for p in phrases:
            fp = fold(p)
            if not fp:
                continue
            if _DEV.search(fp):
                (dev_short if len(fp) <= 3 else dev_long).append(fp)
            else:
                latin.append(fp)
        parts = []
        if latin:
            parts.append(rf"(?<![a-z0-9])(?:{_alt(latin)})(?![a-z0-9])")
        if dev_long:
            parts.append(rf"(?<![{DEVANAGARI}])(?:{_alt(dev_long)})")
        if dev_short:
            parts.append(rf"(?<![{DEVANAGARI}])(?:{_alt(dev_short)})(?![{DEVANAGARI}])")
        self._re = re.compile("|".join(parts)) if parts else None

    def finditer(self, text: str) -> list[re.Match]:
        return list(self._re.finditer(text)) if self._re else []

    def search(self, text: str, pos: int = 0, endpos: int | None = None) -> re.Match | None:
        """Search a window of `text` while word boundaries still see the full text, so a
        window that starts mid-word ('...ना' cut from 'पुराना') is not read as a word."""
        if not self._re:
            return None
        return self._re.search(text, pos, len(text) if endpos is None else endpos)


@dataclass
class Fired:
    id: str
    weight: float
    hard: bool
    evidence: dict[str, str] = field(default_factory=dict)


def _gap(a: re.Match, b: re.Match) -> int:
    """Characters between two matches (0 if they overlap)."""
    if a.end() <= b.start():
        return b.start() - a.end()
    if b.end() <= a.start():
        return a.start() - b.end()
    return 0


def _near(xs: list[re.Match], ys: list[re.Match], window: int) -> bool:
    return any(_gap(x, y) <= window for x in xs for y in ys)


def _clause_start(text: str, pos: int) -> int:
    start = 0
    for m in _CLAUSE_BREAK.finditer(text, 0, pos):
        start = m.end()
    return start


def _sentence(text: str, start: int, end: int) -> str:
    s0 = 0
    for m in _SENTENCE_BREAK.finditer(text, 0, start):
        s0 = m.end()
    m = _SENTENCE_BREAK.search(text, end)
    return text[s0 : m.start() if m else len(text)]


# Phrases that look like requests but are routine in genuine messages: you hand a code to
# the delivery agent or the cab driver standing in front of you.
_OTP_OK_CONTEXT = re.compile(
    r"(?<![a-z])(delivery|deliver|driver|captain|ride|trip|cab|pickup|technician|डिलीवरी|ड्राइवर)")
# A message that contains the code itself is delivering it; a fraudster does not know your code.
_CODE_NEXT_TO_TERM = re.compile(
    r"(?:otp|pin|code|ओटीपी|कोड)\D{0,12}(?<![\dx*•])\d{4,8}(?!\d)|(?<![\dx*•])\d{4,8}(?!\d)\D{0,12}(?:otp|pin|code|ओटीपी|कोड)")
_PIN_CODE = re.compile(r"\s*(?:-|\s)?code")
_UPI_RECEIVE_PATTERNS = [re.compile(p) for p in (
    r"(?:scan|स्कैन)\W+(?:\w+\W+){0,5}?(?:qr|क्यूआर|code|कोड)\W+(?:\w+\W+){0,8}?(?:receive|get|claim|credit|refund|cashback|paane|pane|lene|milega|पाने|प्राप्त|पाएं|लेने)",
    r"(?:enter|daal|dal|daalo|dalo|डाल|डालें|डालो)\W+(?:\w+\W+){0,4}?(?:upi\s*pin|pin|पिन)\W+(?:\w+\W+){0,8}?(?:receive|get|claim|credit|refund|cashback|paane|pane|पाने|प्राप्त)",
    # Hindi word order: "PIN डालो, तब पैसे मिलेंगे" (the verb after PIN, the money after that)
    r"(?:upi\s*pin|pin|पिन)\W+(?:daalo|dalo|daal|dal|daliye|dalna|enter|डालो|डालें|डालिए|डालना)\W+(?:\w+\W+){0,6}?(?:milenge|milega|mil\s+jayenge|mil\s+jayega|aayenge|aa\s+jayenge|मिलेंगे|मिलेगा|मिल\s+जाएंगे|आ\s+जाएंगे|receive|credit)",
    r"(?:receive|get|claim)\W+(?:\w+\W+){0,6}?(?:money|payment|amount|refund|cashback|rs|₹)\W+(?:\w+\W+){0,6}?(?:enter|scan)\W+(?:\w+\W+){0,3}?(?:upi\s*pin|pin|qr)",
    r"(?:collect request|payment request|request money|money request)\W+(?:\w+\W+){0,10}?(?:approve|accept|स्वीकार)",
    r"(?:approve|accept|स्वीकार)\W+(?:\w+\W+){0,5}?(?:request|रिक्वेस्ट)\W+(?:\w+\W+){0,8}?(?:receive|get|refund|cashback|paane|पाने|प्राप्त)",
    r"(?:पैसे|पैसा|रकम|रुपये)\s+(?:पाने|लेने)\s+के\s+लिए\s+(?:\S+\s+){0,3}?(?:पिन|क्यूआर|qr|स्कैन)",
    r"(?:paise|paisa)\s+(?:paane|pane|lene)\s+ke\s+liye\s+(?:\S+\s+){0,3}?(?:pin|qr|scan)",
    r"(?:राशि|पैसे|पैसा|रकम|रुपये)\s+(?:प्राप्त|पाने|लेने)\s+(?:करने\s+)?के\s+लिए\s+(?:\S+\s+){0,6}?(?:पिन|क्यूआर|qr|स्कैन)",
)]
# The collect-request trick: "to reverse it, approve the request we sent you", "I sent Rs 5000 by mistake,
# accept the request and return it". Approving a UPI request sends money out; it never reverses or refunds
# anything. Only the instruction counts ("approve", "accept kar do"), never a report ("request accepted").
_COLLECT_VERB = re.compile(r"(?<![a-z])(?:approve|accept)(?![a-z])|स्वीकार|अप्रूव")
_COLLECT_WHY = re.compile(r"reverse|return|refund|mistake|galti|wapas|vapas|गलती|वापस|रिफंड|लौटा")
_COLLECT_REQUEST = [(re.compile(p), why) for p, why in (
    # instruction, then why: "accept the request on PhonePe and return it"
    (r"(?<![a-z])(?:approve|accept)(?![a-z])\W+(?:\w+\W+){0,4}?(?:requests?|रिक्वेस्ट)(?![a-z])(?:\W+\w+){0,10}?\W+"
     r"(?:reverse|return|refund|back|wapas|vapas|वापस|mistake|galti|गलती)", False),
    # why, then instruction: "to reverse it approve the request", "by mistake, please accept the request"
    (r"(?:reverse|return|refund|mistake|galti|wapas|vapas|गलती|वापस)\W+(?:\w+\W+){0,8}?(?<![a-z])(?:approve|accept)(?![a-z])"
     r"\W+(?:\w+\W+){0,3}?(?:requests?|रिक्वेस्ट)(?![a-z])", False),
    # Hindi word order: "रिक्वेस्ट स्वीकार करें", "request accept kar do" (with a why anywhere in the message)
    (r"(?:requests?|रिक्वेस्ट|अनुरोध)\W+(?:\S+\s+){0,2}?(?:(?:approve|accept)\s+(?:kar\s*do|karo|karein|karen|kar\s+dein|kijiye)"
     r"|(?:स्वीकार|अप्रूव)\s+(?:करें|करो|कर\s+दें|कर\s+दो|कीजिए))", True),
)]
_WALLET_TERMS = re.compile(r"(?<![a-z])(?:paytm|phonepe|phone pe|google pay|gpay|bhim|wallet|deduct\w*|debit\w*)(?![a-z])")
# Sending money, for scheme_fee: "500 रुपये इस नंबर पर भेजें", "is UPI par 299 bhejo", "pay Rs 100 to this number".
_SEND_MONEY = re.compile(
    r"(?<![a-z])(?:send|pay|transfer|bhejo|bhejein|bhejen|bhej\s+do|bhejiye|jama\s+karo|jama\s+karein|jama\s+kare)(?![a-z])"
    r"|(?:भेजें|भेजो|भेज\s+दें|भेज\s+दो|भेजिए|जमा\s+करें|जमा\s+करो|भुगतान\s+करें)(?![ऀ-ॿ])")
# Pay (or send) money first to receive, release, withdraw or settle something.
_PAY_FIRST = re.compile(
    r"(?:pay|paying|send|deposit|bharo|bharna|jama)\s+(?:\w+\s+){0,5}?(?:tax|gst|fee|fees|charge|charges|duty|deposit|"
    r"advance|amount)\b(?:\W+\w+){0,8}?\W+(?:first|to withdraw|to release|to claim|to receive|to activate|to settle|"
    r"before|to avoid|or face)\b"
    r"|(?:send|pay)\s+(?:rs\.?|₹|inr)?\s?\d[\d,]*(?:/-)?\s+(?:as\s+)?(?:gst|tax|fee|fees|charges?|deposit|advance)\b"
    r"|(?:to\s+withdraw|withdrawal)\W+(?:\w+\W+){0,4}?pay\b"
    r"|(?:security|settlement|verification|clearance)\s+(?:amount|fee|charge|deposit)"
)
_HI_FEE_SEND = re.compile(r"(?:शुल्क|फीस|चार्ज)\s+(?:\S+\s+){0,5}?(?:भेजें|भरें|जमा\s+करें|दें|भेजो|भरो)")
_COURIER_FEE = re.compile(r"(?:pay|send)\s+(?:the\s+)?(?:delivery|customs|clearance|courier|shipping)\s+(?:fee|fees|charges?|duty)")
_SHARE_TO_CONTACTS = re.compile(
    r"(?:send|sent|share|shared|forward|upload)\w*\s+(?:\w+\s+){0,3}?(?:to\s+)?(?:all\s+)?(?:your\s+)?"
    r"(?:contacts|relatives|family|friends)")
_PRIZE_EXCLUDE = re.compile(r"reward\s+points|loyalty\s+points|earned\s+\d+\s+points|cashback\s+points")
_NO_FEE = re.compile(r"(?:\bno|without|zero|free|बिना|कोई)\s+$")  # "No registration fee", "बिना शुल्क"
_EARN_RATE = re.compile(r"earn\w*\s+(?:upto\s+|up to\s+)?(?:rs\.?|₹|inr)?\s?\d[\d,]*\s*(?:/-)?\s*(?:per day|daily|/day|a day|per hour|per task|weekly|per week)")
_RETURN_PCT = re.compile(r"(?<!\d)\d{2,4}\s?%\s*(?:return|returns|profit|munafa|मुनाफ)")
_PAY_TO_GET = re.compile(r"pay\s+(?:only\s+)?(?:rs\.?|₹|inr)?\s?\d[\d,]*(?:/-)?\s+(?:only\s+)?(?:to|for|and)\s+(?:receive|get|claim|release|unlock|activate|process|withdraw)")
_HI_FEE_FIRST = re.compile(r"(?:पहले|pehle)\s+(?:\S+\s+){0,4}?(?:फीस|शुल्क|चार्ज|fee|fees|charge)")
_APK_TEXT = re.compile(r"\.apk\b|\bapk\s+(?:file|download|link)")
_JOIN_GROUP = re.compile(
    r"\bjoin\W+(?:\w+\W+){0,5}?(?:group|channel)\b"
    r"|\b(?:group|channel)\W+(?:\w+\W+){0,2}?(?:on\s+)?(?:telegram|whatsapp)\b"
    r"|\b(?:telegram|whatsapp)\W+(?:\w+\W+){0,2}?(?:group|channel)\b"
)


class SignalEngine:
    def __init__(self, pack: dict[str, Any]):
        self.defs = pack["signals"]
        self.L = {name: Lexicon(phrases) for name, phrases in pack["lexicons"].items()}
        d = pack["domains"]
        self.shorteners = set(d["shorteners"])
        self.suspicious_tlds = set(d["suspicious_tlds"])
        self.official_suffixes = tuple(d["official_suffixes"])
        self.official_domains = set(d["official_domains"])
        self.brand_tokens = sorted(d["brand_tokens"], key=len, reverse=True)

    # ------------------------------------------------------------ helpers

    def is_official(self, host: str) -> bool:
        if host.endswith(self.official_suffixes):
            return True
        return any(host == d or host.endswith("." + d) for d in self.official_domains)

    def brand_in_host(self, host: str) -> str | None:
        labels = host.split(".")[:-1]
        for label in labels:
            for part in label.split("-"):
                for token in self.brand_tokens:
                    if part == token or part.startswith(token) or (len(token) >= 4 and part.endswith(token)):
                        return token
        return None

    def negated(self, text: str, start: int, end: int) -> bool:
        lo = max(start - 28, _clause_start(text, start))
        if self.L["negations_pre"].search(text, lo, start):
            return True
        cut = _CLAUSE_BREAK.search(text, end, end + 14)
        return bool(self.L["negations_post"].search(text, end, cut.start() if cut else min(len(text), end + 14)))

    def negated_in_sentence(self, text: str, m: re.Match) -> bool:
        """A negation anywhere earlier in the same sentence ('Do not install apps like AnyDesk')."""
        s0 = 0
        for b in _SENTENCE_BREAK.finditer(text, 0, m.start()):
            s0 = b.end()
        return bool(self.L["negations_pre"].search(text, s0, m.start()))

    def advisory_context(self, text: str, m: re.Match) -> bool:
        """True when the match sits in a warning sentence ('police never do digital arrest')."""
        return bool(self.L["advisory"].search(_sentence(text, m.start(), m.end()))) or self.negated(text, m.start(), m.end())

    # ------------------------------------------------------------ detection

    def run(self, ctx: Context) -> list[Fired]:
        n, L = ctx.norm, self.L
        fired: dict[str, Fired] = {}

        def fire(sid: str, **evidence: str) -> None:
            if sid not in fired:
                spec = self.defs[sid]
                fired[sid] = Fired(sid, float(spec["weight"]), bool(spec.get("hard")), evidence)

        org_bank = bool(L["bank_terms"].search(n))
        org_claim = org_bank or bool(L["authority_terms"].search(n))
        links = [u for u in ctx.urls if u.host not in ("wa.me", "api.whatsapp.com")]
        nonofficial = [u for u in links if not self.is_official(u.host)]
        official = [u for u in links if self.is_official(u.host)]
        share_verbs = [v for v in L["share_verbs"].finditer(n) if not self.negated(n, v.start(), v.end())]

        # --- requests for secrets
        secrets = L["otp_terms"].finditer(n) + L["code_phrases"].finditer(n)
        secrets += [m for m in L["pin_terms"].finditer(n) if not _PIN_CODE.match(n, m.end())]
        for v in share_verbs:
            if not any(_gap(v, t) <= 60 for t in secrets):
                continue
            sentence = _sentence(n, v.start(), v.end())
            routine = _OTP_OK_CONTEXT.search(sentence) or _CODE_NEXT_TO_TERM.search(n)
            if routine and not nonofficial and ctx.input_type != "call":
                continue  # "share OTP 4417 with the driver" delivers a code; it does not ask for one
            fire("otp_request", phrase=_snippet(n, v))
            break
        personal = L["personal_info_terms"].finditer(n)
        if any(_gap(v, p) <= 50 for v in share_verbs for p in personal):
            fire("personal_info_request")
        for pat in _UPI_RECEIVE_PATTERNS:
            m = pat.search(n)
            # also reject a negation inside the match: "to receive money you never need to enter your PIN",
            # and a warning about the trick: "fraudsters ask you to scan QR codes for refunds"
            if (m and not self.negated(n, m.start(), m.end()) and not self.L["negations_pre"].search(n, m.start(), m.end())
                    and not self.L["advisory"].search(_sentence(n, m.start(), m.end()))):
                fire("upi_receive", phrase=m.group(0)[:60])
                break
        if "upi_receive" not in fired and (L["money_terms"].search(n) or ctx.amounts or ctx.upi_ids or _WALLET_TERMS.search(n)):
            for pat, needs_why in _COLLECT_REQUEST:
                m = pat.search(n)
                if not m or (needs_why and not _COLLECT_WHY.search(n)):
                    continue
                verb = _COLLECT_VERB.search(n, m.start(), m.end())
                # negation is checked at the verb: "never approve a request" is advice, while "if you did
                # not make this payment, approve the request to reverse it" is still the trick
                if verb and not self.advisory_context(n, verb):
                    fire("upi_receive", phrase=m.group(0)[:60])
                    break

        # --- links
        for u in nonofficial:
            path = u.path.lower()
            if path.endswith(".apk") or ".apk" in path or u.host.endswith(".apk"):
                fire("link_apk", domain=u.host)
            if u.is_ip:
                fire("link_ip", domain=u.host)
            if u.host in self.shorteners:
                fire("link_shortener", domain=u.host)
            if u.tld in self.suspicious_tlds:
                fire("link_suspicious_tld", domain=u.host)
            if self.brand_in_host(u.host):
                fire("link_lookalike", domain=u.host)
            elif org_bank:
                fire("link_bank_unofficial", domain=u.host)
            fire("link_present", domain=u.host)
        apk = _APK_TEXT.search(n)
        if apk and not self.negated(n, apk.start(), apk.end()):
            fire("link_apk", domain=apk.group(0))
        if links and not nonofficial:
            fire("official_link", domain=official[0].host)

        # --- who sent it
        if ctx.sender_kind == "mobile" and org_claim:
            fire("call_mobile_claims_org" if ctx.input_type == "call" else "sender_mobile_claims_org", sender=ctx.sender or "")
        elif ctx.sender_kind == "dlt":
            fire("dlt_sender", sender=ctx.sender or "")
        elif ctx.sender_kind == "1600":
            fire("bank_1600_caller", sender=ctx.sender or "")

        # --- personal mobile numbers to call
        number_spans = list(_MOBILE_RE.finditer(n))
        calls = L["call_verbs"].finditer(n)
        wa_link = any(u.host in ("wa.me", "api.whatsapp.com") for u in ctx.urls)
        contact = None
        for m in number_spans:
            if any(_gap(m, c) <= 40 for c in calls) or "whatsapp" in n:
                contact = re.sub(r"\D", "", m.group(1))
                break
        if contact is None and wa_link and ctx.mobiles:
            contact = ctx.mobiles[0]
        if contact:
            fire("contact_mobile", number=contact)
            if org_claim:
                fire("org_contact_mobile", number=contact)
            if L["debit_credit_terms"].search(n):
                fire("fake_alert_callback", number=contact)
        if L["customer_care_terms"].search(n) and ctx.mobiles:
            fire("customer_care_bait", number=ctx.mobiles[0])

        # --- pressure and threats
        m = L["urgency"].search(n)
        if m:
            fire("urgency", phrase=m.group(0))
        for m in L["digital_arrest"].finditer(n):
            if not self.advisory_context(n, m):
                fire("digital_arrest")
                break
        for m in L["threat_terms"].finditer(n):
            if not self.advisory_context(n, m):
                fire("threat_authority", phrase=m.group(0))
                break
        couriers, seized = L["courier_terms"].finditer(n), L["seized_terms"].finditer(n)
        if couriers and seized and _near(couriers, seized, 80) and not self.advisory_context(n, seized[0]):
            fire("courier_seized")
        if L["secrecy"].search(n):
            fire("secrecy")

        # --- money bait
        if not _PRIZE_EXCLUDE.search(n):
            for m in L["prize"].finditer(n):
                if not self.advisory_context(n, m):
                    fire("prize")
                    break
        easy = {m.group(0) for m in L["easy_money"].finditer(n)}
        if len(easy) >= 2 or _EARN_RATE.search(n):
            fire("easy_money")
        elif easy:
            fire("easy_money_weak")
        if L["investment"].search(n) or _RETURN_PCT.search(n):
            fire("investment_promise")
        if (L["join_group"].search(n) or _JOIN_GROUP.search(n)
                or any(u.host in ("t.me", "chat.whatsapp.com") for u in ctx.urls)):
            fire("join_group")
        pay_first = _PAY_FIRST.search(n)
        fee_terms = [m for m in L["advance_fee"].finditer(n)
                     if not self.negated(n, m.start(), m.end()) and not _NO_FEE.search(n[max(0, m.start() - 10) : m.start()])]
        if (fee_terms or _PAY_TO_GET.search(n) or _HI_FEE_FIRST.search(n) or _HI_FEE_SEND.search(n)
                or (pay_first and not self.negated(n, pay_first.start(), pay_first.end()))
                or (_COURIER_FEE.search(n) and (L["courier_terms"].search(n) or "gift" in n))):
            fire("advance_fee")
        if L["loan"].search(n):
            fire("loan_offer")

        # --- impersonation stories
        kyc, kyc_threat = L["kyc_terms"].finditer(n), L["kyc_threat_terms"].finditer(n)
        if kyc and kyc_threat and _near(kyc, kyc_threat, 60):
            if nonofficial or ctx.mobiles:
                fire("kyc_threat")
            elif not L["branch_visit"].search(n):
                fire("kyc_mention")
        elec, cut = L["electricity_terms"].finditer(n), L["disconnect_terms"].finditer(n)
        if elec and cut and _near(elec, cut, 60) and (L["tonight_terms"].search(n) or ctx.mobiles):
            fire("electricity_cut")
        if L["family_terms"].search(n) and L["emergency_terms"].search(n) and L["money_send_terms"].search(n):
            fire("relative_emergency")
        if L["new_number"].search(n):
            fire("new_number")
        if L["sim_terms"].search(n) and L["sim_action"].search(n):
            fire("sim_swap")
        refunds = L["refund_terms"].finditer(n)
        # "do not click any link offering a refund" and "never approve a request to get a refund" are advice
        actions = [a for a in L["action_terms"].finditer(n) + calls if not self.advisory_context(n, a)]
        if refunds and actions and _near(refunds, actions, 60):
            fire("refund_bait")
        media = L["sextortion_media"].finditer(n)
        threat = L["sextortion_threat"].finditer(n) + list(_SHARE_TO_CONTACTS.finditer(n))
        money = bool(L["money_terms"].search(n) or ctx.amounts or ctx.upi_ids)
        if (media and threat and _near(media, threat, 80) and money) or (L["sextortion_explicit"].search(n) and (threat or money)):
            fire("sextortion")
        install = L["install_terms"].finditer(n)
        if L["scheme_terms"].search(n) and (nonofficial or install or apk):
            fire("govt_scheme_bait")
        # Money sent to a phone number, UPI ID or link to get a scheme or card. Ayushman and e-Shram cards are
        # free; a fee paid at the counter has no number or link and is not this. On once the fraud pack defines
        # scheme_fee (pack 1.4.0, scripts/pack_update_1_4.py); web/checker.js mirrors it.
        if ("scheme_fee" in self.defs and L["scheme_terms"].search(n) and (ctx.mobiles or ctx.upi_ids or nonofficial)
                and (ctx.amounts or L["money_terms"].search(n))
                and any(not self.advisory_context(n, m) for m in _SEND_MONEY.finditer(n))):
            fire("scheme_fee")
        if L["challan_terms"].search(n) and nonofficial:
            fire("challan_link")
        if L["tax_refund_terms"].search(n) and (nonofficial or "personal_info_request" in fired):
            fire("tax_refund_bait")
        for m in L["remote_access"].finditer(n):
            if (not self.negated_in_sentence(n, m)
                    and not self.L["advisory"].search(_sentence(n, m.start(), m.end()))):
                fire("remote_access")
                break
        if "link_apk" not in fired and nonofficial and any(not self.negated(n, i.start(), i.end()) for i in install):
            fire("app_install")
        if ctx.mixed_tokens:
            fire("lookalike_text")

        # --- signs of a genuine message (lower the score, never to "safe")
        requests = {"otp_request", "personal_info_request", "upi_receive", "remote_access", "link_apk",
                    "advance_fee", "contact_mobile", "kyc_threat", "digital_arrest"}
        asked = bool(requests & fired.keys())
        advisory = L["advisory"].search(n)
        negated_share = any(self.negated(n, v.start(), v.end()) for v in L["share_verbs"].finditer(n))
        if (L["otp_terms"].search(n) and _has_code(n) and (advisory or negated_share)
                and not asked and not nonofficial):
            fire("genuine_otp_delivery")
        if (L["debit_credit_terms"].search(n) and L["account_terms"].search(n) and ctx.amounts
                and not nonofficial and not asked):
            fire("genuine_txn_alert")
        if advisory and not asked:
            fire("advisory")

        return list(fired.values())


def _snippet(text: str, m: re.Match, width: int = 40) -> str:
    return text[max(0, m.start() - width // 2) : m.end() + width // 2].strip()


@lru_cache(maxsize=1)
def get_engine() -> SignalEngine:
    return SignalEngine(get_pack("fraud").data)
