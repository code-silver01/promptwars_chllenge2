"""
chat.py — Chat API Route
==========================
Defines the POST /api/chat endpoint with:
  • Pydantic request/response validation
  • Rate limiting (20 req/min per session_id via slowapi)
  • Structured JSON responses
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from controllers.chat_controller import handle_chat, handle_guided_step

# ── Rate limiter — keyed by session_id from request body ─────
limiter = Limiter(key_func=get_remote_address)

# ── Router instance ──────────────────────────────────────────
router = APIRouter(prefix="/api", tags=["Chat"])


# ── Request / Response schemas ───────────────────────────────
class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User message text (1-500 characters).",
        examples=["How do I register to vote?"],
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique session identifier for rate limiting.",
        examples=["sess_abc123"],
    )
    lang: str = Field(
        default="en",
        max_length=5,
        description="Language code (reserved for future i18n).",
        examples=["en"],
    )


class ChatResponse(BaseModel):
    """Structured response returned to the frontend."""
    reply: str = Field(..., description="AI-generated response text.")
    intent: str = Field(..., description="Detected user intent.")
    guided_step: int | None = Field(
        None,
        description="Current wizard step (1-4) or null for free-form.",
    )


class GuidedStepRequest(BaseModel):
    """Request a specific guided wizard step."""
    step: int = Field(
        ...,
        ge=1,
        le=4,
        description="Step number (1-4) of the guided voting wizard.",
    )


# ── Endpoints ────────────────────────────────────────────────
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="Process a user message through intent detection and Gemini AI.",
)
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint. Processes the user message through:
      1. Input validation (Pydantic)
      2. Rate limiting (slowapi — 20 req/min per IP)
      3. Sanitisation + Intent detection + AI response

    Returns a structured response with the reply, intent, and
    optional guided step indicator.
    """
    try:
        result: dict = await handle_chat(
            message=body.message,
            session_id=body.session_id,
            lang=body.lang,
        )
        return ChatResponse(**result)
    except ValueError as e:
        # Sanitiser rejected the input (SQL injection, etc.)
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/guided-step",
    response_model=ChatResponse,
    summary="Get a guided wizard step",
    description="Returns the content for a specific step of the voting guide.",
)
@limiter.limit("20/minute")
async def guided_step_endpoint(
    request: Request, body: GuidedStepRequest
) -> ChatResponse:
    """
    Returns guided wizard step content by step number (1-4).
    Used by the frontend wizard navigation buttons.
    """
    try:
        result: dict = await handle_guided_step(step=body.step)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
