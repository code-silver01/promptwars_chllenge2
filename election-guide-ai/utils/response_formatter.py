"""
response_formatter.py — Response Formatting Utilities
=====================================================
Converts raw AI-generated text into structured, user-friendly
responses with numbered steps, bullet points, and emoji headers.
"""

import re


def format_response(text: str) -> str:
    """
    Post-process the Gemini response to ensure consistent formatting.

    Applies:
      - Normalise line breaks (collapse 3+ newlines into 2)
      - Ensure numbered lists use consistent formatting
      - Trim trailing whitespace per line

    Args:
        text: Raw response string from Gemini.

    Returns:
        A cleanly formatted response string.
    """
    # Collapse excessive blank lines (3+ newlines → 2)
    formatted: str = re.sub(r"\n{3,}", "\n\n", text)

    # Normalise numbered-list formats: "1)" or "1-" → "1."
    formatted = re.sub(r"^(\d+)[)\-]\s", r"\1. ", formatted, flags=re.MULTILINE)

    # Strip trailing whitespace on every line
    formatted = "\n".join(line.rstrip() for line in formatted.splitlines())

    return formatted.strip()


def build_step_response(step_number: int, title: str, details: list[str]) -> str:
    """
    Build a single guided-flow step as a formatted string.

    Args:
        step_number: The 1-based step index.
        title:       Emoji-prefixed step title.
        details:     List of bullet-point strings.

    Returns:
        Formatted step string ready for the chat UI.
    """
    bullets: str = "\n".join(f"  • {d}" for d in details)
    return f"**Step {step_number} — {title}**\n{bullets}"
