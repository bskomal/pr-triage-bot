"""
GitHub API client — wraps PyGithub with rate limiting,
caching, and clean data models.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generator, Optional

import structlog
from github import Github, GithubException, RateLimitExceededException
from github.PullRequest import PullRequest
from github.Issue import Issue

logger = structlog.get_logger(__name__)


@dataclass
class PRData:
    """Clean representation of a GitHub Pull Request."""
    number: int
    title: str
    description: str
    body: str
    author: str
    created_at: datetime
    updated_at: datetime
    state: str
    draft: bool
    files_changed: list[str]
    additions: int
    deletions: int
    commit_messages: list[str]
    linked_issues: list[int]
    existing_labels: list[str]
    url: str
    head_sha: str

    @property
    def diff_sample(self) -> str:
        """Sample of the diff for analysis (first 2000 chars)."""
        return ""  # Populated separately when needed


@dataclass
class IssueData:
    """Clean representation of a GitHub Issue."""
    number: int
    title: str
    body: str
    author: str
    created_at: datetime
    updated_at: datetime
    state: str
    labels: list[str]
    comments_count: int
    url: str


@dataclass
class RepoStats:
    """Repository triage statistics."""
    open_prs: int
    open_issues: int
    stale_prs: int
    needs_triage: int
    last_updated: datetime = field(default_factory=datetime.utcnow)


class GitHubClient:
    """
    Production-grade GitHub API client.
    Handles rate limiting, pagination, and data normalization.
    """

    def __init__(
        self,
        token: str,
        repo_name: str,
        rate_limit_buffer: int = 100,
    ):
        self._gh = Github(token, per_page=100)
        self._repo_name = repo_name
        self._repo = None
        self._rate_limit_buffer = rate_limit_buffer

        logger.info(
            "GitHub client initialized",
            repo=repo_name,
        )

    @property
    def repo(self):
        """Lazy-load repository."""
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    def get_open_prs(
        self,
        max_count: int = 50,
        skip_drafts: bool = False,
    ) -> list[PRData]:
        """Fetch and normalize open pull requests."""
        self._check_rate_limit()

        pulls = []
        for pr in self.repo.get_pulls(state="open", sort="updated", direction="desc"):
            if len(pulls) >= max_count:
                break

            if skip_drafts and pr.draft:
                logger.debug("Skipping draft PR", pr_number=pr.number)
                continue

            try:
                pulls.append(self._normalize_pr(pr))
            except Exception as e:
                logger.error(
                    "Failed to normalize PR",
                    pr_number=pr.number,
                    error=str(e),
                )

        logger.info("Fetched open PRs", count=len(pulls))
        return pulls

    def get_open_issues(
        self,
        max_count: int = 100,
        exclude_prs: bool = True,
    ) -> list[IssueData]:
        """Fetch and normalize open issues."""
        self._check_rate_limit()

        issues = []
        for issue in self.repo.get_issues(state="open", sort="updated", direction="desc"):
            if len(issues) >= max_count:
                break

            # GitHub returns PRs as issues — filter them out
            if exclude_prs and issue.pull_request:
                continue

            try:
                issues.append(self._normalize_issue(issue))
            except Exception as e:
                logger.error(
                    "Failed to normalize issue",
                    issue_number=issue.number,
                    error=str(e),
                )

        logger.info("Fetched open issues", count=len(issues))
        return issues

    def add_labels(self, number: int, labels: list[str], is_pr: bool = True) -> bool:
        """Add labels to a PR or issue."""
        self._check_rate_limit()

        try:
            item = (
                self.repo.get_pull(number)
                if is_pr
                else self.repo.get_issue(number)
            )
            item.add_to_labels(*labels)
            logger.info(
                "Labels added",
                number=number,
                labels=labels,
                type="PR" if is_pr else "Issue",
            )
            return True
        except GithubException as e:
            logger.error(
                "Failed to add labels",
                number=number,
                labels=labels,
                error=str(e),
            )
            return False

    def post_comment(
        self,
        number: int,
        body: str,
        is_pr: bool = True,
    ) -> bool:
        """Post a comment on a PR or issue."""
        self._check_rate_limit()

        try:
            item = (
                self.repo.get_pull(number)
                if is_pr
                else self.repo.get_issue(number)
            )
            item.create_issue_comment(body)
            logger.info(
                "Comment posted",
                number=number,
                type="PR" if is_pr else "Issue",
            )
            return True
        except GithubException as e:
            logger.error(
                "Failed to post comment",
                number=number,
                error=str(e),
            )
            return False

    def ensure_labels_exist(self, label_configs: list[dict]) -> None:
        """Create labels if they don't exist in the repo."""
        existing = {label.name for label in self.repo.get_labels()}

        for label_config in label_configs:
            name = label_config["name"]
            if name not in existing:
                try:
                    self.repo.create_label(
                        name=name,
                        color=label_config.get("color", "ededed"),
                        description=label_config.get("description", ""),
                    )
                    logger.info("Created label", name=name)
                except GithubException as e:
                    logger.warning("Failed to create label", name=name, error=str(e))

    def get_pr_diff_sample(self, pr_number: int, max_chars: int = 2000) -> str:
        """Fetch a sample of the PR diff for analysis."""
        self._check_rate_limit()

        try:
            pr = self.repo.get_pull(pr_number)
            diff_parts = []

            for file in pr.get_files():
                if file.patch:
                    diff_parts.append(f"--- {file.filename}\n{file.patch}")
                if sum(len(d) for d in diff_parts) >= max_chars:
                    break

            return "\n".join(diff_parts)[:max_chars]
        except Exception as e:
            logger.warning("Failed to fetch diff", pr_number=pr_number, error=str(e))
            return ""

    def get_repo_stats(self) -> RepoStats:
        """Get current repository triage statistics."""
        self._check_rate_limit()

        open_prs = self.repo.get_pulls(state="open").totalCount
        open_issues = self.repo.get_issues(
            state="open"
        ).totalCount - open_prs  # Issues minus PRs

        # Count items needing triage (no labels)
        needs_triage = sum(
            1 for issue in self.repo.get_issues(state="open")
            if not issue.pull_request and len(list(issue.labels)) == 0
        )

        return RepoStats(
            open_prs=open_prs,
            open_issues=max(open_issues, 0),
            stale_prs=0,  # Calculated separately
            needs_triage=needs_triage,
        )

    def _normalize_pr(self, pr: PullRequest) -> PRData:
        """Convert GitHub API PR object to clean PRData."""
        files = list(pr.get_files())
        commits = list(pr.get_commits())

        return PRData(
            number=pr.number,
            title=pr.title or "",
            description=pr.body or "",
            body=pr.body or "",
            author=pr.user.login if pr.user else "unknown",
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            state=pr.state,
            draft=pr.draft,
            files_changed=[f.filename for f in files],
            additions=pr.additions,
            deletions=pr.deletions,
            commit_messages=[c.commit.message for c in commits],
            linked_issues=self._extract_issue_numbers(pr.body or ""),
            existing_labels=[label.name for label in pr.labels],
            url=pr.html_url,
            head_sha=pr.head.sha,
        )

    def _normalize_issue(self, issue: Issue) -> IssueData:
        """Convert GitHub API Issue object to clean IssueData."""
        return IssueData(
            number=issue.number,
            title=issue.title or "",
            body=issue.body or "",
            author=issue.user.login if issue.user else "unknown",
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            state=issue.state,
            labels=[label.name for label in issue.labels],
            comments_count=issue.comments,
            url=issue.html_url,
        )

    def _extract_issue_numbers(self, text: str) -> list[int]:
        """Extract referenced issue numbers from PR body."""
        import re
        pattern = r"(?:closes|fixes|resolves|related to)\s+#(\d+)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        return [int(m) for m in matches]

    def _check_rate_limit(self) -> None:
        """Check rate limit and wait if necessary."""
        try:
            rate_limit = self._gh.get_rate_limit()
            remaining = rate_limit.core.remaining

            if remaining < self._rate_limit_buffer:
                reset_time = rate_limit.core.reset
                wait_seconds = (reset_time - datetime.utcnow()).seconds + 10

                logger.warning(
                    "Rate limit low — waiting for reset",
                    remaining=remaining,
                    wait_seconds=wait_seconds,
                )
                import time
                time.sleep(min(wait_seconds, 3600))

        except Exception as e:
            logger.warning("Failed to check rate limit", error=str(e))