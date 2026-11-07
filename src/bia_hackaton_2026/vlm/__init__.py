"""Vision module: image description via Groq VLM."""
from .describe import build_agent_input, describe_image

__all__ = ["describe_image", "build_agent_input"]
