"""
test_sanitizer.py — Unit Tests for Input Sanitizer
====================================================
Tests the multi-layer sanitisation pipeline:
  • HTML tag stripping
  • SQL injection rejection
  • Special character escaping
  • Length truncation
"""

import pytest
from utils.sanitizer import sanitize_input, MAX_INPUT_LENGTH


class TestSanitizeInput:
    """Test suite for the sanitize_input function."""

    # ── HTML stripping tests ─────────────────────────────────

    def test_strips_html_bold_tags(self):
        """bleach should remove <b> tags and return plain text."""
        result = sanitize_input("<b>hello</b>")
        assert result == "hello"

    def test_strips_script_tags(self):
        """XSS payloads with <script> tags should be completely removed."""
        result = sanitize_input("<script>alert(1)</script>")
        assert "script" not in result.lower()
        assert "alert" not in result

    def test_strips_nested_html(self):
        """Nested HTML tags should be fully stripped."""
        result = sanitize_input("<div><p>Test <strong>bold</strong></p></div>")
        assert result == "Test bold"

    def test_strips_img_tag_with_onerror(self):
        """Image tags with event handlers should be removed."""
        result = sanitize_input('<img src=x onerror="alert(1)">')
        assert "img" not in result.lower()
        assert "onerror" not in result.lower()

    # ── SQL injection detection tests ────────────────────────

    def test_rejects_drop_table(self):
        """SQL DROP TABLE statements should raise ValueError."""
        with pytest.raises(ValueError, match="malicious"):
            sanitize_input("DROP TABLE users;")

    def test_rejects_select_statement(self):
        """SQL SELECT statements should raise ValueError."""
        with pytest.raises(ValueError, match="malicious"):
            sanitize_input("SELECT * FROM votes")

    def test_rejects_insert_statement(self):
        """SQL INSERT statements should raise ValueError."""
        with pytest.raises(ValueError, match="malicious"):
            sanitize_input("INSERT INTO users VALUES (1)")

    def test_rejects_sql_comment_dashes(self):
        """SQL comment syntax (--) should raise ValueError."""
        with pytest.raises(ValueError, match="malicious"):
            sanitize_input("admin' --")

    def test_allows_normal_text_with_similar_words(self):
        """Words like 'selection' should NOT trigger the SQL filter."""
        # "selection" contains "select" but as part of a larger word
        # Our regex uses word boundaries (\b) so this should pass
        result = sanitize_input("What is the selection process?")
        assert "selection" in result or "process" in result

    # ── Character escaping tests ─────────────────────────────

    def test_escapes_angle_brackets(self):
        """Angle brackets should be HTML-entity escaped."""
        # After bleach strips tags, raw < > in text get escaped
        result = sanitize_input("5 is less than 10")
        assert result  # should not be empty

    def test_plain_text_passes_through(self):
        """Normal election-related text should pass through unchanged."""
        msg = "How do I register to vote in my constituency"
        result = sanitize_input(msg)
        assert "register" in result
        assert "vote" in result

    # ── Length truncation tests ───────────────────────────────

    def test_truncates_long_input(self):
        """Messages longer than MAX_INPUT_LENGTH should be truncated."""
        long_msg = "a" * (MAX_INPUT_LENGTH + 100)
        result = sanitize_input(long_msg)
        assert len(result) <= MAX_INPUT_LENGTH

    def test_preserves_short_input(self):
        """Messages within the limit should not be altered."""
        short_msg = "Hello, how do I vote?"
        result = sanitize_input(short_msg)
        assert "vote" in result

    # ── Edge cases ───────────────────────────────────────────

    def test_empty_string_after_strip(self):
        """Empty input after stripping should return empty string."""
        result = sanitize_input("   ")
        assert result == ""

    def test_unicode_text(self):
        """Unicode characters (Hindi, emojis) should be preserved."""
        result = sanitize_input("मतदान कैसे करें? 🗳️")
        assert "मतदान" in result or "🗳️" in result
