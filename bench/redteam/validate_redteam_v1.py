# -*- coding: utf-8 -*-
"""Validate redteam_v1_blind.jsonl: schema, counts, UPI handles, phone shapes."""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl

P = Path(__file__).parent / "redteam_v1_blind.jsonl"
KEYS = ["id", "label", "category", "technique", "lang", "input_type", "sender", "text"]
LANGS = {"en", "hi", "hinglish", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or", "ur"}
REGIONAL = LANGS - {"en", "hi", "hinglish"}
errors = []
recs = []

with P.open(encoding="utf-8") as fh:
    for ln, line in enumerate(fh, 1):
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {ln}: JSON error {e}")
            continue
        recs.append(r)
        if list(r.keys()) != KEYS:
            errors.append(f"{r.get('id')}: keys {list(r.keys())}")
        if not re.fullmatch(r"rt1-\d{3}", r["id"]):
            errors.append(f"{r['id']}: bad id")
        if r["label"] not in {"scam", "genuine"}:
            errors.append(f"{r['id']}: bad label")
        if r["lang"] not in LANGS:
            errors.append(f"{r['id']}: bad lang {r['lang']}")
        if r["input_type"] not in {"text", "call", "qr"}:
            errors.append(f"{r['id']}: bad input_type")
        if r["sender"] is not None and not isinstance(r["sender"], str):
            errors.append(f"{r['id']}: bad sender")
        for k in ("category", "technique", "text"):
            if not isinstance(r[k], str) or not r[k].strip():
                errors.append(f"{r['id']}: empty {k}")

ids = [r["id"] for r in recs]
if len(ids) != len(set(ids)):
    errors.append("duplicate ids")

# ---- digit normalisation (Devanagari/Bengali/Odia/etc. -> ASCII) ----
def ascii_digits(s):
    out = []
    for ch in s:
        if ch.isdigit() and not ch.isascii():
            try:
                out.append(str(unicodedata.digit(ch)))
                continue
            except (TypeError, ValueError):
                pass
        out.append(ch)
    return "".join(out)

# ---- UPI handles: every x@y that is not an e-mail must be @sahayakdemo ----
for r in recs:
    for m in re.finditer(r"[A-Za-z0-9._\-]+@([A-Za-z0-9.\-]+)", r["text"]):
        dom = m.group(1).rstrip(".")
        if "." in dom:            # e-mail address (gmail.com etc.)
            continue
        if dom != "sahayakdemo":
            errors.append(f"{r['id']}: UPI handle not @sahayakdemo: {m.group(0)}")

# ---- QR payloads ----
for r in recs:
    if r["input_type"] != "qr":
        continue
    t = r["text"]
    if not t.startswith("upi://pay?"):
        errors.append(f"{r['id']}: QR not upi://pay")
        continue
    qs = dict(parse_qsl(urlsplit(t.replace(" ", "%20")).query))
    if not qs.get("pa", "").endswith("@sahayakdemo"):
        errors.append(f"{r['id']}: QR pa not @sahayakdemo")
    for k in ("pa", "pn"):
        if k not in qs:
            errors.append(f"{r['id']}: QR missing {k}")

# ---- phone-number shapes ----
for r in recs:
    blob = ascii_digits(r["text"])
    # numbers with digits separated by single spaces/dots, e.g. 9 1 2 5 ... or 9.1.3...
    for m in re.finditer(r"(?<![\d*])(\d(?:[ .]\d){9})(?![\d])", blob):
        d = re.sub(r"\D", "", m.group(1))
        if d[0] not in "6789":
            errors.append(f"{r['id']}: spaced 10-digit number not 6-9: {m.group(1)}")
    # plain/grouped 10-digit runs not part of longer numbers
    for m in re.finditer(r"(?<![\d\w-])(\d{5}[ ]?\d{5}|\d{10})(?![\d])", blob):
        d = m.group(1).replace(" ", "")
        if d.startswith("1800") or d.startswith("1860"):
            continue
        if d[0] not in "6789":
            # could be a consumer / account / reference number - report for manual review
            print(f"  note {r['id']}: 10-digit non-mobile run {m.group(1)!r} (check it is not a phone)")
    s = r["sender"]
    if s and s.startswith("+91"):
        if not re.fullmatch(r"\+91[6-9]\d{9}", s):
            errors.append(f"{r['id']}: bad sender number {s}")

# ---- counts ----
lab = Counter(r["label"] for r in recs)
it = Counter((r["label"], r["input_type"]) for r in recs)
lng = Counter((r["label"], r["lang"]) for r in recs)
regional_scam = sum(1 for r in recs if r["label"] == "scam" and r["lang"] in REGIONAL)
regional_gen = sum(1 for r in recs if r["label"] == "genuine" and r["lang"] in REGIONAL)
scam_nonqr = sum(1 for r in recs if r["label"] == "scam" and r["input_type"] != "qr")
gen_nonqr = sum(1 for r in recs if r["label"] == "genuine" and r["input_type"] != "qr")

expect = {
    "total": (len(recs), 182),
    "scam messages (text+call)": (scam_nonqr, 110),
    "genuine messages (text+call)": (gen_nonqr, 60),
    "scam calls": (it[("scam", "call")], 25),
    "scam qr": (it[("scam", "qr")], 8),
    "genuine qr": (it[("genuine", "qr")], 4),
    "regional scams": (regional_scam, 15),
    "regional genuine": (regional_gen, 5),
}
for name, (got, want) in expect.items():
    flag = "OK " if got == want else "BAD"
    print(f"{flag} {name}: {got} (want {want})")
    if got != want:
        errors.append(f"count {name}: {got} != {want}")

# languages of the 15 regional scams must cover all 10 requested languages
need = {"ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or", "ur"}
have = {r["lang"] for r in recs if r["label"] == "scam" and r["lang"] in REGIONAL}
if need - have:
    errors.append(f"regional scam languages missing: {need - have}")

# sanity: invisible / homoglyph characters really present where intended
zw = [r["id"] for r in recs if "​" in r["text"]]
cyr = [r["id"] for r in recs if re.search(r"[Ѐ-ӿ]", r["text"])]
print("zero-width items:", zw, "| cyrillic items:", cyr)

print("\nlabel:", dict(lab))
print("label x input_type:", dict(sorted(it.items())))
print("label x lang:", dict(sorted(lng.items())))
print("\nscam categories:", dict(Counter(r["category"] for r in recs if r["label"] == "scam").most_common()))
print("\ngenuine categories:", dict(Counter(r["category"] for r in recs if r["label"] == "genuine").most_common()))

if errors:
    print("\nERRORS:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\nALL CHECKS PASSED")
