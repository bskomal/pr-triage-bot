"""
Tests for Core Analyzer.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.analyzer import Analyzer, PRAnalysisResult, IssueAnalysisResult
from src.github.client import PRData, IssueData


@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.complete = AsyncMock(return_value=MagicMock(parsed={
        "type": "bug",
        "priority": "critical",
        "complexity": "small",
        "confidence": 0.9,
        "reasoning": "Fixes critical crash",
    }))
    return client


@pytest.fixture
def mock_github():
    client = MagicMock()
    client._repo_name = "owner/repo"
    client.get_pr_diff_sample = MagicMock(return_value="+ diff content")
    client.add_labels = MagicMock(return_value=True)
    client.post_comment = MagicMock(return_value=True)
    return client


@pytest.fixture
def sample_pr():
    return PRData(
        number=101,
        title="fix(core): resolve null pointer exception in logger",
        description="## Description\nFixes NPE crash on startup.\n\nCloses #10",
        body="Full description body",
        author="contributor1",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        state="open",
        draft=False,
        files_changed=["src/core/logger.py", "tests/test_logger.py"],
        additions=15,
        deletions=2,
        commit_messages=["fix(core): fix NPE in logger"],
        linked_issues=[10],
        existing_labels=[],
        url="https://github.com/owner/repo/pull/101",
        head_sha="abcdef123456",
    )


@pytest.fixture
def sample_issue():
    return IssueData(
        number=10,
        title="App crashes on startup with NPE",
        body="App throws NullPointerException when starting without config.",
        author="user1",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        state="open",
        labels=[],
        comments_count=1,
        url="https://github.com/owner/repo/issues/10",
    )


@pytest.mark.asyncio
async def test_analyzer_analyze_pr(mock_llm, mock_github, sample_pr):
    """PR analysis should successfully produce PRAnalysisResult and apply labels."""
    analyzer = Analyzer(llm_client=mock_llm, github_client=mock_github, dry_run=False)

    with patch.object(analyzer.supabase, "insert", new_callable=AsyncMock) as mock_insert, \
         patch.object(analyzer, "_update_repo_stats", new_callable=AsyncMock):
        mock_insert.return_value = True
        result = await analyzer.analyze_pr(sample_pr)

    assert isinstance(result, PRAnalysisResult)
    assert result.pr.number == 101
    assert "type: bug" in result.recommended_labels
    assert "priority: critical" in result.recommended_labels
    mock_github.add_labels.assert_called_once()


@pytest.mark.asyncio
async def test_analyzer_pr_error_resilience(mock_llm, mock_github, sample_pr):
    """Parallel PR analysis should handle errors in one module gracefully without crashing."""
    analyzer = Analyzer(llm_client=mock_llm, github_client=mock_github, dry_run=True)

    with patch.object(analyzer.scorer, "score", side_effect=RuntimeError("Scorer error")), \
         patch.object(analyzer.supabase, "insert", new_callable=AsyncMock):
        result = await analyzer.analyze_pr(sample_pr)

    assert isinstance(result, PRAnalysisResult)
    assert result.quality_score.overall == 50


@pytest.mark.asyncio
async def test_compute_stats_excludes_slop_from_critical(mock_llm, mock_github):
    """_compute_stats should exclude flagged slop PRs from critical_prs count."""
    analyzer = Analyzer(llm_client=mock_llm, github_client=mock_github, dry_run=True)

    clean_critical_pr = MagicMock(
        classification={"priority": "critical"},
        slop_result=MagicMock(is_suspected_slop=False),
        quality_score=MagicMock(overall=85, tier="excellent")
    )
    slop_critical_pr = MagicMock(
        classification={"priority": "critical"},
        slop_result=MagicMock(is_suspected_slop=True),
        quality_score=MagicMock(overall=20, tier="poor")
    )

    stats = analyzer._compute_stats(
        pr_results=[clean_critical_pr, slop_critical_pr],
        issue_results=[]
    )

    assert stats["critical_prs"] == 1
    assert stats["slop_flagged"] == 1
