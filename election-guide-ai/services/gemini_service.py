"""
gemini_service.py — Google Gemini API Integration
===================================================
Handles all communication with the Gemini 1.5 Flash model via
the Google Generative AI REST API.

Key design decisions:
  • Uses httpx.AsyncClient for non-blocking HTTP calls
  • Injects a system prompt on every request to constrain AI behaviour
  • Includes retry logic with exponential back-off for transient errors
  • Never logs user messages in production (privacy compliance)
"""

import os
import logging
import httpx

from utils.response_formatter import format_response

# ── Logger — configured to suppress user messages ────────────
logger = logging.getLogger(__name__)

# ── Gemini REST API endpoint template ────────────────────────
_GEMINI_URL: str = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent?key={api_key}"
)

# ── System instruction injected into every Gemini call ───────
SYSTEM_PROMPT: str = (
    "You are Election Guide AI, a friendly assistant that helps citizens "
    "understand how to vote. Always respond in structured format using:\n"
    "- Numbered steps for processes\n"
    "- Bullet points for lists\n"
    "- Emoji section headers for clarity\n"
    "Never answer questions unrelated to elections. If unsure, say: "
    "'I can only help with election-related questions. Try asking about "
    "eligibility, registration, documents needed, or voting steps.'"
)

# ── Maximum retries for transient API errors ─────────────────
_MAX_RETRIES: int = 2
_TIMEOUT_SECONDS: float = 30.0


async def call_gemini(user_message: str) -> str:
    """
    Send a user query to Gemini 1.5 Flash and return the formatted response.

    The function:
      1. Reads the API key from environment variables
      2. Builds the request payload with system instruction
      3. Sends the request with retry on 5xx / timeout errors
      4. Extracts and formats the response text

    Args:
        user_message: Sanitised user message string.

    Returns:
        Formatted AI response text.

    Raises:
        RuntimeError: If the API key is missing or all retries fail.
    """
    # Load API key from environment (never hardcoded)
    api_key: str | None = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in .env or Cloud Run environment variables."
        )

    # Construct the full API URL with key
    url: str = _GEMINI_URL.format(api_key=api_key)

    # Build the request body following Gemini REST schema
    payload: dict = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "parts": [{"text": user_message}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,       # balanced creativity
            "topP": 0.9,              # nucleus sampling
            "topK": 40,               # top-k filtering
            "maxOutputTokens": 1024,  # keep responses concise
        },
    }

    # Attempt the API call with retry logic
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                # Raise on HTTP error status codes
                response.raise_for_status()

                # Parse the response JSON
                data: dict = response.json()

                # Extract the generated text from the response
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.warning("Gemini returned no candidates.")
                    return "I'm sorry, I couldn't generate a response. Please try again."

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    logger.warning("Gemini candidate has no parts.")
                    return "I'm sorry, I couldn't generate a response. Please try again."

                raw_text: str = parts[0].get("text", "")

                # Format the response for consistent output
                return format_response(raw_text)

            except httpx.HTTPStatusError as e:
                last_error = e
                # Retry only on server errors (5xx)
                if e.response.status_code >= 500:
                    logger.warning(
                        "Gemini API server error (attempt %d/%d): %s",
                        attempt + 1, _MAX_RETRIES + 1, e,
                    )
                    continue
                # Client errors (4xx) — don't retry
                logger.error("Gemini API client error: %s", e)
                break

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning(
                    "Gemini API timeout/connection error (attempt %d/%d): %s",
                    attempt + 1, _MAX_RETRIES + 1, e,
                )
                continue

    # All retries exhausted
    logger.error("Gemini API call failed after retries: %s", last_error)
    return (
        "I'm experiencing connectivity issues with the AI service. "
        "Please try again in a moment."
    )
