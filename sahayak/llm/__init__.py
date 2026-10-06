"""Local LLM backends behind one interface (Ollama, OpenAI-style servers, or none)."""

from .backend import LLMResult, LLMUnavailable, get_backend

__all__ = ["LLMResult", "LLMUnavailable", "get_backend"]
