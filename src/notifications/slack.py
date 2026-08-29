"""
Slack notification system for PR Triage Bot.
Sends rich formatted messages to Slack channels.
"""

import os
from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SlackConfig:
    webhook_url: str
    channel: Optional[str] = None
    username: str = "PR Triage Bot"
    icon_emoji: str = ":robot_face:"


class SlackNotifier:
    """
    Sends rich Slack notifications for PR analysis results.
    Uses Slack Block Kit for beautiful formatting.
    """

    def __init__(self, config: SlackConfig):
        self.config = config

    async def send_pr_analysis(
        self,
        pr_number: int,
        title: str,
        author: str,
        repo: str,
        quality_score: int,
        quality_tier: str,
        is_slop: bool,
        slop_confidence: float,
        priority: str,
        pr_type: str,
        url: str,
        feedback: str,
        labels: list[str],
    ) -> bool:
        """Send PR analysis result to Slack."""
        
        # Choose color based on quality
        color = (
            "#3fb950" if quality_score >= 80
            else "#58a6ff" if quality_score >= 60
            else "#d29922" if quality_score >= 40
            else "#f85149"
        )

        # Build blocks
        blocks = [
            # Header
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{'🚫 AI Slop Flagged' if is_slop else '✅ PR Analyzed'}: #{pr_number}",
                    "emoji": True,
                }
            },
            # PR Info
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{url}|{title}>*\n`{repo}` • @{author}",
                }
            },
            # Divider
            {"type": "divider"},
            # Stats
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Quality Score*\n{self._score_emoji(quality_score)} {quality_score}/100 ({quality_tier})",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Priority*\n{self._priority_emoji(priority)} {priority.title()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type*\n🏷️ {pr_type.title()}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Slop Detection*\n{'🚫 Flagged' if is_slop else '✅ Clean'} ({slop_confidence:.0%})",
                    },
                ]
            },
        ]

        # Add slop warning if needed
        if is_slop:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *AI Slop Warning*: This PR has been flagged with {slop_confidence:.0%} confidence. Review carefully before spending time on it.",
                }
            })

        # Add feedback
        if feedback:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"💡 *Feedback*: {feedback}",
                }
            })

        # Add labels
        if labels:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🏷️ *Labels Applied*: {', '.join(f'`{l}`' for l in labels)}",
                }
            })

        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View PR on GitHub",
                        "emoji": True,
                    },
                    "url": url,
                    "style": "primary",
                }
            ]
        })

        payload = {
            "username": self.config.username,
            "icon_emoji": self.config.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ]
        }

        if self.config.channel:
            payload["channel"] = self.config.channel

        return await self._send(payload)

    async def send_daily_digest(
        self,
        repo: str,
        total_prs: int,
        critical_prs: int,
        slop_flagged: int,
        excellent_prs: int,
        avg_quality: int,
        critical_list: list[dict],
        flagged_list: list[dict],
    ) -> bool:
        """Send daily digest to Slack."""

        health_emoji = (
            "🟢" if avg_quality >= 70
            else "🟡" if avg_quality >= 50
            else "🔴"
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 Daily Triage Digest — {repo}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*PRs Analyzed*\n📊 {total_prs}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Quality*\n{health_emoji} {avg_quality}/100",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Critical PRs*\n🔥 {critical_prs}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Slop Flagged*\n🚫 {slop_flagged}",
                    },
                ]
            },
            {"type": "divider"},
        ]

        # Critical PRs
        if critical_list:
            critical_text = "\n".join(
                f"• <{pr['url']}|#{pr['number']}> — {pr['title'][:50]}"
                for pr in critical_list[:5]
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔥 *Critical PRs (Action Required)*\n{critical_text}",
                }
            })

        # Flagged PRs
        if flagged_list:
            flagged_text = "\n".join(
                f"• <{pr['url']}|#{pr['number']}> — {pr['title'][:50]}"
                for pr in flagged_list[:5]
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚫 *Flagged PRs (Review Carefully)*\n{flagged_text}",
                }
            })

        payload = {
            "username": self.config.username,
            "icon_emoji": self.config.icon_emoji,
            "blocks": blocks,
        }

        return await self._send(payload)

    async def _send(self, payload: dict) -> bool:
        """Send payload to Slack webhook."""
        try:
            async with httpx.AsyncClient(
                timeout=10
            ) as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                )
                if response.status_code == 200:
                    logger.info("Slack notification sent")
                    return True
                else:
                    logger.warning(
                        "Slack notification failed",
                        status=response.status_code,
                        body=response.text,
                    )
                    return False
        except Exception as e:
            logger.error(
                "Slack send error",
                error=str(e)
            )
            return False

    def _score_emoji(self, score: int) -> str:
        if score >= 80: return "🌟"
        if score >= 60: return "✅"
        if score >= 40: return "⚠️"
        return "❌"

    def _priority_emoji(self, priority: str) -> str:
        return {
            "critical": "🔴",
            "high":     "🟠",
            "medium":   "🟡",
            "low":      "⚪",
        }.get(priority, "⚪")