"""
PR Quality Scorer — Multi-dimensional contribution quality assessment.
Produces a 0-100 score with breakdown per dimension.
"""

from dataclasses import dataclass, field
from typing import Optional

import structlog

from src.ai.llm_client import LLMClient
from src.ai.prompts import SCORE_QUALITY

logger = structlog.get_logger(__name__)

# File extensions that count as test files
TEST_EXTENSIONS = {".test.py", ".spec.py", "_test.py", "test_.py"}
TEST_DIRECTORIES = {"test", "tests", "__tests__", "spec", "specs"}
DOC_FILES = {
    "readme.md", "changelog.md", "contributing.md",
    "docs/", "documentation/", ".rst", ".mdx",
}


@dataclass
class ScoreDimension:
    name: str
    score: int          # 0-100
    weight: float       # contribution to overall score
    reason: str = ""


@dataclass
class QualityScore:
    overall: int                                    # 0-100
    tier: str                                       # excellent|good|needs-work|poor
    dimensions: list[ScoreDimension] = field(default_factory=list)
    label: str = ""                                 # GitHub label to apply
    feedback: str = ""                              # Actionable feedback for contributor
    breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def emoji(self) -> str:
        return {
            "excellent": "🌟",
            "good": "✅",
            "needs-work": "⚠️",
            "poor": "❌",
        }.get(self.tier, "❓")


class PRScorer:
    """
    Scores pull requests across multiple quality dimensions.
    
    Dimensions:
    - Description quality (20%)
    - Test coverage (25%)
    - Documentation (20%)
    - Scope focus (15%)
    - Commit message quality (10%)
    - Linked issue (10%)
    """

    DIMENSION_WEIGHTS = {
        "description_quality": 0.20,
        "test_coverage": 0.25,
        "documentation": 0.20,
        "scope_focus": 0.15,
        "commit_quality": 0.10,
        "linked_issue": 0.10,
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client

    async def score(
        self,
        title: str,
        description: str,
        body: str,
        files_changed: list[str],
        additions: int,
        deletions: int,
        commit_messages: list[str],
        linked_issues: list[int],
    ) -> QualityScore:
        """
        Score a PR across all quality dimensions.
        Combines heuristic + LLM scoring.
        """
        logger.info("Scoring PR quality", title=title[:60])

        test_files = self._identify_test_files(files_changed)
        doc_files = self._identify_doc_files(files_changed)

        dimensions = [
            self._score_description(description, body),
            self._score_tests(test_files, files_changed),
            self._score_documentation(doc_files, files_changed, description),
            self._score_scope(files_changed, additions, deletions),
            self._score_commits(commit_messages),
            self._score_issue_linkage(linked_issues, description, body),
        ]

        # LLM enhancement for description and test scoring
        if self.llm:
            try:
                llm_scores = await self._llm_score(
                    title=title,
                    description=description,
                    has_tests=len(test_files) > 0,
                    has_docs=len(doc_files) > 0,
                    files_changed=files_changed,
                    test_files=test_files,
                    description_length=len(description),
                )
                dimensions = self._merge_llm_scores(dimensions, llm_scores)
                feedback = llm_scores.get("feedback", "")
            except Exception as e:
                logger.warning("LLM scoring failed, using heuristics only", error=str(e))
                feedback = self._generate_feedback(dimensions)
        else:
            feedback = self._generate_feedback(dimensions)

        overall = self._compute_overall(dimensions)
        tier = self._compute_tier(overall)
        label = self._compute_label(tier)

        result = QualityScore(
            overall=overall,
            tier=tier,
            dimensions=dimensions,
            label=label,
            feedback=feedback,
            breakdown={d.name: d.score for d in dimensions},
        )

        logger.info(
            "Scoring complete",
            overall=overall,
            tier=tier,
            label=label,
        )

        return result

    def _identify_test_files(self, files: list[str]) -> list[str]:
        """Find test files in the changed file list."""
        test_files = []
        for f in files:
            fname = f.lower()
            if any(d in fname.split("/") for d in TEST_DIRECTORIES):
                test_files.append(f)
            elif fname.startswith("test_") or fname.endswith("_test.py"):
                test_files.append(f)
            elif ".test." in fname or ".spec." in fname:
                test_files.append(f)
        return test_files

    def _identify_doc_files(self, files: list[str]) -> list[str]:
        """Find documentation files in the changed file list."""
        doc_files = []
        for f in files:
            fname = f.lower()
            if any(doc in fname for doc in DOC_FILES):
                doc_files.append(f)
            elif fname.endswith((".md", ".rst", ".mdx", ".txt")):
                doc_files.append(f)
        return doc_files

    def _score_description(self, description: str, body: str) -> ScoreDimension:
        """Score description quality heuristically."""
        text = (description + " " + body).strip()

        if not text or len(text) < 20:
            return ScoreDimension(
                name="description_quality",
                score=0,
                weight=self.DIMENSION_WEIGHTS["description_quality"],
                reason="No meaningful description provided",
            )

        score = 0
        word_count = len(text.split())

        # Length scoring (up to 40 points)
        if word_count >= 100:
            score += 40
        elif word_count >= 50:
            score += 30
        elif word_count >= 20:
            score += 15
        else:
            score += 5

        # Structural elements (up to 40 points)
        if "##" in text or "###" in text:
            score += 15  # Has sections
        if "- " in text or "* " in text:
            score += 10  # Has bullet points
        if "```" in text:
            score += 10  # Has code examples
        if "screenshot" in text.lower() or "![" in text:
            score += 5   # Has screenshots

        # Quality markers (up to 20 points)
        if "fix" in text.lower() and "#" in text:
            score += 10  # References issue
        if "test" in text.lower():
            score += 5
        if "breaking change" in text.lower():
            score += 5

        return ScoreDimension(
            name="description_quality",
            score=min(score, 100),
            weight=self.DIMENSION_WEIGHTS["description_quality"],
            reason=f"Description has {word_count} words",
        )

    def _score_tests(
        self, test_files: list[str], all_files: list[str]
    ) -> ScoreDimension:
        """Score test coverage."""
        if not all_files:
            return ScoreDimension(
                name="test_coverage",
                score=50,
                weight=self.DIMENSION_WEIGHTS["test_coverage"],
                reason="No file information available",
            )

        if not test_files:
            return ScoreDimension(
                name="test_coverage",
                score=10,
                weight=self.DIMENSION_WEIGHTS["test_coverage"],
                reason="No test files included",
            )

        # Ratio of test files to all files
        test_ratio = len(test_files) / len(all_files)

        if test_ratio >= 0.4:
            score = 100
            reason = f"Excellent test coverage: {len(test_files)} test files"
        elif test_ratio >= 0.2:
            score = 80
            reason = f"Good test coverage: {len(test_files)} test files"
        elif test_ratio >= 0.1:
            score = 60
            reason = f"Some tests included: {len(test_files)} test files"
        else:
            score = 40
            reason = f"Minimal test coverage: {len(test_files)} test files"

        return ScoreDimension(
            name="test_coverage",
            score=score,
            weight=self.DIMENSION_WEIGHTS["test_coverage"],
            reason=reason,
        )

    def _score_documentation(
        self,
        doc_files: list[str],
        all_files: list[str],
        description: str,
    ) -> ScoreDimension:
        """Score documentation quality."""
        score = 0

        if doc_files:
            score += 60
            score += min(len(doc_files) * 10, 30)

        # Docs in description
        if description and len(description) > 100:
            score += 10

        if score == 0:
            # Not all PRs need docs — give partial credit
            score = 40
            reason = "No doc files (may be acceptable for this PR type)"
        else:
            reason = f"Includes {len(doc_files)} documentation file(s)"

        return ScoreDimension(
            name="documentation",
            score=min(score, 100),
            weight=self.DIMENSION_WEIGHTS["documentation"],
            reason=reason,
        )

    def _score_scope(
        self,
        files_changed: list[str],
        additions: int,
        deletions: int,
    ) -> ScoreDimension:
        """Score PR scope — focused PRs score higher."""
        total_changes = additions + deletions
        file_count = len(files_changed)

        if file_count == 0:
            return ScoreDimension(
                name="scope_focus",
                score=50,
                weight=self.DIMENSION_WEIGHTS["scope_focus"],
                reason="No file change information",
            )

        # Small, focused PRs are easier to review
        if file_count <= 3 and total_changes <= 100:
            score = 100
            reason = f"Focused PR: {file_count} files, {total_changes} changes"
        elif file_count <= 10 and total_changes <= 500:
            score = 80
            reason = f"Reasonable scope: {file_count} files, {total_changes} changes"
        elif file_count <= 20 and total_changes <= 1000:
            score = 60
            reason = f"Large PR: {file_count} files, {total_changes} changes"
        elif file_count <= 50:
            score = 40
            reason = f"Very large PR: {file_count} files — consider splitting"
        else:
            score = 20
            reason = f"Massive PR: {file_count} files — should be split"

        return ScoreDimension(
            name="scope_focus",
            score=score,
            weight=self.DIMENSION_WEIGHTS["scope_focus"],
            reason=reason,
        )

    def _score_commits(self, commit_messages: list[str]) -> ScoreDimension:
        """Score commit message quality."""
        if not commit_messages:
            return ScoreDimension(
                name="commit_quality",
                score=20,
                weight=self.DIMENSION_WEIGHTS["commit_quality"],
                reason="No commit messages found",
            )

        scores = []
        for msg in commit_messages:
            msg_score = 0
            clean = msg.strip()

            # Conventional commits format
            if re.match(
                r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\(.+\))?: .+",
                clean,
            ):
                msg_score = 100
            # Reasonable length and specificity
            elif len(clean) >= 20 and not re.match(
                r"^(fix|update|change|wip)\s*$", clean, re.IGNORECASE
            ):
                msg_score = 70
            # Too short or generic
            elif len(clean) < 10:
                msg_score = 20
            else:
                msg_score = 40

            scores.append(msg_score)

        avg_score = sum(scores) // len(scores)
        return ScoreDimension(
            name="commit_quality",
            score=avg_score,
            weight=self.DIMENSION_WEIGHTS["commit_quality"],
            reason=f"Analyzed {len(commit_messages)} commit message(s)",
        )

    def _score_issue_linkage(
        self,
        linked_issues: list[int],
        description: str,
        body: str,
    ) -> ScoreDimension:
        """Score whether PR is linked to an issue."""
        text = (description + " " + body).lower()

        # Check for issue references in text
        has_ref = bool(
            re.search(r"(closes|fixes|resolves|related to)\s+#\d+", text)
            or re.search(r"#\d{1,6}", text)
            or linked_issues
        )

        if linked_issues:
            score = 100
            reason = f"Linked to issue(s): {linked_issues}"
        elif has_ref:
            score = 80
            reason = "References an issue in description"
        else:
            score = 20
            reason = "No linked issue found"

        return ScoreDimension(
            name="linked_issue",
            score=score,
            weight=self.DIMENSION_WEIGHTS["linked_issue"],
            reason=reason,
        )

    async def _llm_score(self, **kwargs) -> dict:
        """Get LLM-enhanced quality scores."""
        response = await self.llm.complete(
            prompt=SCORE_QUALITY,
            variables={
                "title": kwargs.get("title", ""),
                "description": kwargs.get("description", "")[:600],
                "has_tests": str(kwargs.get("has_tests", False)),
                "has_docs": str(kwargs.get("has_docs", False)),
                "files_changed": str(kwargs.get("files_changed", [])[:10]),
                "test_files": str(kwargs.get("test_files", [])),
                "description_length": kwargs.get("description_length", 0),
            },
            expect_json=True,
        )
        return response.parsed or {}

    def _merge_llm_scores(
        self,
        heuristic_dims: list[ScoreDimension],
        llm_scores: dict,
    ) -> list[ScoreDimension]:
        """Blend heuristic and LLM scores (60/40 split)."""
        llm_map = {
            "description_quality": llm_scores.get("description_quality"),
            "test_coverage": llm_scores.get("test_coverage"),
            "documentation": llm_scores.get("documentation"),
            "scope_focus": llm_scores.get("scope_focus"),
        }

        merged = []
        for dim in heuristic_dims:
            llm_score = llm_map.get(dim.name)
            if llm_score is not None:
                blended = int(dim.score * 0.4 + int(llm_score) * 0.6)
                merged.append(
                    ScoreDimension(
                        name=dim.name,
                        score=min(blended, 100),
                        weight=dim.weight,
                        reason=dim.reason,
                    )
                )
            else:
                merged.append(dim)

        return merged

    def _compute_overall(self, dimensions: list[ScoreDimension]) -> int:
        """Weighted average across all dimensions."""
        total = sum(d.score * d.weight for d in dimensions)
        return int(min(total, 100))

    def _compute_tier(self, score: int) -> str:
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "needs-work"
        else:
            return "poor"

    def _compute_label(self, tier: str) -> str:
        return {
            "excellent": "quality: excellent",
            "good": "quality: good",
            "needs-work": "quality: needs-work",
            "poor": "quality: needs-work",
        }.get(tier, "quality: needs-work")

    def _generate_feedback(self, dimensions: list[ScoreDimension]) -> str:
        """Generate actionable feedback from dimension scores."""
        weak = [d for d in dimensions if d.score < 50]
        if not weak:
            return "Great contribution! Meets all quality standards."

        suggestions = []
        for d in sorted(weak, key=lambda x: x.score)[:3]:
            if d.name == "test_coverage":
                suggestions.append("add tests")
            elif d.name == "description_quality":
                suggestions.append("improve PR description")
            elif d.name == "documentation":
                suggestions.append("update documentation")
            elif d.name == "commit_quality":
                suggestions.append("use conventional commit format")
            elif d.name == "linked_issue":
                suggestions.append("link to a related issue")

        return f"To improve this PR: {', '.join(suggestions)}."


import re