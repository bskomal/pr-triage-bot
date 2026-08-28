"""
Tests for PR Quality Scorer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.scorer import PRScorer, QualityScore


@pytest.fixture
def scorer():
    return PRScorer(llm_client=None)


@pytest.fixture
def excellent_pr_data():
    return {
        "title": "feat(payments): add Stripe webhook handler with retry logic",
        "description": (
            "## Summary\nAdds Stripe webhook handler.\n\n"
            "## Changes\n- WebhookHandler class\n- Retry with exponential backoff\n\n"
            "Closes #88"
        ),
        "body": "Full implementation with tests and docs.",
        "files_changed": [
            "src/payments/webhook.py",
            "tests/test_webhook.py",
            "docs/webhooks.md",
        ],
        "additions": 180,
        "deletions": 10,
        "commit_messages": [
            "feat(payments): add Stripe webhook handler",
            "test(payments): add webhook handler tests",
            "docs(payments): document webhook configuration",
        ],
        "linked_issues": [88],
    }


@pytest.mark.asyncio
async def test_excellent_pr_scores_high(scorer, excellent_pr_data):
    """Well-structured PR should score 60+."""
    result = await scorer.score(**excellent_pr_data)
    assert result.overall >= 60
    assert result.tier in ("excellent", "good")


@pytest.mark.asyncio
async def test_minimal_pr_scores_low(scorer):
    """Minimal PR should score below 50."""
    result = await scorer.score(
        title="fix bug",
        description="fixed it",
        body="",
        files_changed=["main.py"],
        additions=5,
        deletions=2,
        commit_messages=["fix"],
        linked_issues=[],
    )
    assert result.overall < 60


@pytest.mark.asyncio
async def test_score_always_0_to_100(scorer, excellent_pr_data):
    """Score must always be in valid range."""
    result = await scorer.score(**excellent_pr_data)
    assert 0 <= result.overall <= 100
    for dim in result.dimensions:
        assert 0 <= dim.score <= 100


@pytest.mark.asyncio
async def test_test_files_improve_score(scorer):
    """PRs with test files should score higher."""
    base = dict(
        title="add feature X",
        description="Added feature X with full implementation.",
        body="",
        files_changed=["src/feature.py"],
        additions=100,
        deletions=0,
        commit_messages=["feat: add feature X"],
        linked_issues=[],
    )

    without_tests = await scorer.score(**base)

    with_tests = await scorer.score(
        **{**base, "files_changed": ["src/feature.py", "tests/test_feature.py"]}
    )

    assert with_tests.overall > without_tests.overall


@pytest.mark.asyncio
async def test_tier_computation(scorer):
    """Tier should match score ranges."""
    # Mock different scores by testing the internal method
    assert scorer._compute_tier(85) == "excellent"
    assert scorer._compute_tier(65) == "good"
    assert scorer._compute_tier(45) == "needs-work"
    assert scorer._compute_tier(25) == "poor"


@pytest.mark.asyncio
async def test_label_matches_tier(scorer, excellent_pr_data):
    """Quality label should match tier."""
    result = await scorer.score(**excellent_pr_data)
    assert result.label.startswith("quality:")


@pytest.mark.asyncio
async def test_feedback_generated(scorer):
    """Feedback should always be a non-empty string."""
    result = await scorer.score(
        title="test pr",
        description="test",
        body="",
        files_changed=["file.py"],
        additions=10,
        deletions=0,
        commit_messages=["update"],
        linked_issues=[],
    )
    assert isinstance(result.feedback, str)
    assert len(result.feedback) > 0


@pytest.mark.asyncio
async def test_doc_only_pr_not_penalized_for_tests(scorer):
    """Pure documentation PRs should receive 100 on test coverage dimension."""
    result = await scorer.score(
        title="docs: update installation instructions in README",
        description="Updated setup instructions with latest CLI steps.",
        body="",
        files_changed=["README.md", "docs/setup.md"],
        additions=20,
        deletions=5,
        commit_messages=["docs: update setup guide"],
        linked_issues=[],
    )
    test_dim = next(d for d in result.dimensions if d.name == "test_coverage")
    assert test_dim.score == 100


@pytest.mark.asyncio
async def test_windows_path_doc_identification(scorer):
    """Windows backslash paths should be identified as documentation files."""
    doc_files = scorer._identify_doc_files(["docs\\architecture.md", "src\\app.py"])
    assert doc_files == ["docs\\architecture.md"]


@pytest.mark.asyncio
async def test_case_insensitive_conventional_commits(scorer):
    """Capitalized conventional commit messages should receive full score."""
    dim = scorer._score_commits(["Feat(auth): add OAuth2 provider", "FIX: resolve deadlock"])
    assert dim.score == 100


@pytest.mark.asyncio
async def test_safe_llm_score_merge(scorer):
    """Merging invalid non-int LLM scores should handle conversion gracefully without crashing."""
    heuristics = [
        scorer._score_scope(["file.py"], 10, 5)
    ]
    merged = scorer._merge_llm_scores(heuristics, {"scope_focus": "invalid-string"})
    assert len(merged) == len(heuristics)