"""
Discord notification system for PR Triage Bot.
Sends rich embeds to Discord channels.
"""

from dataclasses import dataclass
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DiscordConfig:
    webhook_url: str
    username: str = "PR Triage Bot"
    avatar_url: str = "https://github.com/bskomal/pr-triage-bot/raw/main/docs/bot-avatar.png"


class DiscordNotifier:
    """
    Sends rich Discord embeds for PR analysis results.
    Uses Discord webhook API with embeds.
    """

    def __init__(self, config: DiscordConfig):
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
        """Send PR analysis to Discord."""

        color = (
            0x3fb950 if quality_score >= 80
            else 0x58a6ff if quality_score >= 60
            else 0xd29922 if quality_score >= 40
            else 0xf85149
        )

        # Slop color override
        if is_slop:
            color = 0xf85149

        fields = [
            {
                "name": "📊 Quality Score",
                "value": f"**{quality_score}/100** ({quality_tier})",
                "inline": True,
            },
            {
                "name": "🎯 Priority",
                "value": priority.title(),
                "inline": True,
            },
            {
                "name": "🏷️ Type",
                "value": pr_type.title(),
                "inline": True,
            },
            {
                "name": "🛡️ Slop Detection",
                "value": f"{'🚫 Flagged' if is_slop else '✅ Clean'} ({slop_confidence:.0%})",
                "inline": True,
            },
        ]

        if labels:
            fields.append({
                "name": "🏷️ Labels Applied",
                "value": ", ".join(f"`{l}`" for l in labels),
                "inline": False,
            })

        if feedback:
            fields.append({
                "name": "💡 Feedback",
                "value": feedback,
                "inline": False,
            })

        embed = {
            "title": f"{'🚫 AI Slop Flagged' if is_slop else '✅ PR Analyzed'} — #{pr_number}",
            "description": f"**[{title}]({url})**\n`{repo}` • @{author}",
            "color": color,
            "fields": fields,
            "footer": {
                "text": "PR Triage Bot • Powered by Llama 3.2",
            },
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        }

        payload = {
            "username": self.config.username,
            "avatar_url": self.config.avatar_url,
            "embeds": [embed],
        }

        return await self._send(payload)

    async def send_daily_digest(
        self,
        repo: str,
        total_prs: int,
        critical_prs: int,
        slop_flagged: int,
        avg_quality: int,
        critical_list: list[dict],
        flagged_list: list[dict],
    ) -> bool:
        """Send daily digest embed to Discord."""

        health_color = (
            0x3fb950 if avg_quality >= 70
            else 0xd29922 if avg_quality >= 50
            else 0xf85149
        )

        description = (
            f"**Repository:** `{repo}`\n\n"
            f"📊 **{total_prs}** PRs analyzed\n"
            f"⭐ Avg quality: **{avg_quality}/100**\n"
            f"🔥 Critical: **{critical_prs}**\n"
            f"🚫 Slop flagged: **{slop_flagged}**"
        )

        fields = []

        if critical_list:
            critical_text = "\n".join(
                f"• [#{pr['number']}]({pr['url']}) — {pr['title'][:40]}"
                for pr in critical_list[:5]
            )
            fields.append({
                "name": "🔥 Critical PRs",
                "value": critical_text,
                "inline": False,
            })

        if flagged_list:
            flagged_text = "\n".join(
                f"• [#{pr['number']}]({pr['url']}) — {pr['title'][:40]}"
                for pr in flagged_list[:5]
            )
            fields.append({
                "name": "🚫 Flagged PRs",
                "value": flagged_text,
                "inline": False,
            })

        embed = {
            "title": "📋 Daily Triage Digest",
            "description": description,
            "color": health_color,
            "fields": fields,
            "footer": {
                "text": "PR Triage Bot • Daily Digest",
            },
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        }

        payload = {
            "username": self.config.username,
            "avatar_url": self.config.avatar_url,
            "embeds": [embed],
        }

        return await self._send(payload)

    async def _send(self, payload: dict) -> bool:
        """Send payload to Discord webhook."""
        try:
            async with httpx.AsyncClient(
                timeout=10
            ) as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                )
                if response.status_code in (200, 204):
                    logger.info(
                        "Discord notification sent"
                    )
                    return True
                else:
                    logger.warning(
                        "Discord notification failed",
                        status=response.status_code,
                    )
                    return False
        except Exception as e:
            logger.error(
                "Discord send error",
                error=str(e)
            )
            return False