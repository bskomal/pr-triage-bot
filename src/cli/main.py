"""
PR Triage Bot CLI — Main entry point.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
import structlog
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()

# ─── Setup logging ────────────────────────────
Path("logs").mkdir(exist_ok=True)

file_handler = logging.FileHandler("logs/triage.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler],
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        default_path = (
            Path(__file__).parent.parent.parent
            / "config"
            / "default.yml"
        )
        if default_path.exists():
            path = default_path
        else:
            return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


@click.group()
@click.version_option(version="1.0.0")
@click.option(
    "--config",
    default="config/default.yml",
    help="Config file path"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.pass_context
def cli(ctx, config, debug):
    """
    \b
    PR Triage Bot — AI-powered maintainer co-pilot.
    Automatically triage pull requests and issues.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    ctx.obj["debug"] = debug

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="ISO"),
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

    console.print(
        Panel.fit(
            "[bold blue]PR Triage Bot[/bold blue] "
            "[dim]v1.0.0[/dim]",
            border_style="blue",
        )
    )


@cli.command(name="analyze-pr")
@click.option(
    "--repo",
    required=True,
    help="GitHub repo: owner/repo"
)
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    required=True,
    help="GitHub personal access token"
)
@click.option(
    "--pr",
    "pr_number",
    required=True,
    type=int,
    help="PR number to analyze"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview without making changes"
)
@click.option(
    "--provider",
    default="ollama",
    type=click.Choice(["ollama", "openai"]),
    help="AI provider"
)
@click.option(
    "--model",
    default="llama3.2",
    help="AI model name"
)
@click.pass_context
def analyze_pr(
    ctx, repo, token, pr_number,
    dry_run, provider, model
):
    """Analyze a single pull request."""

    console.print(
        f"[cyan]Analyzing PR #{pr_number} "
        f"in {repo}[/cyan]"
    )
    console.print(
        f"[dim]Provider: {provider} | "
        f"Model: {model}[/dim]"
    )

    if dry_run:
        console.print(
            "[yellow]DRY RUN — No changes will "
            "be made[/yellow]"
        )

    async def _run():
        try:
            from src.ai.llm_client import (
                LLMClient, LLMConfig, LLMProvider
            )
            from src.core.analyzer import Analyzer
            from src.github.client import GitHubClient

            console.print(
                "[dim]Connecting to GitHub...[/dim]"
            )
            github = GitHubClient(
                token=token,
                repo_name=repo,
            )

            console.print("[dim]Loading PRs...[/dim]")
            prs = github.get_open_prs(max_count=200)
            pr = next(
                (p for p in prs if p.number == pr_number),
                None
            )

            if not pr:
                console.print(
                    f"[red]PR #{pr_number} not found "
                    f"or not open[/red]"
                )
                return

            console.print(
                f"[green]Found PR: {pr.title}[/green]"
            )

            llm_config = LLMConfig(
                provider=LLMProvider(provider),
                model=model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )

            console.print(
                "[dim]Starting AI analysis...[/dim]"
            )

            async with LLMClient(llm_config) as llm:
                analyzer = Analyzer(
                    llm_client=llm,
                    github_client=github,
                    dry_run=dry_run,
                )
                result = await analyzer.analyze_pr(pr)

            # ── Display Results ──────────────────
            console.print("\n")
            console.print(
                Panel(
                    f"[bold]Title:[/bold] {pr.title}\n"
                    f"[bold]Author:[/bold] @{pr.author}\n"
                    f"[bold]Changes:[/bold] "
                    f"+{pr.additions} / -{pr.deletions}"
                    f" | {len(pr.files_changed)} files",
                    title=f"PR #{pr.number}",
                    border_style="blue",
                )
            )

            # Quality Score
            quality = result.quality_score
            table = Table(
                title=(
                    f"Quality Score: {quality.emoji} "
                    f"{quality.overall}/100 "
                    f"({quality.tier})"
                )
            )
            table.add_column("Dimension", style="cyan")
            table.add_column("Score", style="bold")
            table.add_column("Reason")

            for dim in quality.dimensions:
                color = (
                    "green" if dim.score >= 70
                    else "yellow" if dim.score >= 40
                    else "red"
                )
                table.add_row(
                    dim.name.replace("_", " ").title(),
                    f"[{color}]{dim.score}/100[/{color}]",
                    dim.reason,
                )
            console.print(table)

            # Slop Detection
            slop = result.slop_result
            slop_color = (
                "red" if slop.is_suspected_slop
                else "green"
            )
            console.print(
                Panel(
                    f"[bold]Suspected Slop:[/bold] "
                    f"[{slop_color}]"
                    f"{slop.is_suspected_slop}"
                    f"[/{slop_color}]\n"
                    f"[bold]Confidence:[/bold] "
                    f"{slop.confidence:.0%}\n"
                    f"[bold]Severity:[/bold] "
                    f"{slop.severity}\n"
                    f"[bold]Signals:[/bold] "
                    f"{', '.join(slop.signal_names) or 'None'}",
                    title="Slop Detection",
                    border_style=slop_color,
                )
            )

            # Classification
            console.print(
                Panel(
                    f"[bold]Type:[/bold] "
                    f"{result.classification.get('type', '?')}\n"
                    f"[bold]Priority:[/bold] "
                    f"{result.classification.get('priority', '?')}\n"
                    f"[bold]Complexity:[/bold] "
                    f"{result.classification.get('complexity', '?')}",
                    title="Classification",
                    border_style="blue",
                )
            )

            # Labels
            if result.recommended_labels:
                console.print(
                    f"\n[bold]Labels:[/bold] "
                    f"{', '.join(result.recommended_labels)}"
                )

            # Feedback
            if quality.feedback:
                console.print(
                    Panel(
                        quality.feedback,
                        title="Feedback",
                        border_style="yellow",
                    )
                )

            console.print(
                f"\n[green]✅ Analysis complete in "
                f"{result.analysis_time_ms}ms[/green]"
            )

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if ctx.obj.get("debug"):
                import traceback
                traceback.print_exc()

    asyncio.run(_run())


@cli.command(name="triage")
@click.option(
    "--repo", required=True,
    help="GitHub repo owner/repo"
)
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    required=True
)
@click.option("--max-prs", default=50, type=int)
@click.option("--max-issues", default=100, type=int)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False
)
@click.option(
    "--provider",
    default="ollama",
    type=click.Choice(["ollama", "openai"])
)
@click.option("--model", default="llama3.2")
@click.option(
    "--output",
    default="markdown",
    type=click.Choice(["markdown", "slack", "discord"])
)
@click.pass_context
def triage(
    ctx, repo, token, max_prs,
    max_issues, dry_run, provider, model, output
):
    """Run full repository triage."""
    console.print(
        f"[cyan]Running full triage on {repo}[/cyan]"
    )

    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow]")

    async def _run():
        try:
            from src.ai.llm_client import (
                LLMClient, LLMConfig, LLMProvider
            )
            from src.core.analyzer import Analyzer
            from src.digest.generator import DigestGenerator
            from src.github.client import GitHubClient

            github = GitHubClient(
                token=token,
                repo_name=repo
            )
            llm_config = LLMConfig(
                provider=LLMProvider(provider),
                model=model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )

            async with LLMClient(llm_config) as llm:
                analyzer = Analyzer(
                    llm_client=llm,
                    github_client=github,
                    dry_run=dry_run,
                )
                console.print(
                    "[dim]Running triage...[/dim]"
                )
                report = await analyzer.run_full_triage(
                    max_prs=max_prs,
                    max_issues=max_issues,
                )

            stats = report.stats
            console.print(
                Panel(
                    f"[bold]PRs Analyzed:[/bold] "
                    f"{stats['total_prs_analyzed']}\n"
                    f"[bold]Issues Analyzed:[/bold] "
                    f"{stats['total_issues_analyzed']}\n"
                    f"[bold]Critical:[/bold] "
                    f"[red]{stats['critical_prs']}[/red]\n"
                    f"[bold]Flagged:[/bold] "
                    f"[yellow]{stats['slop_flagged']}[/yellow]\n"
                    f"[bold]Excellent:[/bold] "
                    f"[green]{stats['excellent_quality']}[/green]\n"
                    f"[bold]Avg Quality:[/bold] "
                    f"{stats['avg_quality_score']}/100",
                    title="Triage Summary",
                    border_style="green",
                )
            )

            digest = DigestGenerator().generate(
                report, format=output
            )
            output_path = Path(
                f"triage-digest-"
                f"{report.generated_at.strftime('%Y%m%d-%H%M')}"
                f".md"
            )
            output_path.write_text(
                digest,
                encoding="utf-8"
            )
            console.print(
                f"[green]✅ Digest saved: "
                f"{output_path}[/green]"
            )

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if ctx.obj.get("debug"):
                import traceback
                traceback.print_exc()

    asyncio.run(_run())


@cli.command(name="stats")
@click.option("--repo", required=True)
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    required=True
)
def stats(repo, token):
    """Show repository statistics."""
    try:
        from src.github.client import GitHubClient

        github = GitHubClient(
            token=token,
            repo_name=repo
        )

        with console.status("Fetching stats..."):
            repo_stats = github.get_repo_stats()

        table = Table(title=f"Stats: {repo}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold white")
        table.add_row("Open PRs", str(repo_stats.open_prs))
        table.add_row(
            "Open Issues",
            str(repo_stats.open_issues)
        )
        table.add_row(
            "Needs Triage",
            str(repo_stats.needs_triage)
        )
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()