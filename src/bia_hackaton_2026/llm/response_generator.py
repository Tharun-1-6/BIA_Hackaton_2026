"""Backwards-compatible import path (main.py uses it). Code now lives in prompt.py and response.py."""
from bia_hackaton_2026.llm.prompt import SYSTEM_PROMPT, build_system_prompt
from bia_hackaton_2026.llm.response import MODEL, MODELS, ask_llm

__all__ = ["ask_llm", "MODEL", "MODELS", "SYSTEM_PROMPT", "build_system_prompt"]
