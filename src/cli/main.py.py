"""
PR Triage Bot CLI — Main entry point.
Built with Click for rich terminal UX.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
import structlog
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from src.ai.llm_client import LLMClient, LLMConfig, LLMProvider
from src.core.analyzer import Analyzer
from src.digest.generator import DigestGenerator
from src.github.client import GitHubClient

load_dotenv()
console = Console()

# ─────────────────────────────────────────────
# Configure structured logging
# ─────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer() if os.getenv("DEBUG") else structlog.processors.JSONRenderer(),
    ]
)


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    path = Path(config_path)
    if not path.exists():
        default_path = Path(__file__).parent.parent.parent / "config" / "default.yml"
        if default_path.exists():
            path = default_path
        else:
            return {}

    with open(path) as f:
        return yaml.safe_load(f) or {}


@click.group()
@click.version_option(version="1.0.0")
@click.option("--config", default="config/default.yml", help="Config file path")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, config: str, debug: bool):
    """
    πŸ€– PR Triage Bot — AI-powered maintainer co-pilot.

    Automatically triage pull requests and issues in your GitHub repository.
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    ctx.obj["debug"] = debug

    if debug:
        os.environ["DEBUG"] = "1"

    console.print(
        Panel.fit(
            "[bold blue]πŸ€– PR Triage Bot[/bold blue] [dim]v1.0.0[/dim]",
            border_style="blue",
        )
    )


@cli.command()
@click.option("--repo", required=True, help="GitHub repo (owner/repo)")
@click.option("--token", envvar="GITHUB_TOKEN", required=True, help="GitHub token")
@click.option("--max-prs", default=50, help="Max PRs to analyze")
@click.option("--max-issues", default=100, help="Max issues to analyze")
@click.option("--dry-run", is_flag=True, help="Preview without making changes")
@click.option("--provider", default="ollama", type=click.Choice(["ollama", "openai"]))
@click.option("--model", default="llama3.2", help="LLM model to use")
@click.option("--output", default="markdown", type=click.Choice(["markdown", "slack", "discord"]))
@click.pass_context
def triage(
    ctx: click.Context,
    repo: str,
    token: str,
    max_prs: int,
    max_issues: int,
    dry_run: bool,
    provider: str,
    model: str,
    output: str,
):
    """Run full repository triage."""
    config = ctx.obj["config"]

    if dry_run:
        console.print("[yellow]⚠️ DRY RUN — No changes will be made[/yellow]")

    async def _run():
        async with LLMClient(
            LLMConfig(
                provider=LLMProvider(provider),
                model=model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        ) as llm:
            github = GitHubClient(
                token=token,
                repo_name=repo,
                rate_limit_buffer=config.get("github", {}).get("rate_limit_buffer", 100),
            )

            # Setup labels
            label_configs = []
            for category in ["priority", "type", "quality", "status"]:
                label_configs.extend(
                    config.get("labels", {}).get(category, [])
                )

            if label_configs and not dry_run:
                with console.status("Creating labels..."):
                    github.ensure_labels_exist(label_configs)

            analyzer = Analyzer(
                llm_client=llm,
                github_client=github,
                dry_run=dry_run,
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running triage...", total=None)
                report = await analyzer.run_full_triage(
                    max_prs=max_prs,
                    max_issues=max_issues,
                )
                progress.update(task, completed=True)

            # Display results
            _display_triage_results(report, console)

            # Generate digest
            digest = DigestGenerator().generate(report, format=output)

            # Save digest
            output_path = Path(f"triage-digest-{report.generated_at.strftime('%Y%m%d-%H%M')}.md")
            output_path.write_text(digest)
            console.print(f"\n[green]βœ… Digest saved to:[/green] {output_path}")

    asyncio.run(_run())


@cli.command()
@click.option("--repo", required=True, help="GitHub repo (owner/repo)")
@click.option("--token", envvar="GITHUB_TOKEN", required=True)
@click.option("--pr", "pr_number", required=True, type=int, help="PR number to analyze")
@click.option("--dry-run", is_flag=True)
@click.option("--provider", default="ollama", type=click.Choice(["ollama", "openai"]))
@click.pass_context
def analyze_pr(
    ctx: click.Context,
    repo: str,
    token: str,
    pr_number: int,
    dry_run: bool,
    provider: str,
):
    """Analyze a single pull request."""

    async def _run():
        async with LLMClient(
            LLMConfig(
                provider=LLMProvider(provider),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        ) as llm:
            github = GitHubClient(token=token, repo_name=repo)
            prs = github.get_open_prs(max_count=200)
            pr = next((p for p in prs if p.number == pr_number), None)

            if not pr:
                console.print(f"[red]PR #{pr_number} not found or not open[/red]")
                sys.exit(1)

            analyzer = Analyzer(llm_client=llm, github_client=github, dry_run=dry_run)

            with console.status(f"Analyzing PR #{pr_number}..."):
                result = await analyzer.analyze_pr(pr)

            _display_pr_result(result, console)

    asyncio.run(_run())


@cli.command()
@click.option("--repo", required=True)
@click.option("--token", envvar="GITHUB_TOKEN", required=True)
def stats(repo: str, token: str):
    """Show repository triage statistics."""
    github = GitHubClient(token=token, repo_name=repo)

    with console.status("Fetching stats..."):
        repo_stats = github.get_repo_stats()

    table = Table(title=f"Repository Stats: {repo}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Open PRs", str(repo_stats.open_prs))
    table.add_row("Open Issues", str(repo_stats.open_issues))
    table.add_row("Needs Triage", str(repo_stats.needs_triage))

    console.print(table)


def _display_triage_results(report, console: Console) -> None:
    """Display triage results in rich terminal format."""
    stats = report.stats

    # Summary panel
    summary = (
        f"[bold]Repo:[/bold] {report.repo}\n"
        f"[bold]PRs:[/bold] {stats['total_prs_analyzed']} analyzed | "
        f"[red]{stats['critical_prs']} critical[/red] | "
        f"[yellow]{stats['slop_flagged']} flagged[/yellow] | "
        f"[green]{stats['excellent_quality']} excellent[/green]\n"
        f"[bold]Issues:[/bold] {stats['total_issues_analyzed']} analyzed | "
        f"{stats['duplicate_issues']} duplicates\n"
        f"[bold]Avg Quality Score:[/bold] {stats['avg_quality_score']}/100"
    )

    console.print(Panel(summary, title="πŸ"Š Triage Summary", border_style="green"))

    # Critical PRs table
    if report.critical_prs:
        table = Table(title="πŸ"₯ Critical PRs")
        table.add_column("PR #", style="bold red")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Quality")
        table.add_column("Author")

        for r in report.critical_prs[:10]:
            table.add_row(
                str(r.pr.number),
                r.pr.title[:50],
                r.classification.get("type", "?"),
                f"{r.quality_score.emoji} {r.quality_score.overall}",
                r.pr.author,
            )

        console.print(table)

    # Flagged PRs
    if report.flagged_prs:
        table = Table(title="⚠️ Flagged PRs (AI Slop / Low Quality)")
        table.add_column("PR #", style="bold yellow")
        table.add_column("Title")
        table.add_column("Confidence")
        table.add_column("Severity")
        table.add_column("Author")

        for r in report.flagged_prs[:10]:
            table.add_row(
                str(r.pr.number),
                r.pr.title[:50],
                f"{r.slop_result.confidence:.0%}",
                r.slop_result.severity,
                r.pr.author,
            )

        console.print(table)


def _display_pr_result(result, console: Console) -> None:
    """Display single PR analysis in detail."""
    pr = result.pr
    quality = result.quality_score
    slop = result.slop_result

    console.print(
        Panel(
            f"[bold]PR #{pr.number}:[/bold] {pr.title}\n"
            f"[bold]Author:[/bold] @{pr.author}\n"
            f"[bold]Changes:[/bold] +{pr.additions} / -{pr.deletions} | {len(pr.files_changed)} files",
            title="Pull Request",
            border_style="blue",
        )
    )

    # Quality score table
    table = Table(title=f"Quality Score: {quality.emoji} {quality.overall}/100 ({quality.tier})")
    table.add_column("Dimension")
    table.add_column("Score")
    table.add_column("Reason")

    for dim in quality.dimensions:
        color = "green" if dim.score >= 70 else "yellow" if dim.score >= 40 else "red"
        table.add_row(
            dim.name.replace("_", " ").title(),
            f"[{color}]{dim.score}/100[/{color}]",
            dim.reason,
        )

    console.print(table)

    # Slop detection
    slop_color = "red" if slop.is_suspected_slop else "green"
    console.print(
        Panel(
            f"[bold]Suspected Slop:[/bold] [{slop_color}]{slop.is_suspected_slop}[/{slop_color}]\n"
            f"[bold]Confidence:[/bold] {slop.confidence:.0%}\n"
            f"[bold]Severity:[/bold] {slop.severity}\n"
            f"[bold]Signals:[/bold] {', '.join(slop.signal_names) or 'None'}",
            title="Slop Detection",
            border_style=slop_color,
        )
    )

    # Classification
    console.print(
        Panel(
            f"[bold]Type:[/bold] {result.classification.get('type', 'unknown')}\n"
            f"[bold]Priority:[/bold] {result.classification.get('priority', 'unknown')}\n"
            f"[bold]Complexity:[/bold] {result.classification.get('complexity', 'unknown')}",
            title="Classification",
            border_style="blue",
        )
    )

    # Labels
    if result.recommended_labels:
        console.print(
            f"[bold]Labels Applied:[/bold] {', '.join(result.recommended_labels)}"
        )

    # Feedback
    if quality.feedback:
        console.print(
            Panel(quality.feedback, title="πŸ'' Feedback", border_style="yellow")
        )