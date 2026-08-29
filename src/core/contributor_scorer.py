"""
Contributor Scoring System.
Tracks and scores contributor quality over time.
This is a KEY differentiator for the product.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ContributorProfile:
    """Complete profile for a GitHub contributor."""
    username: str
    total_prs: int
    avg_quality_score: float
    excellent_prs: int
    good_prs: int
    needs_work_prs: int
    slop_prs: int
    slop_rate: float
    consistency_score: float
    trend: str              # "improving" | "declining" | "stable"
    rank: str               # "champion" | "regular" | "newcomer" | "watch"
    last_pr_date: Optional[datetime]
    feedback_history: list[str] = field(default_factory=list)

    @property
    def trust_score(self) -> int:
        """
        0-100 trust score for this contributor.
        High trust = PRs get fast-tracked.
        Low trust = PRs get extra scrutiny.
        """
        base = self.avg_quality_score

        # Bonuses
        if self.total_prs >= 10:
            base += 5
        if self.slop_rate == 0:
            base += 10
        if self.trend == "improving":
            base += 5

        # Penalties
        base -= self.slop_rate * 30
        if self.total_prs < 3:
            base -= 10

        return max(0, min(100, int(base)))

    @property
    def rank_emoji(self) -> str:
        return {
            "champion":  "🏆",
            "regular":   "⭐",
            "newcomer":  "🌱",
            "watch":     "⚠️",
        }.get(self.rank, "❓")


class ContributorScorer:
    """
    Scores and tracks contributor quality over time.
    Builds reputation system for maintainers.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client

    def calculate_profile(
        self,
        username: str,
        pr_history: list[dict],
    ) -> ContributorProfile:
        """
        Calculate complete contributor profile
        from their PR history.
        """
        if not pr_history:
            return self._empty_profile(username)

        total = len(pr_history)
        scores = [
            p.get("quality_score", 0)
            for p in pr_history
        ]
        avg_score = sum(scores) / total if scores else 0

        excellent = sum(
            1 for p in pr_history
            if p.get("quality_tier") == "excellent"
        )
        good = sum(
            1 for p in pr_history
            if p.get("quality_tier") == "good"
        )
        needs_work = sum(
            1 for p in pr_history
            if p.get("quality_tier") == "needs-work"
        )
        slop_count = sum(
            1 for p in pr_history
            if p.get("is_slop", False)
        )
        slop_rate = slop_count / total

        # Calculate trend (last 3 vs first 3)
        trend = "stable"
        if total >= 6:
            recent = sum(scores[-3:]) / 3
            older  = sum(scores[:3]) / 3
            if recent > older + 10:
                trend = "improving"
            elif recent < older - 10:
                trend = "declining"

        # Calculate consistency
        if len(scores) > 1:
            import statistics
            try:
                std_dev = statistics.stdev(scores)
                consistency = max(0, 100 - std_dev)
            except Exception:
                consistency = 50.0
        else:
            consistency = 50.0

        # Calculate rank
        rank = self._calculate_rank(
            avg_score=avg_score,
            total_prs=total,
            slop_rate=slop_rate,
            trend=trend,
        )

        # Last PR date
        last_date = None
        if pr_history:
            try:
                last_date = datetime.fromisoformat(
                    pr_history[-1].get(
                        "analyzed_at",
                        datetime.utcnow().isoformat()
                    )
                )
            except Exception:
                last_date = datetime.utcnow()

        return ContributorProfile(
            username=username,
            total_prs=total,
            avg_quality_score=round(avg_score, 1),
            excellent_prs=excellent,
            good_prs=good,
            needs_work_prs=needs_work,
            slop_prs=slop_count,
            slop_rate=round(slop_rate, 3),
            consistency_score=round(consistency, 1),
            trend=trend,
            rank=rank,
            last_pr_date=last_date,
        )

    def _calculate_rank(
        self,
        avg_score: float,
        total_prs: int,
        slop_rate: float,
        trend: str,
    ) -> str:
        """Determine contributor rank."""

        # Watch list — too much slop
        if slop_rate >= 0.5:
            return "watch"

        # Champion — high quality, many PRs
        if (
            avg_score >= 75
            and total_prs >= 5
            and slop_rate == 0
        ):
            return "champion"

        # Regular — decent history
        if total_prs >= 3 and avg_score >= 50:
            return "regular"

        # Newcomer — not enough history
        return "newcomer"

    def _empty_profile(
        self, username: str
    ) -> ContributorProfile:
        return ContributorProfile(
            username=username,
            total_prs=0,
            avg_quality_score=0.0,
            excellent_prs=0,
            good_prs=0,
            needs_work_prs=0,
            slop_prs=0,
            slop_rate=0.0,
            consistency_score=0.0,
            trend="stable",
            rank="newcomer",
            last_pr_date=None,
        )

    def get_leaderboard(
        self,
        profiles: list[ContributorProfile],
        limit: int = 10,
    ) -> list[ContributorProfile]:
        """Get top contributors by trust score."""
        return sorted(
            profiles,
            key=lambda p: p.trust_score,
            reverse=True,
        )[:limit]

    def get_watch_list(
        self,
        profiles: list[ContributorProfile],
    ) -> list[ContributorProfile]:
        """Get contributors that need monitoring."""
        return [
            p for p in profiles
            if p.rank == "watch"
            or p.slop_rate >= 0.3
        ]