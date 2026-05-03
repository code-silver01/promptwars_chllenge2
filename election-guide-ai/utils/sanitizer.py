"""
sanitizer.py — Input Sanitization Module
=========================================
Provides defence-in-depth sanitisation for all user-supplied text.
Layers:
  1. Strip HTML/script tags via bleach
  2. Reject SQL injection patterns
  3. Escape remaining special characters
  4. Enforce maximum character length
"""

import re
import bleach


# ── SQL injection patterns to reject ─────────────────────────
# Compiled once at module level for performance
_SQL_PATTERNS: re.Pattern = re.compile(
    r"\b(DROP|SELECT|INSERT|DELETE|UPDATE|ALTER|UNION|EXEC|EXECUTE|TRUNCATE)\b"
    r"|--"           # SQL single-line comment
    r"|;[\s]*$"      # trailing semicolons
    r"|/\*.*?\*/"    # SQL block comments
    r"|'[\s]*OR[\s]+'",  # classic OR-based injection
    re.IGNORECASE,
)

# ── HTML entity escape map ───────────────────────────────────
_ESCAPE_MAP: dict[str, str] = {
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    '"': "&quot;",
    "'": "&#x27;",
}

# Maximum allowed message length (chars)
MAX_INPUT_LENGTH: int = 500


def sanitize_input(raw: str) -> str:
    """
    Sanitise user input through a multi-step pipeline.

    Args:
        raw: The raw user-supplied string.

    Returns:
        A cleaned, safe string ready for downstream processing.

    Raises:
        ValueError: If the input contains SQL injection patterns.
    """
    # Step 1 — Strip all HTML tags (bleach removes scripts, iframes, etc.)
    cleaned: str = bleach.clean(raw, tags=[], attributes={}, strip=True)

    # Step 2 — Reject SQL injection attempts
    if _SQL_PATTERNS.search(cleaned):
        raise ValueError("Input contains potentially malicious patterns.")

    # Step 3 — Escape remaining special characters
    for char, entity in _ESCAPE_MAP.items():
        cleaned = cleaned.replace(char, entity)

    # Step 4 — Truncate to maximum allowed length
    cleaned = cleaned[:MAX_INPUT_LENGTH].strip()

    return cleaned
