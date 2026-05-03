"""
chat_controller.py — Chat Request Orchestrator
================================================
Coordinates the full lifecycle of a chat request:
  1. Sanitise user input
  2. Detect intent (guided flow or free-form)
  3. If guided → return pre-built wizard step
  4. If general → forward to Gemini and format response
"""

import logging

from utils.sanitizer import sanitize_input
from services.intent_service import detect_intent, get_guided_step, IntentResult
from services.gemini_service import call_gemini

# ── Logger ───────────────────────────────────────────────────
logger = logging.getLogger(__name__)


async def handle_chat(message: str, session_id: str, lang: str = "en") -> dict:
    """
    Process a single chat request end-to-end.

    Args:
        message:    Raw user message (will be sanitised).
        session_id: Client-supplied session identifier.
        lang:       Language code (reserved for future i18n support).

    Returns:
        dict with keys: reply (str), intent (str), guided_step (int|None).
    """
    # Step 1 — Sanitise the input (raises ValueError on SQL injection)
    clean_message: str = sanitize_input(message)

    # Step 2 — Detect the user's intent
    intent_result: IntentResult = detect_intent(clean_message)

    # Step 3a — Guided flow: "voting_process" triggers wizard step 1
    if intent_result.intent == "voting_process":
        guided = get_guided_step(1)
        return {
            "reply": guided.reply,
            "intent": guided.intent,
            "guided_step": guided.guided_step,
        }

    # Step 3b — Specific intents that benefit from Gemini's depth
    # Forward the sanitised message to Gemini with the intent context
    try:
        ai_reply: str = await call_gemini(clean_message)
    except RuntimeError as e:
        logger.error("Gemini service error for session %s: %s", session_id, e)
        ai_reply = (
            "I'm sorry, I'm having trouble connecting to the AI service right now. "
            "Please try again in a moment."
        )

    return {
        "reply": ai_reply,
        "intent": intent_result.intent,
        "guided_step": None,
    }


async def handle_guided_step(step: int) -> dict:
    """
    Return a specific guided wizard step by number.

    Args:
        step: Step number (1-4).

    Returns:
        dict with reply, intent, and guided_step fields.

    Raises:
        ValueError: If step is out of the 1-4 range.
    """
    guided = get_guided_step(step)
    return {
        "reply": guided.reply,
        "intent": guided.intent,
        "guided_step": guided.guided_step,
    }
