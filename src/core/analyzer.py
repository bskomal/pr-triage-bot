"""
Core PR/Issue Analyzer — orchestrates all analysis modules.
Single entry point for all triage operations.
Includes Supabase integration for dashboard data.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
import structlog

from src.ai.llm_client import LLMClient
from src.ai.prompts import (
    CLASSIFY_PR,
    CLASSIFY_ISSUE,
    DETECT_DUPLICATE,
)
from src.core.scorer import PRScorer, QualityScore
from src.core.slop_detector import SlopDetector, SlopResult
from src.github.client import GitHubClient, PRData, IssueData

logger = structlog.get_logger(__name__)

VALID_TYPES = [
    "bug", "feature", "docs",
    "refactor", "test", "chore", "security"
]
VALID_PRIORITIES = ["critical", "high", "medium", "low"]
VALID_COMPLEXITY = [
    "trivial", "small", "medium", "large", "xl"
]


# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class PRAnalysisResult:
    """Complete analysis result for a single PR."""
    pr: PRData
    classification: dict
    quality_score: QualityScore
    slop_result: SlopResult
    recommended_labels: list[str]
    auto_reply: Optional[str]
    analyzed_at: datetime = field(
        default_factory=datetime.utcnow
    )
    analysis_time_ms: int = 0

    @property
    def needs_attention(self) -> bool:
        return (
            self.classification.get("priority")
            in ("critical", "high")
            and not self.slop_result.is_suspected_slop
        )

    @property
    def should_flag(self) -> bool:
        return self.slop_result.is_suspected_slop


@dataclass
class IssueAnalysisResult:
    """Complete analysis result for a single Issue."""
    issue: IssueData
    classification: dict
    is_duplicate: bool
    duplicate_of: Optional[int]
    recommended_labels: list[str]
    auto_reply: Optional[str]
    analyzed_at: datetime = field(
        default_factory=datetime.utcnow
    )


@dataclass
class TriageReport:
    """Full triage report for a repository."""
    repo: str
    generated_at: datetime
    pr_results: list[PRAnalysisResult]
    issue_results: list[IssueAnalysisResult]
    stats: dict

    @property
    def critical_prs(self) -> list[PRAnalysisResult]:
        return [
            r for r in self.pr_results
            if r.classification.get("priority") == "critical"
            and not r.slop_result.is_suspected_slop
        ]

    @property
    def flagged_prs(self) -> list[PRAnalysisResult]:
        return [
            r for r in self.pr_results
            if r.slop_result.is_suspected_slop
        ]

    @property
    def excellent_prs(self) -> list[PRAnalysisResult]:
        return [
            r for r in self.pr_results
            if r.quality_score.tier == "excellent"
        ]

    @property
    def duplicate_issues(self) -> list[IssueAnalysisResult]:
        return [
            r for r in self.issue_results
            if r.is_duplicate
        ]


# ─────────────────────────────────────────────
# Supabase Client
# ─────────────────────────────────────────────

class SupabaseClient:
    """
    Lightweight Supabase REST client.
    No external SDK needed — just httpx.
    """

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "")
        self.enabled = bool(self.url and self.key)

        if self.enabled:
            logger.info(
                "Supabase client initialized",
                url=self.url,
            )
        else:
            logger.warning(
                "Supabase not configured — "
                "dashboard data will not be saved. "
                "Set SUPABASE_URL and SUPABASE_KEY in .env"
            )

    @property
    def headers(self) -> dict:
        return {
            "apikey":        self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type":  "application/json",
            "Prefer":        "return=minimal",
        }

    async def insert(
        self,
        table: str,
        record: dict,
    ) -> bool:
        """Insert a record into a Supabase table."""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient(
                timeout=10
            ) as client:
                response = await client.post(
                    f"{self.url}/rest/v1/{table}",
                    headers=self.headers,
                    json=record,
                )

                if response.status_code in (200, 201):
                    logger.info(
                        "Saved to Supabase",
                        table=table,
                    )
                    return True
                else:
                    logger.warning(
                        "Supabase insert failed",
                        table=table,
                        status=response.status_code,
                        body=response.text[:200],
                    )
                    return False

        except Exception as e:
            logger.warning(
                "Supabase insert error",
                table=table,
                error=str(e),
            )
            return False

    async def upsert(
        self,
        table: str,
        record: dict,
        on_conflict: str = "",
    ) -> bool:
        """Upsert a record into a Supabase table."""
        if not self.enabled:
            return False

        try:
            headers = {
                **self.headers,
                "Prefer": f"resolution=merge-duplicates,return=minimal",
            }

            async with httpx.AsyncClient(
                timeout=10
            ) as client:
                response = await client.post(
                    f"{self.url}/rest/v1/{table}",
                    headers=headers,
                    json=record,
                )

                return response.status_code in (200, 201)

        except Exception as e:
            logger.warning(
                "Supabase upsert error",
                error=str(e)
            )
            return False


# ─────────────────────────────────────────────
# Main Analyzer
# ─────────────────────────────────────────────

class Analyzer:
    """
    Master orchestrator for all PR and Issue analysis.
    Coordinates LLM, scorer, slop detector,
    GitHub client, and Supabase storage.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        github_client: GitHubClient,
        dry_run: bool = False,
    ):
        self.llm = llm_client
        self.github = github_client
        self.dry_run = dry_run
        self.scorer = PRScorer(llm_client=llm_client)
        self.slop_detector = SlopDetector(
            llm_client=llm_client
        )
        self.supabase = SupabaseClient()

        logger.info(
            "Analyzer initialized",
            dry_run=dry_run,
            supabase_enabled=self.supabase.enabled,
        )

    # ─────────────────────────────────────────
    # PR Analysis
    # ─────────────────────────────────────────

    async def analyze_pr(
        self,
        pr: PRData,
    ) -> PRAnalysisResult:
        """
        Full analysis pipeline for a single PR.
        Runs classification, scoring, and slop
        detection in parallel for speed.
        """
        import time
        start = time.monotonic()

        logger.info(
            "Analyzing PR",
            pr_number=pr.number,
            title=pr.title[:60],
        )

        # Fetch diff sample for slop detection
        diff_sample = ""
        try:
            diff_sample = self.github.get_pr_diff_sample(
                pr.number
            )
        except Exception as e:
            logger.warning(
                "Could not fetch diff",
                error=str(e)
            )

        # Run all analyses in parallel with fallback handling
        try:
            results = await asyncio.gather(
                self._classify_pr(pr),
                self.scorer.score(
                    title=pr.title,
                    description=pr.description,
                    body=pr.body,
                    files_changed=pr.files_changed,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    commit_messages=pr.commit_messages,
                    linked_issues=pr.linked_issues,
                ),
                self.slop_detector.analyze(
                    title=pr.title,
                    description=pr.description,
                    commit_messages=pr.commit_messages,
                    diff_sample=diff_sample,
                    files_changed=pr.files_changed,
                ),
                return_exceptions=True
            )
            classification = (
                results[0] if not isinstance(results[0], Exception)
                else {
                    "type": "chore",
                    "priority": "medium",
                    "complexity": "medium",
                    "confidence": 0.0,
                    "reasoning": "Classification failed",
                }
            )
            quality_score = (
                results[1] if not isinstance(results[1], Exception)
                else QualityScore(
                    overall=50,
                    tier="needs-work",
                    label="quality: needs-work",
                    feedback="Analysis partially unavailable.",
                )
            )
            slop_result = (
                results[2] if not isinstance(results[2], Exception)
                else SlopResult(
                    is_suspected_slop=False,
                    confidence=0.0,
                    severity="low",
                )
            )
        except Exception as e:
            logger.error("Parallel analysis failed", error=str(e))
            classification = {
                "type": "chore",
                "priority": "medium",
                "complexity": "medium",
                "confidence": 0.0,
            }
            quality_score = QualityScore(
                overall=50, tier="needs-work", label="quality: needs-work"
            )
            slop_result = SlopResult(
                is_suspected_slop=False, confidence=0.0, severity="low"
            )

        # Build labels and reply
        labels = self._build_pr_labels(
            classification, quality_score, slop_result
        )
        auto_reply = self._build_pr_reply(
            pr=pr,
            quality_score=quality_score,
            slop_result=slop_result,
            classification=classification,
        )

        # Apply to GitHub unless dry run
        if not self.dry_run:
            if labels:
                try:
                    self.github.add_labels(
                        pr.number, labels, is_pr=True
                    )
                except Exception as e:
                    logger.error(
                        "Failed to add labels",
                        error=str(e)
                    )
            if auto_reply:
                try:
                    self.github.post_comment(
                        pr.number,
                        auto_reply,
                        is_pr=True
                    )
                except Exception as e:
                    logger.error(
                        "Failed to post comment",
                        error=str(e)
                    )

        elapsed_ms = int(
            (time.monotonic() - start) * 1000
        )

        result = PRAnalysisResult(
            pr=pr,
            classification=classification,
            quality_score=quality_score,
            slop_result=slop_result,
            recommended_labels=labels,
            auto_reply=auto_reply,
            analysis_time_ms=elapsed_ms,
        )

        # Save to Supabase dashboard
        await self._save_pr_to_supabase(result)

        logger.info(
            "PR analysis complete",
            pr_number=pr.number,
            quality_tier=quality_score.tier,
            quality_score=quality_score.overall,
            is_slop=slop_result.is_suspected_slop,
            priority=classification.get("priority"),
            labels_applied=labels,
            elapsed_ms=elapsed_ms,
        )

        return result

    # ─────────────────────────────────────────
    # Issue Analysis
    # ─────────────────────────────────────────

    async def analyze_issue(
        self,
        issue: IssueData,
        existing_issues: list[IssueData],
    ) -> IssueAnalysisResult:
        """Full analysis for a single issue."""
        logger.info(
            "Analyzing issue",
            issue_number=issue.number,
            title=issue.title[:60],
        )

        try:
            classification, duplicate_info = (
                await asyncio.gather(
                    self._classify_issue(issue),
                    self._detect_duplicate(
                        issue, existing_issues
                    ),
                )
            )
        except Exception as e:
            logger.error(
                "Issue analysis failed",
                error=str(e)
            )
            classification = {
                "type": "unknown",
                "priority": "medium",
                "needs_more_info": False,
                "missing_info": [],
            }
            duplicate_info = {"is_duplicate": False}

        is_duplicate = duplicate_info.get(
            "is_duplicate", False
        )
        duplicate_of = duplicate_info.get("duplicate_of")

        labels = self._build_issue_labels(
            classification=classification,
            is_duplicate=is_duplicate,
            needs_more_info=classification.get(
                "needs_more_info", False
            ),
        )

        auto_reply = self._build_issue_reply(
            issue=issue,
            classification=classification,
            is_duplicate=is_duplicate,
            duplicate_of=duplicate_of,
        )

        # Apply to GitHub
        if not self.dry_run:
            if labels:
                try:
                    self.github.add_labels(
                        issue.number,
                        labels,
                        is_pr=False
                    )
                except Exception as e:
                    logger.error(
                        "Failed to add issue labels",
                        error=str(e)
                    )
            if auto_reply:
                try:
                    self.github.post_comment(
                        issue.number,
                        auto_reply,
                        is_pr=False,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to post issue comment",
                        error=str(e)
                    )

        return IssueAnalysisResult(
            issue=issue,
            classification=classification,
            is_duplicate=is_duplicate,
            duplicate_of=duplicate_of,
            recommended_labels=labels,
            auto_reply=auto_reply,
        )

    # ─────────────────────────────────────────
    # Full Triage
    # ─────────────────────────────────────────

    async def run_full_triage(
        self,
        max_prs: int = 50,
        max_issues: int = 100,
    ) -> TriageReport:
        """Run full repository triage."""
        logger.info(
            "Starting full triage",
            repo=self.github._repo_name,
            max_prs=max_prs,
            max_issues=max_issues,
        )

        prs = self.github.get_open_prs(
            max_count=max_prs
        )
        issues = self.github.get_open_issues(
            max_count=max_issues
        )

        # Analyze PRs with bounded concurrency
        pr_results = await self._analyze_batch(
            items=prs,
            analyze_fn=self.analyze_pr,
            concurrency=3,
        )

        # Analyze issues sequentially
        issue_results = []
        for issue in issues:
            try:
                result = await self.analyze_issue(
                    issue=issue,
                    existing_issues=[
                        i for i in issues
                        if i.number != issue.number
                    ],
                )
                issue_results.append(result)
            except Exception as e:
                logger.error(
                    "Issue analysis failed",
                    issue_number=issue.number,
                    error=str(e),
                )

        stats = self._compute_stats(
            pr_results, issue_results
        )

        # Save digest to Supabase
        await self._save_digest_to_supabase(
            pr_results=pr_results,
            issue_results=issue_results,
            stats=stats,
        )

        report = TriageReport(
            repo=self.github._repo_name,
            generated_at=datetime.utcnow(),
            pr_results=pr_results,
            issue_results=issue_results,
            stats=stats,
        )

        logger.info(
            "Full triage complete",
            prs_analyzed=len(pr_results),
            issues_analyzed=len(issue_results),
            critical_prs=len(report.critical_prs),
            flagged_prs=len(report.flagged_prs),
            excellent_prs=len(report.excellent_prs),
        )

        return report

    # ─────────────────────────────────────────
    # Batch Processing
    # ─────────────────────────────────────────

    async def _analyze_batch(
        self,
        items: list,
        analyze_fn,
        concurrency: int = 3,
    ) -> list:
        """Process items with bounded concurrency."""
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_analyze(item):
            async with semaphore:
                try:
                    return await analyze_fn(item)
                except Exception as e:
                    logger.error(
                        "Item analysis failed",
                        error=str(e),
                    )
                    return None

        tasks = [
            bounded_analyze(item)
            for item in items
        ]
        raw = await asyncio.gather(*tasks)
        return [r for r in raw if r is not None]

    # ─────────────────────────────────────────
    # Classification
    # ─────────────────────────────────────────

    async def _classify_pr(self, pr: PRData) -> dict:
        """Classify PR type and priority via LLM."""
        try:
            response = await self.llm.complete(
                prompt=CLASSIFY_PR,
                variables={
                    "title": pr.title or "No title",
                    "description": (
                        pr.description or ""
                    )[:500],
                    "files_changed": str(
                        pr.files_changed[:20]
                    ),
                    "additions": pr.additions or 0,
                    "deletions": pr.deletions or 0,
                    "commit_messages": "\n".join(
                        pr.commit_messages[:5]
                    ) or "No commit messages",
                },
                expect_json=True,
            )
            result = response.parsed or {}

            # Validate fields
            if result.get("type") not in VALID_TYPES:
                result["type"] = "chore"
            if result.get("priority") not in VALID_PRIORITIES:
                result["priority"] = "medium"
            if result.get("complexity") not in VALID_COMPLEXITY:
                result["complexity"] = "medium"

            return result

        except Exception as e:
            logger.warning(
                "PR classification failed — using defaults",
                error=str(e),
                pr_number=pr.number,
            )
            return {
                "type":       "chore",
                "priority":   "medium",
                "complexity": "medium",
                "confidence": 0.0,
                "reasoning":  "Classification failed",
            }

    async def _classify_issue(
        self, issue: IssueData
    ) -> dict:
        """Classify issue type and priority via LLM."""
        try:
            response = await self.llm.complete(
                prompt=CLASSIFY_ISSUE,
                variables={
                    "title": issue.title or "No title",
                    "body":  (issue.body or "")[:600],
                    "existing_labels": str(
                        issue.labels or []
                    ),
                },
                expect_json=True,
            )
            return response.parsed or {}
        except Exception as e:
            logger.warning(
                "Issue classification failed",
                error=str(e)
            )
            return {
                "type":           "unknown",
                "priority":       "medium",
                "needs_more_info": False,
                "missing_info":   [],
            }

    async def _detect_duplicate(
        self,
        issue: IssueData,
        existing_issues: list[IssueData],
    ) -> dict:
        """Detect if issue is a duplicate."""
        if not existing_issues:
            return {"is_duplicate": False}

        formatted = "\n\n".join(
            f"Issue #{i.number}: {i.title}\n"
            f"{(i.body or '')[:200]}"
            for i in existing_issues[:10]
        )

        try:
            response = await self.llm.complete(
                prompt=DETECT_DUPLICATE,
                variables={
                    "new_title": issue.title or "",
                    "new_body":  (issue.body or "")[:400],
                    "existing_issues": formatted,
                },
                expect_json=True,
            )
            return response.parsed or {}
        except Exception as e:
            logger.warning(
                "Duplicate detection failed",
                error=str(e)
            )
            return {"is_duplicate": False}

    # ─────────────────────────────────────────
    # Label Building
    # ─────────────────────────────────────────

    def _build_pr_labels(
        self,
        classification: dict,
        quality_score: QualityScore,
        slop_result: SlopResult,
    ) -> list[str]:
        """Build the complete set of labels to apply."""
        labels = []

        pr_type = classification.get("type", "")
        if pr_type and pr_type != "unknown":
            labels.append(f"type: {pr_type}")

        priority = classification.get("priority", "")
        if priority:
            labels.append(f"priority: {priority}")

        labels.append(quality_score.label)

        if slop_result.is_suspected_slop:
            labels.append("quality: ai-generated")

        return list(dict.fromkeys(labels))

    def _build_issue_labels(
        self,
        classification: dict,
        is_duplicate: bool,
        needs_more_info: bool,
    ) -> list[str]:
        """Build labels for an issue."""
        labels = ["status: triaged"]

        issue_type = classification.get("type", "")
        if issue_type and issue_type != "unknown":
            labels.append(f"type: {issue_type}")

        priority = classification.get("priority", "")
        if priority:
            labels.append(f"priority: {priority}")

        if is_duplicate:
            labels.append("status: duplicate")

        return list(dict.fromkeys(labels))

    # ─────────────────────────────────────────
    # Reply Building
    # ─────────────────────────────────────────

    def _build_pr_reply(
        self,
        pr: PRData,
        quality_score: QualityScore,
        slop_result: SlopResult,
        classification: dict,
    ) -> Optional[str]:
        """Build auto-reply comment for PR if needed."""
        if slop_result.is_suspected_slop:
            return self._render_slop_reply(
                pr, slop_result
            )

        if quality_score.overall < 40:
            return self._render_quality_reply(
                pr, quality_score
            )

        return None

    def _build_issue_reply(
        self,
        issue: IssueData,
        classification: dict,
        is_duplicate: bool,
        duplicate_of: Optional[int],
    ) -> Optional[str]:
        """Build auto-reply for an issue."""
        if is_duplicate and duplicate_of:
            return (
                f"🤖 **PR Triage Bot**\n\n"
                f"This issue appears to be a duplicate "
                f"of #{duplicate_of}.\n"
                f"Please check that issue for existing "
                f"discussion.\n\n"
                f"_If you believe this is different, "
                f"please explain how._"
            )

        if classification.get("needs_more_info"):
            missing = classification.get(
                "missing_info", []
            )
            if missing:
                items = "\n".join(
                    f"- {item}" for item in missing
                )
                return (
                    f"🤖 **PR Triage Bot**\n\n"
                    f"Thanks for the report! "
                    f"To help us investigate:\n\n"
                    f"{items}\n\n"
                    f"_Please update the issue._"
                )

        return None

    def _render_slop_reply(
        self,
        pr: PRData,
        slop: SlopResult,
    ) -> str:
        """Render slop detection reply."""
        signals = "\n".join(
            f"- {s}" for s in slop.signal_names[:5]
        )
        return (
            f"🤖 **PR Triage Bot — Quality Review**\n\n"
            f"This PR has been flagged before "
            f"maintainer time is spent on it.\n\n"
            f"**Signals detected:**\n{signals}\n\n"
            f"**To get this PR reviewed:**\n"
            f"1. Explain specifically what changed and why\n"
            f"2. Add tests that cover your changes\n"
            f"3. Use specific commit messages\n\n"
            f"_This is automated. A maintainer will "
            f"review if you update the PR._"
        )

    def _render_quality_reply(
        self,
        pr: PRData,
        score: QualityScore,
    ) -> str:
        """Render quality feedback reply."""
        rows = "\n".join(
            f"| {d.name.replace('_', ' ').title()} "
            f"| {d.score}/100 |"
            for d in score.dimensions
        )
        return (
            f"🤖 **PR Triage Bot — Quality Feedback**\n\n"
            f"**Quality Score: {score.overall}/100** "
            f"({score.tier})\n\n"
            f"**Feedback:** {score.feedback}\n\n"
            f"| Dimension | Score |\n"
            f"|-----------|-------|\n"
            f"{rows}\n\n"
            f"_Update your PR to improve for faster review._"
        )

    # ─────────────────────────────────────────
    # Supabase Storage
    # ─────────────────────────────────────────

    async def _save_pr_to_supabase(
        self,
        result: PRAnalysisResult,
    ) -> None:
        """Save PR analysis result to Supabase."""
        try:
            record = {
                "repo": self.github._repo_name,
                "pr_number": result.pr.number,
                "title": result.pr.title,
                "author": result.pr.author,
                "url": result.pr.url,
                "quality_score": (
                    result.quality_score.overall
                ),
                "quality_tier": (
                    result.quality_score.tier
                ),
                "pr_type": result.classification.get(
                    "type", "unknown"
                ),
                "priority": result.classification.get(
                    "priority", "medium"
                ),
                "complexity": result.classification.get(
                    "complexity", "medium"
                ),
                "is_slop": (
                    result.slop_result.is_suspected_slop
                ),
                "slop_confidence": (
                    result.slop_result.confidence
                ),
                "slop_severity": (
                    result.slop_result.severity
                ),
                "slop_signals": (
                    result.slop_result.signal_names
                ),
                "recommended_labels": (
                    result.recommended_labels
                ),
                "feedback": (
                    result.quality_score.feedback
                ),
                "additions": result.pr.additions,
                "deletions": result.pr.deletions,
                "files_changed": len(
                    result.pr.files_changed
                ),
                "analyzed_at": (
                    result.analyzed_at.isoformat()
                ),
                "dry_run": self.dry_run,
            }

            await self.supabase.insert(
                "pr_analyses", record
            )

            # Update repo stats
            await self._update_repo_stats()

        except Exception as e:
            logger.warning(
                "Failed to save PR to Supabase",
                error=str(e)
            )

    async def _save_digest_to_supabase(
        self,
        pr_results: list[PRAnalysisResult],
        issue_results: list[IssueAnalysisResult],
        stats: dict,
    ) -> None:
        """Save triage digest summary to Supabase."""
        try:
            record = {
                "repo": self.github._repo_name,
                "format": "markdown",
                "generated_at": datetime.utcnow().isoformat(),
                "total_prs": stats.get(
                    "total_prs_analyzed", 0
                ),
                "total_issues": stats.get(
                    "total_issues_analyzed", 0
                ),
                "critical_prs": stats.get(
                    "critical_prs", 0
                ),
                "slop_flagged": stats.get(
                    "slop_flagged", 0
                ),
                "avg_quality": stats.get(
                    "avg_quality_score", 0
                ),
                "content": (
                    f"Triage completed: "
                    f"{stats.get('total_prs_analyzed', 0)} PRs, "
                    f"{stats.get('total_issues_analyzed', 0)} issues"
                ),
            }

            await self.supabase.insert(
                "digests", record
            )

        except Exception as e:
            logger.warning(
                "Failed to save digest to Supabase",
                error=str(e)
            )

    async def _update_repo_stats(self) -> None:
        """Update repository summary stats."""
        try:
            repo = self.github._repo_name

            record = {
                "repo": repo,
                "last_analyzed": datetime.utcnow().isoformat(),
            }

            await self.supabase.upsert(
                "repo_stats",
                record,
                on_conflict="repo",
            )

        except Exception as e:
            logger.warning(
                "Failed to update repo stats",
                error=str(e)
            )

    # ─────────────────────────────────────────
    # Stats
    # ─────────────────────────────────────────

    def _compute_stats(
        self,
        pr_results: list[PRAnalysisResult],
        issue_results: list[IssueAnalysisResult],
    ) -> dict:
        """Compute summary statistics."""
        return {
            "total_prs_analyzed": len(pr_results),
            "total_issues_analyzed": len(issue_results),
            "critical_prs": len([
                r for r in pr_results
                if r.classification.get("priority") == "critical"
                and not r.slop_result.is_suspected_slop
            ]),
            "high_priority_prs": len([
                r for r in pr_results
                if r.classification.get("priority")
                == "high"
            ]),
            "slop_flagged": len([
                r for r in pr_results
                if r.slop_result.is_suspected_slop
            ]),
            "excellent_quality": len([
                r for r in pr_results
                if r.quality_score.tier == "excellent"
            ]),
            "duplicate_issues": len([
                r for r in issue_results
                if r.is_duplicate
            ]),
            "avg_quality_score": (
                sum(
                    r.quality_score.overall
                    for r in pr_results
                ) // len(pr_results)
                if pr_results else 0
            ),
        }