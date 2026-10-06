"""Text folding and extraction for Fraud-Shield.

Everything here is deterministic and fast. All matching happens on `fold(text)`:
NFKC, casefolded, look-alike Cyrillic/Greek letters mapped to Latin, Hindi nukta
dropped and chandrabindu written as anusvara, so spelling variants match one lexicon.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

DEVANAGARI = "ऀ-ॿ"

# Lowercase Cyrillic/Greek letters that render like Latin ones (applied after casefold).
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k",
    "м": "m", "т": "t", "в": "b", "н": "h", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d",
    "ӏ": "l", "ο": "o", "ν": "v", "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p",
    "τ": "t", "υ": "u", "χ": "x",
})
_CONFUSABLE_SCRIPTS = re.compile(r"[Ͱ-ϿЀ-ӿ]")
_LATIN = re.compile(r"[A-Za-z]")


# Devanagari digits (some Hindi SMS, and what OCR returns for Hindi screenshots) read as 0-9,
# so phone numbers, amounts and codes are found whichever digits a message uses.
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.translate(_HOMOGLYPHS).translate(_DEV_DIGITS)
    # Hindi: drop nukta (फ़ -> फ), chandrabindu -> anusvara (एँ -> एं)
    text = unicodedata.normalize("NFD", text).replace("़", "")
    text = unicodedata.normalize("NFC", text).replace("ँ", "ं")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[ \t ]+", " ", text)
    text = _defang(text)
    text = _WORD.sub(lambda m: _deleet(m.group()), text)
    return text.strip()


# Links written so filters miss them: "hxxp://", "site[.]top", "site (dot) top", "site dot top".
def _defang(text: str) -> str:
    text = re.sub(r"\bhxxp(s?)://", r"http\1://", text)
    text = re.sub(r"\s*[\[({]\s*(?:\.|dot)\s*[\])}]\s*", ".", text)
    return re.sub(rf"(?<=[a-z0-9])\s+dot\s+(?=(?:{_TLDS})\b)", ".", text)


# Digits written for letters inside words: "0TP", "bl0cked", "upd4te". Only in words that are mostly
# letters, only for a digit between two letters (or a leading 0), and never inside a link, so codes,
# masked numbers ("XX4421") and amounts stay as they are.
_WORD = re.compile(r"(?<![\w/.-])[a-z0-9]{3,}(?![\w/-]|\.\w)")
_LEET = {"0": "o", "3": "e", "4": "a", "5": "s"}


def _deleet(word: str) -> str:
    letters = sum(c.isalpha() for c in word)
    if not letters or letters == len(word) or letters <= len(word) - letters:
        return word
    out = list(word)
    for i, c in enumerate(word):
        nxt = i + 1 < len(word) and word[i + 1].isalpha()
        if c in _LEET and nxt and ((i > 0 and word[i - 1].isalpha()) or (i == 0 and c == "0")):
            out[i] = _LEET[c]
    return "".join(out)


def mixed_script_tokens(text: str) -> list[str]:
    """Tokens that mix Latin with Cyrillic/Greek letters, e.g. 'SВI' with a Cyrillic В."""
    out = []
    for token in re.findall(r"[^\s.,!?:;()\"'/]+", unicodedata.normalize("NFKC", text)):
        if _LATIN.search(token) and _CONFUSABLE_SCRIPTS.search(token):
            out.append(token)
    return out


# ---------------------------------------------------------------- links

_TLDS = (
    "com|in|net|org|xyz|top|online|site|club|icu|live|shop|info|buzz|click|link|vip|rest|work|me|co|"
    "io|ly|gl|cc|tk|ml|ga|cf|gq|app|page|biz|ws|to|gd|su|ru|cn|support|help|monster|cyou|sbs|cfd|quest|"
    "bond|win|loan|cam|today|store|space|website|fun|pw|at|id|gy|ae|be|st|us|uk|sh|sbi|bank|gov|nic|fin"
)
_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"'()]+"
    r"|\b\d{1,3}(?:\.\d{1,3}){3}(?::\d{2,5})?/[^\s<>\"'()]*"
    rf"|\b(?:[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?\.)+(?:{_TLDS})\b(?::\d{{2,5}})?(?:/[^\s<>\"'()]*)?",
    re.IGNORECASE,
)
_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


@dataclass(frozen=True)
class Url:
    raw: str
    host: str
    path: str

    @property
    def is_ip(self) -> bool:
        return bool(_IPV4.match(self.host))

    @property
    def tld(self) -> str:
        return self.host.rsplit(".", 1)[-1] if "." in self.host else self.host


def extract_urls(text: str) -> list[Url]:
    urls, seen = [], set()
    for m in _URL_RE.finditer(text):
        raw = m.group(0).rstrip(".,;:!?)]}\"'")
        rest = re.sub(r"^(?:https?://)", "", raw, flags=re.I)
        host, _, path = rest.partition("/")
        host = host.split(":")[0].lower()
        if host.startswith("www."):
            host = host[4:]
        if not host or host in seen:
            continue
        seen.add(host)
        urls.append(Url(raw=raw, host=host, path="/" + path if path else ""))
    return urls


# ---------------------------------------------------------------- numbers, money, UPI IDs

_MOBILE_RE = re.compile(r"(?<![\d])(?:\+?91[\s-]?|0)?([6-9]\d{4}[\s-]?\d{5})(?![\d])")
_TOLLFREE_RE = re.compile(r"(?<!\d)(18[06]0[\s-]?\d{3}[\s-]?\d{3,4})(?!\d)")
_SERIES1600_RE = re.compile(r"(?<!\d)(1600\d{6})(?!\d)")
_DLT_SENDER_RE = re.compile(r"^[a-z]{2}-[a-z0-9]{3,9}(?:-[pstg])?$", re.I)

_AMOUNT_RE = re.compile(
    r"(?:₹|\brs\.?|\binr|\brupees?|रु\.?|रुपये|रुपए)\s?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d{1,2}))?"
    r"(?:\s*(lakh|lac|crore|cr|लाख|करोड़|करोड))?",
    re.IGNORECASE,
)
_UPI_RE = re.compile(r"(?<![\w.@-])([a-z0-9][a-z0-9._-]{1,255}@[a-z][a-z0-9]{1,63})(?![\w@]|\.[a-z])", re.IGNORECASE)


def extract_mobiles(text: str) -> list[str]:
    found = []
    for m in _MOBILE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if digits not in found:
            found.append(digits)
    return found


def extract_tollfree(text: str) -> list[str]:
    return [re.sub(r"\D", "", m.group(1)) for m in _TOLLFREE_RE.finditer(text)]


def extract_1600(text: str) -> list[str]:
    return [m.group(1) for m in _SERIES1600_RE.finditer(text)]


def extract_amounts(text: str) -> list[float]:
    out = []
    for m in _AMOUNT_RE.finditer(text):
        value = float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else ""))
        unit = (m.group(3) or "").lower()
        if unit in ("lakh", "lac", "लाख"):
            value *= 1e5
        elif unit in ("crore", "cr", "करोड़", "करोड"):
            value *= 1e7
        out.append(value)
    return out


def extract_upi_ids(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).lower() for m in _UPI_RE.finditer(text)))


def classify_sender(sender: str | None) -> str | None:
    """'mobile' | 'dlt' (registered business header) | '1600' | 'other' | None."""
    if not sender:
        return None
    s = sender.strip()
    digits = re.sub(r"\D", "", s)
    if re.fullmatch(r"1600\d{6}", digits):
        return "1600"
    if re.fullmatch(r"(?:91|0)?[6-9]\d{9}", digits) and len(re.sub(r"[\d\s+()-]", "", s)) == 0:
        return "mobile"
    if _DLT_SENDER_RE.match(s):
        return "dlt"
    return "other"


# ---------------------------------------------------------------- language

_HINGLISH_MARKERS = {
    "hai", "hain", "aap", "aapka", "aapke", "aapki", "kar", "karo", "karein", "kare", "ke", "ki", "ka",
    "nahi", "nahin", "mat", "paise", "paisa", "batao", "bhejo", "ho", "gaya", "jayega", "hoga", "kya",
    "se", "ko", "mein", "me", "abhi", "turant", "jaldi", "bhai", "beta", "yeh", "ye", "woh", "aur",
}


def detect_language(text: str) -> str:
    """'hi' (Devanagari), 'hinglish' (romanised Hindi) or 'en'."""
    dev = len(re.findall(f"[{DEVANAGARI}]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    if dev and dev >= 0.4 * (dev + lat):
        return "hi"
    words = re.findall(r"[a-z]+", text.lower())
    if words and sum(w in _HINGLISH_MARKERS for w in words) >= max(2, len(words) // 8):
        return "hinglish"
    return "en"


# ---------------------------------------------------------------- context

@dataclass
class Context:
    raw: str
    norm: str
    lang: str
    input_type: str
    sender: str | None
    sender_kind: str | None
    urls: list[Url] = field(default_factory=list)
    mobiles: list[str] = field(default_factory=list)
    tollfree: list[str] = field(default_factory=list)
    series1600: list[str] = field(default_factory=list)
    amounts: list[float] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    mixed_tokens: list[str] = field(default_factory=list)


def build_context(text: str, sender: str | None = None, input_type: str = "text") -> Context:
    norm = fold(text)
    urls = extract_urls(norm)
    # wa.me/91XXXXXXXXXX links are contact numbers too
    mobiles = extract_mobiles(norm)
    for u in urls:
        if u.host in ("wa.me", "api.whatsapp.com"):
            for d in re.findall(r"\d{10,12}", u.path):
                tail = d[-10:]
                if tail[0] in "6789" and tail not in mobiles:
                    mobiles.append(tail)
    return Context(
        raw=text,
        norm=norm,
        lang=detect_language(text),
        input_type=input_type,
        sender=sender.strip() if sender else None,
        sender_kind=classify_sender(sender),
        urls=urls,
        mobiles=mobiles,
        tollfree=extract_tollfree(norm),
        series1600=extract_1600(norm),
        amounts=extract_amounts(norm),
        upi_ids=extract_upi_ids(norm),
        mixed_tokens=mixed_script_tokens(text),
    )
