"""Spot the scam, the awareness game in the phone app: its cards are up to date, and every answer the game teaches
agrees with Sahayak's own check (scripts/build_game.py keeps only such cards)."""
import json
import subprocess
import sys
from pathlib import Path

from sahayak.fraud.pipeline import check_message

ROOT = Path(__file__).resolve().parent.parent
GAME = json.loads((ROOT / "web" / "game.json").read_text(encoding="utf-8"))


def test_the_cards_are_built_from_the_current_sources():
    out = subprocess.run([sys.executable, "scripts/build_game.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_every_card_agrees_with_the_check():
    for card in GAME["cards"]:
        verdict = check_message(card["text"], sender=card["sender"], input_type=card["input_type"])["verdict"]
        assert verdict == ("scam" if card["truth"] == "scam" else "no_signs"), card["id"]


def test_every_badge_can_be_earned_and_a_round_can_be_dealt():
    badges = GAME["badges"]
    assert len(badges) == 8 and "real" in badges
    for badge in badges:
        assert sum(c["badge"] == badge for c in GAME["cards"]) >= 3, badge  # three right answers earn a badge
    assert sum(c["truth"] == "genuine" for c in GAME["cards"]) >= 5
    assert len({c["id"] for c in GAME["cards"]}) == len(GAME["cards"])


def test_the_app_knows_every_badge():
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    for badge in GAME["badges"]:
        assert f'"{badge}"' in app and f"badge_{badge}:" in app and f"badge_{badge}_d:" in app, badge
