"""Remove what identifies a person from messages people shared with consent, before anyone else sees them.

Reads a JSON-lines file (one message per line, with at least "text") and writes a redacted copy beside it. What it
replaces, consistently within one run (the same number becomes the same stand-in everywhere):
  - mobile numbers (with or without +91, spaces or dashes) and landlines with an STD code: a fictional number of the
    same shape (9000000001, 9000000002, ...; 0110000001, ... for landlines), so a check still sees "a mobile number";
  - Aadhaar numbers (12 digits, often 4-4-4), card and account numbers (9 to 18 digits): all but the last 4 digits
    become X, the way banks print them;
  - PAN numbers: XXXXX0000X; e-mail addresses: person1@example.com;
  - the name part of a UPI ID (ramesh.k@okaxis becomes payee1@okaxis): the bank handle after @ is kept, it matters;
  - query strings on links (?id=..., often a personal token): replaced by "?…"; the domain and path are kept, they are
    the evidence;
  - names after a greeting or title ("Dear Ramesh Kumar", "Mr. Sharma", "प्रिय राम", "श्री मोहन"): [NAME].
It keeps toll-free and 1600-series numbers (banks' and companies' own), short codes such as 1930, amounts, dates,
OTP-style codes and brand names. Names elsewhere in a message cannot be found reliably by a script: a person reads
every redacted message before it leaves the collection laptop (bench/scambench/COLLECTING.md).

The original text is never written anywhere by this script; the log lists counts per kind, not values.

Usage: python bench/redact_messages.py <in.jsonl> [--out <out.jsonl>]   (default: <in>.redacted.jsonl)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEV = "ऀ-ॿ"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}\b", re.I)
_UPI = re.compile(r"\b([\w.-]{2,})@([a-z][a-z0-9]{1,20})\b", re.I)
_URL_QUERY = re.compile(r"((?:https?://|www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s?#]*)?)\?[^\s]*", re.I)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
_TOLL_FREE = re.compile(r"^(?:1800|1860|1600)")
# +91 / 0 / 91 prefixes, then a 10-digit mobile starting 6-9, with optional spaces or dashes inside
_MOBILE = re.compile(r"(?<![\d])(?:\+?91[\s-]?|0)?([6-9]\d{4}[\s-]?\d{5}|[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4})(?![\d])")
# landline with an STD code: 0 + 2-4 digit code + 6-8 digit number = 10-11 digits
_LANDLINE = re.compile(r"(?<![\d])0[1-9]\d{1,3}[\s-]\d{6,8}(?![\d])")
# long digit runs (Aadhaar 4-4-4, card 4-4-4-4, account numbers): 9 to 18 digits, spaces or dashes allowed
_LONG_DIGITS = re.compile(r"(?<![\d])\d(?:[\s-]?\d){8,17}(?![\d])")
_NAME_AFTER = re.compile(
    r"(?:\b(?i:dear|hi|hello|mr|mrs|ms|miss|shri|smt|sri)\.?\s+)((?:[A-Z][a-z]+)(?:\s+[A-Z][a-z]+){0,2})"
    rf"|(?:(?:प्रिय|श्री|श्रीमती|सुश्री)\s+)([{DEV}]+(?:\s+[{DEV}]+)?)(?=\s*(?:जी|,|।|!|\s|$))")
# Words after "Dear" or "प्रिय" that address a role, not a person ("Dear Customer", "Hi Mum": kept, they are evidence)
_NOT_NAMES = {"Customer", "Customers", "Sir", "Madam", "User", "Member", "Consumer", "Parent", "Parents", "Team",
              "Friend", "Friends", "All", "Valued", "Card", "Account", "Policy", "Applicant", "Candidate", "Student",
              "Taxpayer", "Citizen", "Beneficiary", "Subscriber", "Client", "Investor", "Winner", "Mum", "Mom",
              "Mummy", "Papa", "Dad", "Beta", "Bhai", "Bhaiya", "Didi", "Maa", "Uncle", "Aunty", "There",
              "ग्राहक", "उपभोक्ता", "सदस्य", "मित्र", "जी", "लाभार्थी", "आवेदक", "नागरिक", "करदाता"}


class Redactor:
    def __init__(self) -> None:
        self.mobiles: dict[str, str] = {}
        self.landlines: dict[str, str] = {}
        self.emails: dict[str, str] = {}
        self.payees: dict[str, str] = {}
        self.counts: Counter = Counter()

    def _mobile(self, m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(1))
        if digits not in self.mobiles:
            self.mobiles[digits] = f"9{len(self.mobiles) + 1:09d}"
        self.counts["mobile"] += 1
        return self.mobiles[digits]

    def _landline(self, m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if digits not in self.landlines:
            self.landlines[digits] = f"0{len(self.landlines) + 1:0{len(digits) - 1}d}"
        self.counts["landline"] += 1
        return self.landlines[digits]

    def _long(self, m: re.Match) -> str:
        raw = m.group(0)
        digits = re.sub(r"\D", "", raw)
        if _TOLL_FREE.match(digits) and len(digits) <= 11:
            return raw  # a company's toll-free or 1600-series number
        if digits in self.mobiles.values() or digits in self.landlines.values():
            return raw  # a stand-in this run already put there
        self.counts["account_or_id"] += 1
        keep = 4
        out, seen = [], 0
        total = len(digits)
        for ch in raw:
            if ch.isdigit():
                seen += 1
                out.append(ch if seen > total - keep else "X")
            else:
                out.append(ch)
        return "".join(out)

    def _email(self, m: re.Match) -> str:
        key = m.group(0).lower()
        if key not in self.emails:
            self.emails[key] = f"person{len(self.emails) + 1}@example.com"
        self.counts["email"] += 1
        return self.emails[key]

    def _upi(self, m: re.Match) -> str:
        name, handle = m.group(1), m.group(2)
        if name.lower().startswith(("payee", "person")):
            return m.group(0)
        if name.lower() not in self.payees:
            self.payees[name.lower()] = f"payee{len(self.payees) + 1}"
        self.counts["upi_id"] += 1
        return f"{self.payees[name.lower()]}@{handle}"

    def _name(self, m: re.Match) -> str:
        name = m.group(1) or m.group(2)
        if name.split()[0] in _NOT_NAMES:
            return m.group(0)
        self.counts["name"] += 1
        return m.group(0).replace(name, "[NAME]")

    def text(self, text: str) -> str:
        text = _URL_QUERY.sub(lambda m: (self.counts.update(["link_query"]), m.group(1) + "?…")[1], text)
        text = _EMAIL.sub(self._email, text)
        text = _UPI.sub(self._upi, text)
        text = _PAN.sub(lambda m: (self.counts.update(["pan"]), "XXXXX0000X")[1], text)
        text = _LANDLINE.sub(self._landline, text)
        text = _MOBILE.sub(self._mobile, text)
        text = _LONG_DIGITS.sub(self._long, text)
        return _NAME_AFTER.sub(self._name, text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    out = args.out or args.src.with_suffix(".redacted.jsonl")
    if out.resolve() == args.src.resolve():
        raise SystemExit("write the redacted copy to a new file; the original stays where it is")
    red = Redactor()
    rows = [json.loads(line) for line in args.src.read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        r["text"] = red.text(r["text"])
        if r.get("sender"):
            r["sender"] = red.text(r["sender"])
        r["redacted"] = True
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} messages -> {out}")
    print("replaced: " + (", ".join(f"{k} {v}" for k, v in sorted(red.counts.items())) or "nothing"))
    print("Now read every message: names outside a greeting are not found by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
