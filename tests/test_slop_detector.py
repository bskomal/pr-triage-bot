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
