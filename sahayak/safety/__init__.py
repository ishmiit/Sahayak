"""Safety gate applied to every answer before it is shown or spoken."""

from .gate import GateResult, check_card_text, check_texts

__all__ = ["GateResult", "check_card_text", "check_texts"]
