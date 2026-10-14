"""Build the cards of "Spot the scam", the awareness game in the phone app (web/game.json).

Each card is a message or a phone call a person might get, with the right answer (scam or real) and the badge it
counts towards. The cards come from messages the team already wrote and vetted: the demo examples, ScamBench and
the call descriptions. None is a real person's message. A card is kept only when Sahayak's own check agrees with its
answer (Scam for a scam, No scam signs for a real one), so the game never teaches anything the checker would
contradict. The phone shows the checker's own reasons after each answer, in the app's language.

  python scripts/build_game.py            # writes web/game.json
  python scripts/build_game.py --check    # fails if web/game.json is out of date

Re-run it after a fraud pack changes; tests/test_game.py fails while a card and the checker disagree.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sahayak.fraud.pipeline import check_message  # noqa: E402

OUT = ROOT / "web" / "game.json"
# Badges: groups of scam categories a player learns to spot, plus one for knowing a real message when they see it.
BADGES = {
    "otp": ("otp_pin", "customer_care"),
    "upi": ("upi_receive",),
    "kyc": ("kyc", "electricity"),
    "arrest": ("digital_arrest", "impersonation"),
    "prize": ("prize", "courier"),
    "money": ("job_task", "investment", "loan_fee"),
    "scheme": ("govt_scheme", "govt_payment", "malicious_app"),
    "real": (),
}
PER_BADGE = 6     # scam cards per badge
REAL_CARDS = 14   # genuine cards
MAX_CHARS = 300   # a card must fit on a phone screen


def badge_for(category: str | None, label: str) -> str | None:
    if label == "genuine":
        return "real"
    for badge, cats in BADGES.items():
        if category in cats:
            return badge
    return None


def candidates() -> list[dict]:
    out: list[dict] = []
    demo = json.loads((ROOT / "packs" / "demo.v1.json").read_text(encoding="utf-8"))
    demo_cat = {"kyc_hi": "kyc", "otp_call": "otp_pin", "upi_receive": "upi_receive", "digital_arrest": "digital_arrest",
                "scheme_apk": "govt_scheme", "ayushman_fee": "govt_scheme", "electricity": "electricity", "genuine_otp": "bank_otp"}
    for ex in demo["examples"]:
        out.append({"id": f"demo-{ex['id']}", "text": ex["text"], "sender": ex.get("sender"),
                    "input_type": ex.get("input_type") or "text", "label": "genuine" if ex["id"].startswith("genuine") else "scam",
                    "category": demo_cat.get(ex["id"]), "lang": "hi" if any("ऀ" <= c <= "ॿ" for c in ex["text"]) else "en"})
    for line in (ROOT / "bench" / "scambench" / "scambench_v0.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out.append({"id": r["id"], "text": r["text"], "sender": None, "input_type": r.get("input_type") or "text",
                    "label": r["label"], "category": r.get("category"), "lang": r.get("lang", "en")})
    for line in (ROOT / "bench" / "callbench" / "calls_v0.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out.append({"id": f"call-{r['id']}", "text": r["text"], "sender": None, "input_type": "call",
                    "label": r["label"], "category": r.get("category"), "lang": r.get("lang", "en")})
    return out


def build() -> list[dict]:
    picked: dict[str, list[dict]] = {b: [] for b in BADGES}
    seen_text: set[str] = set()
    for c in candidates():
        badge = badge_for(c["category"], c["label"])
        if not badge or len(c["text"]) > MAX_CHARS or c["text"] in seen_text:
            continue
        if "​" in c["text"] or "‍" in c["text"]:  # red-team tricks with hidden characters stay out of a game
            continue
        # A real delivery code is handed over at the door. It is genuine, but it would contradict the game's one-line
        # lesson for real messages ("never asks you to share an OTP"), so it stays out until it has its own lesson.
        if c["label"] == "genuine" and re.search(r"deliver", c["text"], re.I) and re.search(r"\b(?:OTP|code)\b", c["text"], re.I):
            continue
        verdict = check_message(c["text"], sender=c["sender"], input_type=c["input_type"])["verdict"]
        if verdict != ("scam" if c["label"] == "scam" else "no_signs"):
            continue  # the game never teaches what the checker would contradict
        limit = REAL_CARDS if badge == "real" else PER_BADGE
        # variety: at most three cards of one kind in a badge, and never the same message twice
        if len(picked[badge]) >= limit or sum(q["category"] == c["category"] for q in picked[badge]) >= 3:
            continue
        seen_text.add(c["text"])
        picked[badge].append({"id": c["id"], "text": c["text"], "sender": c["sender"], "input_type": c["input_type"],
                              "truth": c["label"], "badge": badge, "category": c["category"], "lang": c["lang"]})
    return [card for badge in BADGES for card in picked[badge]]


def main(argv: list[str]) -> int:
    cards = build()
    body = json.dumps({"note": "Spot the scam: cards for the awareness game (scripts/build_game.py). Written by the team to "
                               "mirror publicly reported patterns; not real messages. Each answer agrees with Sahayak's check.",
                       "badges": list(BADGES), "cards": cards}, ensure_ascii=False, indent=1) + "\n"
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != body:
            print("web/game.json is out of date: run python scripts/build_game.py")
            return 1
        return 0
    OUT.write_text(body, encoding="utf-8")
    by = {b: sum(c["badge"] == b for c in cards) for b in BADGES}
    print(f"web/game.json: {len(cards)} cards " + ", ".join(f"{b} {n}" for b, n in by.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
