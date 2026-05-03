"""
test_chat.py — Integration & Unit Tests for Chat API
======================================================
Tests cover:
  • POST /api/chat — valid, empty, oversized, XSS payloads
  • GET /health — status check
  • Intent detection accuracy
  • Guided step retrieval
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from main import app
from services.intent_service import detect_intent, get_guided_step


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    """Use asyncio as the async test backend."""
    return "asyncio"


@pytest.fixture
async def client():
    """Create an async HTTP test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ── Health endpoint tests ────────────────────────────────────

class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Health check should return 200 with status='ok'."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


# ── Chat endpoint tests ─────────────────────────────────────

class TestChatEndpoint:
    """Tests for POST /api/chat."""

    @pytest.mark.asyncio
    @patch("controllers.chat_controller.call_gemini", new_callable=AsyncMock)
    async def test_valid_message_returns_reply(self, mock_gemini, client):
        """A valid chat message should return 200 with a reply field."""
        mock_gemini.return_value = "Here is how to vote..."
        response = await client.post("/api/chat", json={
            "message": "How do I vote?",
            "session_id": "test123",
            "lang": "en",
        })
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "intent" in data
        assert len(data["reply"]) > 0

    @pytest.mark.asyncio
    async def test_empty_message_returns_422(self, client):
        """An empty message should fail Pydantic validation (422)."""
        response = await client.post("/api/chat", json={
            "message": "",
            "session_id": "test123",
            "lang": "en",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_message_field_returns_422(self, client):
        """A request body missing the 'message' field should return 422."""
        response = await client.post("/api/chat", json={
            "session_id": "test123",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_oversized_message_returns_422(self, client):
        """A message exceeding 500 characters should return 422."""
        long_message = "a" * 501
        response = await client.post("/api/chat", json={
            "message": long_message,
            "session_id": "test123",
            "lang": "en",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("controllers.chat_controller.call_gemini", new_callable=AsyncMock)
    async def test_xss_payload_is_sanitized(self, mock_gemini, client):
        """XSS payloads should be sanitised — no <script> in response."""
        mock_gemini.return_value = "I can help with elections."
        response = await client.post("/api/chat", json={
            "message": "<script>alert(1)</script>How to vote?",
            "session_id": "test123",
            "lang": "en",
        })
        # Should either succeed (with sanitised input) or return 200
        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in data.get("reply", "")

    @pytest.mark.asyncio
    async def test_guided_flow_trigger(self, client):
        """Messages matching 'how to vote' should trigger guided flow."""
        response = await client.post("/api/chat", json={
            "message": "How to vote",
            "session_id": "test123",
            "lang": "en",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "voting_process"
        assert data["guided_step"] == 1


# ── Intent detection tests ───────────────────────────────────

class TestIntentDetection:
    """Tests for the intent_service.detect_intent function."""

    def test_how_to_vote_intent(self):
        """'how do I vote' should map to voting_process intent."""
        result = detect_intent("how do I vote")
        assert result.intent == "voting_process"

    def test_eligibility_intent(self):
        """'check eligibility' should map to check_eligibility intent."""
        result = detect_intent("Am I eligible to vote?")
        assert result.intent == "check_eligibility"

    def test_registration_intent(self):
        """'register' should map to registration intent."""
        result = detect_intent("How do I register to vote?")
        assert result.intent == "registration"

    def test_documents_intent(self):
        """'documents' should map to documents_needed intent."""
        result = detect_intent("What documents do I need?")
        assert result.intent == "documents_needed"

    def test_timeline_intent(self):
        """'timeline' should map to election_timeline intent."""
        result = detect_intent("What is the election timeline?")
        assert result.intent == "election_timeline"

    def test_general_intent_fallback(self):
        """Unrecognised messages should fall back to general intent."""
        result = detect_intent("Tell me a joke")
        assert result.intent == "general"

    def test_guide_me_intent(self):
        """'guide me' should map to voting_process intent."""
        result = detect_intent("guide me through the process")
        assert result.intent == "voting_process"


# ── Guided step tests ────────────────────────────────────────

class TestGuidedSteps:
    """Tests for the guided wizard step retrieval."""

    def test_step_1_returns_eligibility(self):
        """Step 1 should contain eligibility information."""
        result = get_guided_step(1)
        assert result.guided_step == 1
        assert "Eligibility" in result.reply
        assert result.is_guided is True

    def test_step_4_returns_voting_day(self):
        """Step 4 should contain voting day information."""
        result = get_guided_step(4)
        assert result.guided_step == 4
        assert "Vote" in result.reply or "Election Day" in result.reply

    def test_invalid_step_raises_error(self):
        """Step numbers outside 1-4 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid guided step"):
            get_guided_step(5)

    def test_step_0_raises_error(self):
        """Step 0 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid guided step"):
            get_guided_step(0)


# ── Security header tests ───────────────────────────────────

class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    @pytest.mark.asyncio
    async def test_security_headers_on_health(self, client):
        """GET /health should include security headers."""
        response = await client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
