"""Fraud-Shield: scam check for messages, screenshots, QR codes and call descriptions."""

from .pipeline import check_message

__all__ = ["check_message"]
