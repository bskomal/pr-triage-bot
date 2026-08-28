"""
Tests for AI Slop Detector.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.slop_detector import SlopDetector, SlopResult, SlopSignal


@pytest.fixture
def detector():
    return SlopDetector(llm_client=None, threshold=0.6)


@pytest.mark.asyncio
async def test_clean_pr_not_flagged_as_slop(detector):
    """High quality PR should not trigger slop heuristics."""
    result = await detector.analyze(
        title="fix(auth): resolve token refresh race condition on logout",
        description=(
            "## Description\n"
            "Fixes a race condition where double clicking logout causes expired token error.\n\n"
            "## Fix\n"
            "Added atomic token revocation lock.\n\n"
            "Closes #42"
        ),
        commit_messages=[
            "fix(auth): add lock to token revocation",
            "test(auth): add race condition test case",
        ],
        diff_sample="diff --git a/auth.py b/auth.py\n+ lock.acquire()",
        files_changed=["src/auth.py", "tests/test_auth.py"],
    )

    assert not result.is_suspected_slop
    assert result.confidence < 0.6
    assert result.severity == "low"


@pytest.mark.asyncio
async def test_slop_pr_flagged(detector):
    """Low quality / AI slop PR with generic messages and phrasing should be flagged."""
    result = await detector.analyze(
        title="update code",
        description=(
            "As an AI language model, I hope this helps. "
            "Please describe the changes you made in order to achieve cutoff."
        ),
        commit_messages=["fix", "update"],
        diff_sample="",
        files_changed=["main.py"],
    )

    assert result.is_suspected_slop
    assert result.confidence >= 0.6
    assert result.severity in ("medium", "high")


@pytest.mark.asyncio
async def test_slop_result_properties():
    """SlopResult helper properties should calculate correctly."""
    signals = [
        SlopSignal(name="generic_title", detected=True, weight=0.4),
        SlopSignal(name="no_tests", detected=False, weight=0.3),
    ]
    result = SlopResult(
        is_suspected_slop=True,
        confidence=0.8,
        severity="high",
        signals=signals,
    )

    assert result.signal_names == ["generic_title"]
    assert 0.0 <= result.heuristic_score <= 1.0


@pytest.mark.asyncio
async def test_explicit_ai_phrase_triggers_signal(detector):
    """A single explicit AI self-identification phrase should trigger the AI phrase signal."""
    check = detector._check_ai_phrases("As an AI language model, here are the requested changes.")
    assert check["detected"] is True


@pytest.mark.asyncio
async def test_doc_pr_does_not_trigger_no_tests_signal(detector):
    """PRs modifying only documentation files should not trigger no_tests_added signal."""
    check = detector._check_no_tests(["README.md", "docs/architecture.md"])
    assert check["detected"] is False


@pytest.mark.asyncio
async def test_diff_header_lines_excluded_from_whitespace_check(detector):
    """Diff header lines starting with +++ or --- should not count as whitespace changes."""
    diff_sample = (
        "--- a/src/app.py\n"
        "+++ b/src/app.py\n"
        "+    valid_code_line = True\n"
        "+    another_code_line = 10"
    )
    check = detector._check_whitespace_changes(diff_sample)
    assert check["detected"] is False


@pytest.mark.asyncio
async def test_string_llm_confidence_handled_safely():
    """String outputs for confidence from LLM should be safely converted to float."""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=MagicMock(parsed={
        "confidence": "0.85",
        "signals_found": ["generic_description"],
        "explanation": "Test explanation"
    }))
    detector_with_llm = SlopDetector(llm_client=mock_llm, threshold=0.6)
    result = await detector_with_llm.analyze(
        title="update code",
        description="As an AI assistant, I updated the code",
        commit_messages=["update"],
        diff_sample="+ code",
        files_changed=["app.py"]
    )
    assert isinstance(result.confidence, float)
    assert result.confidence > 0.5

