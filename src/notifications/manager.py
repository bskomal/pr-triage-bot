"""
Notification manager — sends to all
configured channels simultaneously.
"""

import os
from typing import Optional

import structlog

from src.notifications.slack import SlackNotifier, SlackConfig
from src.notifications.discord import DiscordNotifier, DiscordConfig
from src.core.analyzer import PRAnalysisResult, TriageReport

logger = structlog.get_logger(__name__)


class NotificationManager:
    """
    Manages all notification channels.
    Sends to Slack and Discord simultaneously.
    """

    def __init__(self):
        self.slack = self._init_slack()
        self.discord = self._init_discord()
        self.enabled = bool(self.slack or self.discord)

        logger.info(
            "Notification manager initialized",
            slack=bool(self.slack),
            discord=bool(self.discord),
        )

    def _init_slack(self) -> Optional[SlackNotifier]:
        """Initialize Slack if webhook configured."""
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook:
            return None
        return SlackNotifier(
            SlackConfig(
                webhook_url=webhook,
                channel=os.getenv("SLACK_CHANNEL"),
            )
        )

    def _init_discord(self) -> Optional[DiscordNotifier]:
        """Initialize Discord if webhook configured."""
        webhook = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook:
            return None
        return DiscordNotifier(
            DiscordConfig(webhook_url=webhook)
        )

    async def notify_pr_analyzed(
        self,
        result: PRAnalysisResult,
    ) -> None:
        """Send PR analysis notification to all channels."""
        if not self.enabled:
            return

        kwargs = {
            "pr_number":      result.pr.number,
            "title":          result.pr.title,
            "author":         result.pr.author,
            "repo":           result.pr.url.split("/")[4] + "/" + result.pr.url.split("/")[5] if result.pr.url else "",
            "quality_score":  result.quality_score.overall,
            "quality_tier":   result.quality_score.tier,
            "is_slop":        result.slop_result.is_suspected_slop,
            "slop_confidence": result.slop_result.confidence,
            "priority":       result.classification.get("priority", "medium"),
            "pr_type":        result.classification.get("type", "unknown"),
            "url":            result.pr.url,
            "feedback":       result.quality_score.feedback,
            "labels":         result.recommended_labels,
        }

        if self.slack:
            try:
                await self.slack.send_pr_analysis(**kwargs)
            except Exception as e:
                logger.warning(
                    "Slack notification failed",
                    error=str(e)
                )

        if self.discord:
            try:
                await self.discord.send_pr_analysis(**kwargs)
            except Exception as e:
                logger.warning(
                    "Discord notification failed",
                    error=str(e)
                )

    async def notify_daily_digest(
        self,
        report: TriageReport,
    ) -> None:
        """Send daily digest to all channels."""
        if not self.enabled:
            return

        stats = report.stats

        critical_list = [
            {
                "number": r.pr.number,
                "title":  r.pr.title,
                "url":    r.pr.url,
            }
            for r in report.critical_prs[:5]
        ]

        flagged_list = [
            {
                "number": r.pr.number,
                "title":  r.pr.title,
                "url":    r.pr.url,
            }
            for r in report.flagged_prs[:5]
        ]

        slack_kwargs = {
            "repo":         report.repo,
            "total_prs":    stats["total_prs_analyzed"],
            "critical_prs": stats["critical_prs"],
            "slop_flagged": stats["slop_flagged"],
            "excellent_prs": stats["excellent_quality"],
            "avg_quality":  stats["avg_quality_score"],
            "critical_list": critical_list,
            "flagged_list":  flagged_list,
        }

        discord_kwargs = {
            "repo":         report.repo,
            "total_prs":    stats["total_prs_analyzed"],
            "critical_prs": stats["critical_prs"],
            "slop_flagged": stats["slop_flagged"],
            "avg_quality":  stats["avg_quality_score"],
            "critical_list": critical_list,
            "flagged_list":  flagged_list,
        }

        if self.slack:
            try:
                await self.slack.send_daily_digest(
                    **slack_kwargs
                )
            except Exception as e:
                logger.warning(
                    "Slack digest failed",
                    error=str(e)
                )

        if self.discord:
            try:
                await self.discord.send_daily_digest(
                    **discord_kwargs
                )
            except Exception as e:
                logger.warning(
                    "Discord digest failed",
                    error=str(e)
                )