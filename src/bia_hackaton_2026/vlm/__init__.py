"""Vision module: image description via Groq VLM, cross-checked by Gemini."""
from .describe import build_agent_input, describe_image
from .verify import describe_verified

__all__ = ["describe_image", "describe_verified", "build_agent_input"]
