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
from .normalize import DEVANAGARI, UNREAD_SCRIPTS, Context, _AMOUNT_RE, _MOBILE_RE, _PAY_CUE, fold

_DEV = re.compile(f"[{DEVANAGARI}]")
# Letters of the scripts Sahayak cannot read yet (Tamil, Bengali, ...; normalize.UNREAD_SCRIPTS), and of the
# scripts it reads (folded Latin, Devanagari).
_UNREAD_LETTER = re.compile("[" + "".join(chars for _, chars in UNREAD_SCRIPTS) + "]")
_WORD_SCRIPT = re.compile(rf"[a-z{DEVANAGARI}]")


def _unreadable(sentence: str) -> bool:
    """Half or more of the sentence's words are in a script Sahayak cannot read, so a negation or warning
    around an English word in it is invisible: 'காவல்துறை, CBI ... கைது செய்யாது' says CBI will NOT arrest.
    Words, not letters: Indic vowel signs are not letters to str.isalpha(), so letters undercount them."""
    unread = readable = 0
    for word in sentence.split():
        if _UNREAD_LETTER.search(word):
            unread += 1
        elif _WORD_SCRIPT.search(word):
            readable += 1
    return unread > 0 and unread >= readable


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
# A call between the handover and the request for the code: it was asked for on a later call, not at the door.
_CALL_WORD = re.compile(r"(?<![a-z])(?:call|phone|rang(?![a-z]))|फोन|कॉल")
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
    # the QR named first, as a person tells it: "he sent a QR code of Re 1 and asked me to scan it and receive money"
    r"(?:qr|क्यूआर)\W+(?:\w+\W+){0,12}?(?:scan|स्कैन)\W+(?:\w+\W+){0,3}?(?:and|to|kar\w*|करके|कर\s+के)\W+(?:\w+\W+){0,2}?(?:receive|get|claim|paane|lene|पाने|लेने)",
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
# The same threat in Hindi word order: the people first, a future "I will send / show / post" last ("tumhare
# saare contacts ko bhej denge", "friends aur family group me daal dungi", "दोस्तों को भेज दूंगी"). It counts only
# after a "pay, or else" earlier in the same clause (_OR_ELSE), so a photographer's "photos family ko bhej dunga,
# ₹500 baaki hai" or "...bhej dunga, warna Sunday ko" stays an ordinary message.
_SHARE_TO_CONTACTS_HI = re.compile(
    r"(?<![a-z])(?:contacts?|friends|family|relatives|dost(?:o|on)|rishtedaa?r(?:o|on)?|ghar\s*wal(?:e|o|on)|"
    r"parivar(?:\s+wal(?:e|o|on))?|biwi|wife|husband|sab\s*ko|sabhi\s*ko)(?![a-z])(?:\s+\S+){0,5}?\s+"
    r"(?:(?:bhej|daal|dal|dikha|forward|share|post|upload|viral|leak)\s*(?:kar\s*)?(?:d(?:u|oo)ng[ai]|d[eu]nge|dege|dega|degi)"
    r"|(?:bhej|daal|dal|dikha)(?:u|oo|au)ng[ai]|(?:bhej|daal|dal|dikhay)enge"
    r"|(?:forward|share|post|upload|viral|leak)\s+kar(?:u|oo)ng[ai]|(?:forward|share|post|upload|viral|leak)\s+karenge)(?![a-z])"
    r"|(?<![ऀ-ॿ])(?:कॉन्टैक्ट्स|कॉन्टैक्ट|कांटेक्ट्स|कॉन्टेक्ट्स|दोस्तों|दोस्तो|परिवार\s+वालों|परिवार\s+वालो|परिवार|"
    r"रिश्तेदारों|रिश्तेदारो|घर\s*वालों|घर\s*वालो|पत्नी|बीवी|पति|सबको|सब\s+को|सभी\s+को)(?:\s+\S+){0,5}?\s+"
    r"(?:(?:भेज|डाल|दिखा|फॉरवर्ड|शेयर|पोस्ट|अपलोड|वायरल|लीक)\s*(?:कर\s*)?(?:दूंगा|दूंगी|दुंगा|दुंगी|देंगे|देंगी|देगा|देगी)"
    r"|(?:भेज|डाल)(?:ूंगा|ूंगी|ुंगा|ुंगी|ेंगे)|दिखाऊंगा|दिखाऊंगी|दिखाएंगे"
    r"|(?:फॉरवर्ड|शेयर|पोस्ट|अपलोड|वायरल|लीक)\s+(?:करूंगा|करूंगी|करेंगे))")
# "Pay, or else": warna, varna, nahi to, "nahi kiya to", otherwise, or else, वरना, नहीं तो, "नहीं भेजे तो".
_OR_ELSE = re.compile(
    r"(?<![a-z])(?:warna|varna|vrna|otherwise|or\s+else|(?:nahi|nahin|nai)\s+(?:\w+\s+)?toh?)(?![a-z])"
    r"|वरना|अन्यथा|(?:नहीं|नही)\s+(?:\S+\s+)?तो(?![ऀ-ॿ])")
_PRIZE_EXCLUDE = re.compile(r"reward\s+points|loyalty\s+points|earned\s+\d+\s+points|cashback\s+points")
_NO_FEE = re.compile(r"(?:\bno|without|zero|free|बिना|कोई)\s+$")  # "No registration fee", "बिना शुल्क"
_EARN_RATE = re.compile(r"earn\w*\s+(?:upto\s+|up to\s+)?(?:rs\.?|₹|inr)?\s?\d[\d,]*\s*(?:/-)?\s*(?:per day|daily|/day|a day|per hour|per task|weekly|per week)")
_RETURN_PCT = re.compile(r"(?<!\d)\d{2,4}\s?%\s*(?:return|returns|profit|munafa|मुनाफ)")
_PAY_TO_GET = re.compile(r"pay\s+(?:only\s+)?(?:rs\.?|₹|inr)?\s?\d[\d,]*(?:/-)?\s+(?:only\s+)?(?:to|for|and)\s+(?:receive|get|claim|release|unlock|activate|process|withdraw)")
_HI_FEE_FIRST = re.compile(r"(?:पहले|pehle)\s+(?:\S+\s+){0,4}?(?:फीस|शुल्क|चार्ज|fee|fees|charge)")
_APK_TEXT = re.compile(r"\.apk\b|\bapk\s+(?:file|download|link)")
# A number you text a BLOCK keyword to is the bank's SMS line for blocking a card or UPI, not a person to call:
# genuine alerts end "Not you? Call 18002586161/SMS BLOCK UPI to 7308080808" or "1800 1234 पर कॉल करें या BLOCK
# लिखकर 9223008333 पर SMS करें"; a fake alert says "call 9046112785 to block your card". Only the number inside
# the instruction is exempt, only beside a toll-free number to call and never from a personal-mobile sender, so
# "Call 9046112785/SMS BLOCK UPI to 9046112785" and "Call or SMS BLOCK to 9046112785" still count.
_MOB = r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
_SMS_BLOCK = re.compile(
    rf"(?<![a-z])(?:sms|text)\W+(?:block|blk)(?!ed|ing)[^,;:.!?।]{{0,30}}?(?<![a-z])(?:to|on)\s+{_MOB}"
    rf"|(?<![a-z])(?:block|blk|ब्लॉक)\S*\s+(?:\S+\s+){{0,3}}?{_MOB}\s+(?:par|pe|पर)\s+(?:sms|एसएमएस)"
    rf"|{_MOB}\s+(?:par|pe|पर)\s+(?:block|blk|ब्लॉक)\S*\s+(?:\S+\s+){{0,2}}?(?:sms|एसएमएस)")
_TOLL_FREE = re.compile(r"(?<!\d)1(?:800|860|600)[\s-]?\d{2,4}(?:[\s-]?\d{2,4})?(?!\d)")
_JOIN_GROUP = re.compile(
    r"\bjoin\W+(?:\w+\W+){0,5}?(?:group|channel)\b"
    r"|\b(?:group|channel)\W+(?:\w+\W+){0,2}?(?:on\s+)?(?:telegram|whatsapp)\b"
    r"|\b(?:telegram|whatsapp)\W+(?:\w+\W+){0,2}?(?:group|channel)\b"
)
# "my SBI account", "मेरे SBI वाले खाते में": a writer naming their own bank is not claiming to be the bank.
# Checked just before each bank or office name (one word may sit between). Not for a described call, where
# "my" is the person who got the call.
_OWN_ORG = re.compile(r"(?:(?<![a-z])(?:my|mere|mera|meri|his|her|uske|uski|uska)"
                      r"|(?<![ऀ-ॿ])(?:मेरे|मेरा|मेरी|उसके|उसकी|उसका))\s+(?:\S+\s+)?$")
# an account or phone number written out (9 to 18 digits): a new place to send money
_LONG_NUMBER = re.compile(r"(?<!\d)\d{9,18}(?!\d)")
# wrong_transfer: a Devanagari letter right after a match means a longer word ("वापस कर दें" inside
# "वापस कर देंगे"); the danda (। ॥) ends a sentence and does not count. "I will return it" is a promise.
_DEV_LETTER = re.compile("[\u0900-\u0963\u0966-\u097f]")
_PROMISE = re.compile(r"(?<![a-z])(?:i|we|he|she|they)(?:'ll|'d|\s+(?:will|shall|would|can|could))\s+(?:\w+\s+){0,2}$")

# An amount the reader is told to pay, for job_fee: "pay ₹6,500", "deposit Rs 999", "₹1,200 jama karna hai",
# "₹500 dena hoga", "₹2,000 भरने होंगे". Salary wording ("we pay ₹15,000 per month", "monthly pay ₹15,000 +
# incentives") is not a demand.
_AMT = r"(?:₹|rs\.?|inr|rupees?|रु\.?|रुपये|रुपए)\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?/-)?"
_PAY_REQ = r"(?:(?:need|needs|have|has|had)\s+to|must|should|please|kindly|pls|plz|(?:asked|asking|told|telling|wants?|wanted)\s+(?:me\s+|us\s+|you\s+|him\s+|her\s+)?to)"
_PAY_FOR = (r"(?:for|towards|as|today|now|immediately|within|before|tonight|first|via|through|online|in\s+advance|advance"
            r"|to\s+(?:confirm|get|book|reserve|block|secure|activate|receive|process|start|complete|join|register|release|claim))")
_PAY_AMOUNT = re.compile(
    # English puts the amount after the verb. Asked for ("need to pay ₹6,500", "kindly pay Rs.3,500", "asked me to
    # deposit ₹8,000") or paid for something ("pay ₹2,000 for the uniform"); not salary wording ("pay ₹16,000, duty 8
    # hours", "we will pay ₹1,000 as joining bonus", "monthly pay ₹28,000 + incentives")
    rf"(?<!no ){_PAY_REQ}\s+(?:pay|deposit|transfer|send)\s+(?:(?:only|just|a|the|of)\s+)?{_AMT}"
    r"(?!\s*(?:per\b|/|a\s+month|monthly|pm\b|salary|ctc|stipend))"
    rf"|(?<![a-z])(?<!we )(?<!will )(?<!we'll )(?:pay|deposit|transfer)\s+(?:(?:only|just|a|the|of)\s+)?{_AMT}\s*{_PAY_FOR}(?![a-z])"
    rf"|(?<![a-z])(?<!we )(?<!will )deposit\s+(?:(?:only|just|a|the|of)\s+)?{_AMT}"
    r"(?!\s*(?:per\b|/|a\s+month|monthly|pm\b|salary|ctc|stipend|\+|-|to\s+(?:₹|rs)))"
    # "₹4,500 must be paid", "a fee of ₹35,000 has to be paid"
    rf"|{_AMT}\s+(?:[^\s.।!?]+\s+){{0,3}}?(?:must|needs?|has|have)\s+(?:to\s+)?be\s+(?:paid|deposited|transferred)"
    # Hinglish and Hindi put the verb last: "₹1,200 jama karna hai", "₹12,000 dene honge", "₹4,500 जमा करना होगा";
    # "₹18,000 account mein transfer hogi" is the salary being paid, not a demand
    rf"|{_AMT}\s+(?:[^\s.।!?]+\s+){{0,3}}?(?:(?:jama|pay|deposit|transfer)\s+(?:karna|karni|karo|karein|karen|kar\s+do"
    r"|kar\s+dena|kar\s+dein|kar\s+dijiye|kijiye|karne\s+(?:honge|hain|padenge|hoga|padega))"
    r"|(?:bharna|bharni|bharne|dena|deni|dene)\s+(?:hai|hain|hoga|hogi|honge|padega|padegi|padenge|pdega)"
    r"|bharo|bharein|bharen|bhar\s+do|de\s+do|de\s+dijiye)(?![a-z])"
    rf"|{_AMT}\s+(?:[^\s.।!?]+\s+){{0,3}}?(?:(?:जमा|भुगतान)\s+(?:करना|करनी|करें|करो|कर\s+दें|कीजिए|करने\s+(?:होंगे|हैं|पडेंगे))"
    r"|(?:भरना|भरनी|भरने|देना|देनी|देने)\s+(?:है|हैं|होगा|होगी|होंगे|पडेगा|पडेगी|पडेंगे)|भरें|भरो)"
)
# Signals that may stand next to in_person: a contact mobile and a time word are normal in a genuine appointment.
_IN_PERSON_OK = frozenset({"contact_mobile", "urgency"})
# A bank named as the card that gets a shop's discount ("10% instant discount on select bank cards", "SBI cards
# par 10% off", "बैंक कार्ड पर 10% छूट") is a sale, not a message from the bank. "Your card" stays a claim:
# "cashback on your HDFC card, claim here" is the bait.
_BANK_OFFER = re.compile(
    r"(?:discount|cashback|off|emi|savings?)\s+(?:on|with|using|via)\s+(?:\S+\s+){0,3}?(?:credit\s+|debit\s+)?cards?\b"
    r"|(?:\S+\s+){0,2}?(?:cards?|कार्ड\S*)\s+(?:par|pe|पर|से)\s+(?:\S+\s+){0,3}?"
    r"(?:discount|cashback|off|छूट|डिस्काउंट|कैशबैक)")
_YOUR = re.compile(r"(?<![a-z])(?:your|aapke|aapka|aapki)(?![a-z])|आपके|आपका|आपकी")
# Weak signs that ordinary messages carry too (a closing date, a KYC reminder, the word "salary"). in_person and
# nothing_asked fire only when nothing stronger fired; an invitation to come in person may also carry a contact
# number for questions and a shop's lucky draw.
_SOFT = {"urgency", "kyc_mention", "easy_money_weak"}
_SOFT_FOR_VISIT = _SOFT | {"contact_mobile", "prize"}


class SignalEngine:
    def __init__(self, pack: dict[str, Any]):
        self.defs = pack["signals"]
        self.L = {name: Lexicon(phrases) for name, phrases in pack["lexicons"].items()}
        d = pack["domains"]
        self.shorteners = set(d["shorteners"])
        self.suspicious_tlds = set(d["suspicious_tlds"])
        self.official_suffixes = tuple(d["official_suffixes"])
        self.official_domains = set(d["official_domains"])
        # numbers a bank itself publishes (missed-call banking): calling them is not the scam signal
        self.official_numbers = set(d.get("official_numbers", []))
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

    def unclear(self, text: str, start: int, end: int) -> bool:
        """negated(), or the words sit in a sentence written mostly in a script Sahayak cannot read, where a
        negation or warning would be invisible. For word signals only: a link, a number or an .apk file is
        evidence in any language."""
        return self.negated(text, start, end) or _unreadable(_sentence(text, start, end))

    def negated_in_sentence(self, text: str, m: re.Match) -> bool:
        """A negation anywhere earlier in the same sentence ('Do not install apps like AnyDesk'), or a sentence
        Sahayak cannot read."""
        s0 = 0
        for b in _SENTENCE_BREAK.finditer(text, 0, m.start()):
            s0 = b.end()
        return bool(self.L["negations_pre"].search(text, s0, m.start())) or _unreadable(_sentence(text, m.start(), m.end()))

    def advisory_context(self, text: str, m: re.Match) -> bool:
        """True when the match sits in a warning sentence ('police never do digital arrest')."""
        return bool(self.L["advisory"].search(_sentence(text, m.start(), m.end()))) or self.unclear(text, m.start(), m.end())

    # ------------------------------------------------------------ detection

    def run(self, ctx: Context) -> list[Fired]:
        n, L = ctx.norm, self.L
        fired: dict[str, Fired] = {}

        def fire(sid: str, **evidence: str) -> None:
            if sid not in fired:
                spec = self.defs[sid]
                fired[sid] = Fired(sid, float(spec["weight"]), bool(spec.get("hard")), evidence)

        # a shop's discount on bank cards ("10% off on select bank cards") is a sale, not the bank speaking
        offers = [m.span() for m in _BANK_OFFER.finditer(n) if not _YOUR.search(m.group(0))]

        def claimed(lex: Lexicon, skip: list[tuple[int, int]] = ()) -> bool:
            return any((ctx.input_type == "call" or not _OWN_ORG.search(n, max(0, m.start() - 30), m.start()))
                       and not any(a <= m.start() and m.end() <= b for a, b in skip)
                       for m in lex.finditer(n))

        org_bank = claimed(L["bank_terms"], offers)
        org_claim = org_bank or claimed(L["authority_terms"])
        links = [u for u in ctx.urls if u.host not in ("wa.me", "api.whatsapp.com")]
        nonofficial = [u for u in links if not self.is_official(u.host)]
        official = [u for u in links if self.is_official(u.host)]
        share_verbs = [v for v in L["share_verbs"].finditer(n) if not self.unclear(n, v.start(), v.end())]

        # --- requests for secrets
        secrets = L["otp_terms"].finditer(n) + L["code_phrases"].finditer(n)
        secrets += [m for m in L["pin_terms"].finditer(n) if not _PIN_CODE.match(n, m.end())]
        # On a call the caller asking for the code is the scam ("delivery executive here, read me the OTP"); the code
        # told at the door is how delivery works: asked for after the parcel was handed over, with no call in
        # between ("he handed me the parcel, then asked for the OTP"), or to be told to the delivery person when the
        # goods arrive ("jab cylinder mil jaye tab delivery wale ko DAC bata dena"). On once the fraud pack defines
        # the handover lexicons; web/checker.js mirrors it.
        at_door = bool(ctx.input_type == "call" and not nonofficial and _OTP_OK_CONTEXT.search(n)
                       and not ("not_in_person" in L and L["not_in_person"].search(n)))
        done = L["handover_done"].finditer(n) if at_door and "handover_done" in L else []
        to = (L["handover_to"].finditer(n) if at_door and "handover_to" in L and "handover_when" in L
              and L["handover_when"].search(n) else [])
        doorstep = False
        for v in share_verbs:
            if not any(_gap(v, t) <= 60 for t in secrets):
                continue
            sentence = _sentence(n, v.start(), v.end())
            routine = _OTP_OK_CONTEXT.search(sentence) or _CODE_NEXT_TO_TERM.search(n)
            if routine and not nonofficial and ctx.input_type != "call":
                continue  # "share OTP 4417 with the driver" delivers a code; it does not ask for one
            if (any(d.end() <= v.start() and not _CALL_WORD.search(n, d.end(), v.start()) for d in done)
                    or any(_gap(v, r) <= 40 for r in to)):
                doorstep = True
                continue
            fire("otp_request", phrase=_snippet(n, v))
            break
        personal = L["personal_info_terms"].finditer(n)
        if any(_gap(v, p) <= 50 for v in share_verbs for p in personal):
            fire("personal_info_request")
        for pat in _UPI_RECEIVE_PATTERNS:
            m = pat.search(n)
            # also reject a negation inside the match: "to receive money you never need to enter your PIN",
            # and a warning about the trick: "fraudsters ask you to scan QR codes for refunds"
            if (m and not self.unclear(n, m.start(), m.end()) and not self.L["negations_pre"].search(n, m.start(), m.end())
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
        mobiles = [x for x in ctx.mobiles if x not in self.official_numbers]
        # a bank's own footer never arrives from a personal mobile number
        sms_lines = ([s.span() for s in _SMS_BLOCK.finditer(n)]
                     if ctx.sender_kind != "mobile" and _TOLL_FREE.search(n) else [])
        contact = None
        for m in number_spans:
            if re.sub(r"\D", "", m.group(1)) in self.official_numbers:
                continue
            if any(a <= m.start() and m.end() <= b for a, b in sms_lines):
                continue  # the bank's SMS-block line, beside its toll-free number (see _SMS_BLOCK)
            if any(_gap(m, c) <= 40 for c in calls) or "whatsapp" in n:
                contact = re.sub(r"\D", "", m.group(1))
                break
        if contact is None and wa_link and mobiles:
            contact = mobiles[0]
        if contact:
            fire("contact_mobile", number=contact)
            if org_claim:
                fire("org_contact_mobile", number=contact)
            if L["debit_credit_terms"].search(n):
                fire("fake_alert_callback", number=contact)
        # The 'customer care' words must label the number ("Call customer care 98760 12345"), not a job title
        # or a shop's name elsewhere in the message ("Customer Support Associate role ... call HR on 93104 57286").
        care = L["customer_care_terms"].finditer(n)
        for m in number_spans:
            number = re.sub(r"\D", "", m.group(1))
            if number in mobiles and any(_gap(m, c) <= 80 for c in care):
                fire("customer_care_bait", number=number)
                break

        # --- pressure and threats
        # "no hurry", "koi jaldi nahi", "jab time mile": a message that says there is no rush is not rushing
        # you, even when it names a date ("fees ki last date 10 tarikh hai ... koi jaldi nahi"). Packs 1.6.0+.
        calm = L["no_pressure"].search(n) if "no_pressure" in L else None
        m = None if calm else L["urgency"].search(n)
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
                     if not self.unclear(n, m.start(), m.end()) and not _NO_FEE.search(n[max(0, m.start() - 10) : m.start()])]
        if (fee_terms or _PAY_TO_GET.search(n) or _HI_FEE_FIRST.search(n) or _HI_FEE_SEND.search(n)
                or (pay_first and not self.negated(n, pay_first.start(), pay_first.end()))
                or (_COURIER_FEE.search(n) and (L["courier_terms"].search(n) or "gift" in n))):
            fire("advance_fee")
        # A job that asks you to pay: real employers never charge to hire, train, kit out or verify you. A fee paid
        # on the recruiter's own official site, with no number or UPI ID to pay ("pay ₹500 exam fee only on
        # rrbapply.gov.in"), is not this. On once the fraud pack defines job_fee and job_terms; web/checker.js mirrors it.
        on_official_site = official and not nonofficial and not ctx.mobiles and not ctx.upi_ids
        if "job_fee" in self.defs and "job_terms" in L and L["job_terms"].search(n) and not on_official_site:
            for m in _PAY_AMOUNT.finditer(n):
                # also a negation inside the match: "₹500 maange to mat bharo"
                if not self.advisory_context(n, m) and not L["negations_pre"].search(n, m.start(), m.end()):
                    fire("job_fee", phrase=m.group(0)[:60])
                    break
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
        # a cut explained as maintenance work ("रखरखाव के कारण आज 10 से 2 बजे तक बिजली बंद रहेगी") is a
        # notice, not the unpaid-bill threat
        maintenance = "maintenance_terms" in L and L["maintenance_terms"].search(n)
        if elec and cut and _near(elec, cut, 60) and (L["tonight_terms"].search(n) or ctx.mobiles) and not maintenance:
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
        # "Sent to you by mistake, please send it back": the 'credited' SMS is fake, or real money that only the
        # sender's bank should reverse. Packs from 1.6.0 define wrong_transfer; web/checker.js mirrors it.
        if ("wrong_transfer" in self.defs and L["mistake_terms"].search(n)
                and (L["money_terms"].search(n) or ctx.amounts or ctx.upi_ids)):
            for b in L["return_request"].finditer(n):
                # "वापस कर दें" asks, "वापस कर देंगे" promises; "please return it" asks, "I will return it" promises
                if (_DEV_LETTER.match(n, b.end()) or _PROMISE.search(n, max(0, b.start() - 40), b.start())
                        or self.advisory_context(n, b)):
                    continue
                fire("wrong_transfer")
                break
        media = L["sextortion_media"].finditer(n)
        threat = L["sextortion_threat"].finditer(n) + list(_SHARE_TO_CONTACTS.finditer(n))
        threat += [m for m in _SHARE_TO_CONTACTS_HI.finditer(n)
                   if _OR_ELSE.search(n, max(m.start() - 60, _clause_start(n, m.start())), m.start())]
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
        # A donation appeal paid to a personal UPI ID or phone number: the fake medical or relief appeal. A real
        # fundraiser can be checked first (the hospital's own account, a verified crowdfunding page). On once the
        # fraud pack defines donation_appeal and donation_terms; web/checker.js mirrors it.
        if ("donation_appeal" in self.defs and (ctx.upi_ids or mobiles)
                and (ctx.amounts or ctx.upi_ids or L["money_terms"].search(n) or _WALLET_TERMS.search(n))
                and any(not self.advisory_context(n, m) for m in L["donation_terms"].finditer(n))):
            fire("donation_appeal")
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
                    "advance_fee", "job_fee", "contact_mobile", "kyc_threat", "digital_arrest"}
        asked = bool(requests & fired.keys())
        advisory = L["advisory"].search(n)
        negated_share = any(self.negated(n, v.start(), v.end()) for v in L["share_verbs"].finditer(n))
        if (L["otp_terms"].search(n) and _has_code(n) and (advisory or negated_share)
                and not asked and not nonofficial):
            fire("genuine_otp_delivery")
        # a bank's transaction alert, not a person's story of a call ("the amount got credited to my account")
        if (L["debit_credit_terms"].search(n) and L["account_terms"].search(n) and ctx.amounts
                and not nonofficial and not asked and ctx.input_type != "call"):
            fire("genuine_txn_alert")
        if doorstep and not asked and "doorstep_code" in self.defs:
            fire("doorstep_code")
        if advisory and not asked:
            fire("advisory")
        # It says there is no hurry, gives no new place to send money (no UPI ID, number, link or account
        # number) and nothing else in it looks like a scam: "mere purane account me bhej dena, koi jaldi nahi".
        # This can outweigh the wording model alone, never a scam sign. Packs from 1.6.0.
        if (calm and "no_pressure" in self.defs and not any(f.weight > 0 for f in fired.values())
                and not (ctx.upi_ids or ctx.mobiles or ctx.urls or _LONG_NUMBER.search(n))):
            fire("no_pressure", phrase=calm.group(0))
        # In person: come to a camp, office, shop or interview ("panchayat bhawan me shivir", "walk-in interview"),
        # or bring your papers ("carry your resume and an Aadhaar copy", "आधार कार्ड साथ लाएं"). Scammers work
        # remotely and ask you to send things, never to come or to bring them. An invitation may carry a contact
        # number, a time word or a shop's lucky draw; bringing papers counts only beside a contact number or a time
        # word; neither counts with money asked, an unknown link or a UPI ID. On once the pack defines in_person.
        positives = {sid for sid, f in fired.items() if f.weight > 0}
        if "in_person" in self.defs and not nonofficial and not ctx.upi_ids:
            visits = ([m for m in L["in_person"].finditer(n) if not self.unclear(n, m.start(), m.end())]
                      if "in_person" in L else [])
            # money asked: an amount beside a word for paying ("uniform ka ₹1,200 jama karna hai", "pay on PhonePe"),
            # or an amount to bring ("₹50,000 lekar aana"). A purchase threshold ("₹2,000 ki kharidari par") is not.
            amounts = list(_AMOUNT_RE.finditer(n))
            pay = [m for m in list(_PAY_CUE.finditer(n)) + list(_WALLET_TERMS.finditer(n))
                   if not self.negated(n, m.start(), m.end()) and not _NO_FEE.search(n[max(0, m.start() - 10) : m.start()])]
            money = bool(amounts and pay) or any(0 <= v.start() - a.end() <= 25 for v in visits for a in amounts)
            visit = visits[0] if visits and not money and not positives - _SOFT_FOR_VISIT else None
            bring = None
            if "bring_verbs" in L and "bring_items" in L and not positives - _IN_PERSON_OK:
                brings, items = L["bring_verbs"].finditer(n), L["bring_items"].finditer(n)
                if brings and items and _near(brings, items, 40):
                    bring = brings[0]
            if visit or bring:
                fire("in_person", phrase=(visit or bring).group(0))
        # The person describing a call says the caller asked for nothing ("kuch maanga nahi"), the call as told
        # names no app, link or code ("didn't ask for anything, just install this app" is the trick), and the
        # rules found nothing stronger than a weak sign. Calls only: a message that says so about itself proves
        # nothing. On once the pack defines it.
        if ("nothing_asked" in self.defs and "nothing_asked" in L and ctx.input_type == "call"
                and L["nothing_asked"].search(n) and not positives - _SOFT and not nonofficial and not ctx.upi_ids
                and not L["action_terms"].search(n) and all(self.negated(n, s.start(), s.end()) for s in secrets)):
            fire("nothing_asked")

        return list(fired.values())


def _snippet(text: str, m: re.Match, width: int = 40) -> str:
    return text[max(0, m.start() - width // 2) : m.end() + width // 2].strip()


@lru_cache(maxsize=1)
def get_engine() -> SignalEngine:
    return SignalEngine(get_pack("fraud").data)
