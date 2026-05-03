"""
intent_service.py — Intent Detection & Guided Flow Engine
==========================================================
Detects user intent from the chat message and, when a guided-flow
intent is matched, returns structured wizard step data instead of
forwarding the query to Gemini.

Supported intents:
  • start_guide / voting_process  → 4-step guided wizard
  • check_eligibility             → eligibility info
  • registration                  → registration steps
  • documents_needed              → document checklist
  • election_timeline             → timeline data
  • general                       → pass-through to Gemini
"""

import re
from dataclasses import dataclass, field


# ── Data class for a detected intent result ──────────────────
@dataclass
class IntentResult:
    """Encapsulates the outcome of intent detection."""
    intent: str                          # canonical intent name
    reply: str | None = None             # pre-built reply (if guided)
    guided_step: int | None = None       # current wizard step (1-4)
    is_guided: bool = False              # True → skip Gemini call


# ── Keyword → intent mapping ────────────────────────────────
# Each tuple: (compiled regex pattern, intent name)
_INTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(start.?guide|guide\s*me|how\s*to\s*vote|voting\s*process)\b", re.I), "voting_process"),
    (re.compile(r"\b(eligib|am\s*i\s*eligible|can\s*i\s*vote|check\s*eligibility)\b", re.I), "check_eligibility"),
    (re.compile(r"\b(register|registration|sign\s*up\s*to\s*vote|enrol)\b", re.I), "registration"),
    (re.compile(r"\b(document|id\s*card|voter\s*id|aadhaar|passport|what\s*do\s*i\s*need)\b", re.I), "documents_needed"),
    (re.compile(r"\b(timeline|schedule|when|dates|election\s*day)\b", re.I), "election_timeline"),
]


# ── Guided wizard steps (returned as structured chat messages) ──
GUIDED_STEPS: dict[int, dict] = {
    1: {
        "title": "✅ Check Eligibility",
        "details": [
            "Must be 18+ years old on the qualifying date",
            "Must be a citizen of the country",
            "Must not be disqualified by any court order",
            "Must be of sound mind and not declared so by a competent court",
        ],
        "button": "I'm eligible → Next",
    },
    2: {
        "title": "📋 Register to Vote",
        "details": [
            "Visit your local election commission website or office",
            "Fill out Form 6 (for new voter registration)",
            "Submit with proof of age (birth certificate / 10th marksheet)",
            "Submit with proof of address (utility bill / Aadhaar)",
            "Deadline: typically 30 days before the election date",
        ],
        "button": "I've registered → Next",
    },
    3: {
        "title": "📄 Prepare Documents",
        "details": [
            "Primary: Voter ID Card (EPIC)",
            "Alternative: Aadhaar Card",
            "Alternative: Passport",
            "Alternative: PAN Card",
            "Alternative: Driving Licence",
            "Alternative: MNREGA Job Card",
            "⚠️ Carry originals only — photocopies are NOT accepted",
        ],
        "button": "I have documents → Next",
    },
    4: {
        "title": "🗳️ Vote on Election Day",
        "details": [
            "Locate your polling booth at voterportal.eci.gov.in",
            "Arrive during polling hours (typically 7 AM – 5 PM)",
            "Show your photo ID to the presiding officer",
            "Get the indelible ink mark on your left index finger",
            "Cast your vote on the Electronic Voting Machine (EVM)",
            "🎉 Congratulations — you've exercised your democratic right!",
        ],
        "button": "Complete Guide ✓",
    },
}


def detect_intent(message: str) -> IntentResult:
    """
    Analyse the user message and return the detected intent.

    Args:
        message: Sanitised user message text.

    Returns:
        IntentResult with the matched intent and optional guided data.
    """
    # Try each pattern in priority order
    for pattern, intent_name in _INTENT_PATTERNS:
        if pattern.search(message):
            return IntentResult(intent=intent_name)

    # No pattern matched — fall through to Gemini
    return IntentResult(intent="general")


def get_guided_step(step: int) -> IntentResult:
    """
    Return the guided wizard data for a specific step number.

    Args:
        step: Step number (1-4).

    Returns:
        IntentResult with the formatted reply and step metadata.

    Raises:
        ValueError: If step is out of range.
    """
    if step not in GUIDED_STEPS:
        raise ValueError(f"Invalid guided step: {step}. Must be 1-4.")

    data = GUIDED_STEPS[step]

    # Build a formatted reply string for the chat UI
    bullets = "\n".join(f"  • {d}" for d in data["details"])
    reply = f"**Step {step} — {data['title']}**\n\n{bullets}"

    return IntentResult(
        intent="voting_process",
        reply=reply,
        guided_step=step,
        is_guided=True,
    )
