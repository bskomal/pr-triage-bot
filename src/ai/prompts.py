"""
Centralized prompt templates for PR Triage Bot.
All prompts are versioned and testable.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PromptTemplate:
    name: str
    version: str
    system: str
    user_template: str


# ─────────────────────────────────────────────
# CLASSIFICATION PROMPT
# ─────────────────────────────────────────────
CLASSIFY_PR = PromptTemplate(
    name="classify_pr",
    version="1.0.0",
    system="""You are an expert open source maintainer analyzing pull requests.
Your job is to classify PRs accurately and consistently.
Always respond with valid JSON only. No explanation. No markdown.
Be strict — wrong classifications waste maintainer time.""",
    user_template="""Analyze this pull request and classify it.

TITLE: {title}
DESCRIPTION: {description}
FILES CHANGED: {files_changed}
ADDITIONS: {additions} lines
DELETIONS: {deletions} lines
COMMIT MESSAGES: {commit_messages}

Respond with this exact JSON structure:
{{
  "type": "bug|feature|docs|refactor|test|chore|security",
  "priority": "critical|high|medium|low",
  "complexity": "trivial|small|medium|large|xl",
  "confidence": 0.0-1.0,
  "reasoning": "one sentence explanation"
}}""",
)


# ─────────────────────────────────────────────
# QUALITY SCORING PROMPT
# ─────────────────────────────────────────────
SCORE_QUALITY = PromptTemplate(
    name="score_quality",
    version="1.0.0",
    system="""You are a senior code reviewer evaluating PR quality.
Score objectively based on evidence in the PR, not assumptions.
Always respond with valid JSON only.""",
    user_template="""Evaluate the quality of this pull request.

TITLE: {title}
DESCRIPTION: {description}
HAS TESTS: {has_tests}
HAS DOCS UPDATE: {has_docs}
FILES CHANGED: {files_changed}
TEST FILES CHANGED: {test_files}
DESCRIPTION LENGTH: {description_length} characters

Score each dimension from 0-100:
{{
  "description_quality": 0-100,
  "test_coverage": 0-100,
  "documentation": 0-100,
  "scope_focus": 0-100,
  "overall_score": 0-100,
  "tier": "excellent|good|needs-work|poor",
  "feedback": "one actionable sentence for the contributor"
}}""",
)


# ─────────────────────────────────────────────
# AI SLOP DETECTION PROMPT
# ─────────────────────────────────────────────
DETECT_AI_SLOP = PromptTemplate(
    name="detect_ai_slop",
    version="1.0.0",
    system="""You are an expert at detecting AI-generated or low-effort contributions.
Look for specific patterns that indicate automated or careless submissions.
Be precise — false positives harm real contributors.
Always respond with valid JSON only.""",
    user_template="""Analyze this PR for signs of AI-generated or low-effort content.

TITLE: {title}
DESCRIPTION: {description}
COMMIT MESSAGES: {commit_messages}
DIFF SAMPLE: {diff_sample}

Red flags to look for:
- Generic, template-like descriptions
- Commit messages like "fix issue", "update code", "improve performance" with no specifics
- Description that doesn't match the actual code changes
- Excessive whitespace-only changes
- Boilerplate text that matches no specific problem
- Overly formal language inconsistent with technical content
- Claims of fixing things not visible in the diff

Respond with:
{{
  "is_suspected_slop": true|false,
  "confidence": 0.0-1.0,
  "signals_found": ["list", "of", "specific", "signals"],
  "severity": "low|medium|high",
  "explanation": "specific reasoning based on evidence"
}}""",
)


# ─────────────────────────────────────────────
# DUPLICATE DETECTION PROMPT
# ─────────────────────────────────────────────
DETECT_DUPLICATE = PromptTemplate(
    name="detect_duplicate",
    version="1.0.0",
    system="""You are analyzing GitHub issues to find duplicates.
Consider semantic similarity, not just keyword matching.
A duplicate addresses the same underlying problem even with different wording.
Always respond with valid JSON only.""",
    user_template="""Is this new issue a duplicate of any existing issues?

NEW ISSUE:
Title: {new_title}
Body: {new_body}

EXISTING ISSUES TO COMPARE:
{existing_issues}

Respond with:
{{
  "is_duplicate": true|false,
  "duplicate_of": null or issue_number,
  "confidence": 0.0-1.0,
  "similarity_reason": "explanation of why they are or aren't duplicates"
}}""",
)


# ─────────────────────────────────────────────
# ISSUE CLASSIFICATION PROMPT
# ─────────────────────────────────────────────
CLASSIFY_ISSUE = PromptTemplate(
    name="classify_issue",
    version="1.0.0",
    system="""You are an expert open source maintainer triaging GitHub issues.
Classify issues accurately to help route them to the right people.
Always respond with valid JSON only.""",
    user_template="""Classify this GitHub issue.

TITLE: {title}
BODY: {body}
LABELS ALREADY APPLIED: {existing_labels}

Respond with:
{{
  "type": "bug|feature|question|docs|security|performance|ux",
  "priority": "critical|high|medium|low",
  "needs_more_info": true|false,
  "missing_info": ["list of what's missing, empty if complete"],
  "confidence": 0.0-1.0,
  "one_line_summary": "crisp summary under 100 chars"
}}""",
)


# ─────────────────────────────────────────────
# DIGEST GENERATION PROMPT
# ─────────────────────────────────────────────
GENERATE_DIGEST_SUMMARY = PromptTemplate(
    name="generate_digest",
    version="1.0.0",
    system="""You are a technical writer creating a maintainer digest.
Be concise, actionable, and prioritize correctly.
Use markdown. No fluff. Maintainers are busy.""",
    user_template="""Generate a maintainer digest from this triage data.

REPOSITORY: {repo_name}
DATE: {date}
TRIAGE DATA:
{triage_data}

Create a digest with:
1. πŸ"₯ Critical Items (needs action today)
2. πŸ'€ Needs Review (good PRs waiting)
3. ⚠️ Flagged Items (ai slop, low quality)
4. πŸ"‹ Summary Stats

Be specific about PR/Issue numbers. Be actionable.""",
)


def get_prompt(name: str) -> PromptTemplate:
    """Retrieve a prompt template by name."""
    prompts = {
        "classify_pr": CLASSIFY_PR,
        "score_quality": SCORE_QUALITY,
        "detect_ai_slop": DETECT_AI_SLOP,
        "detect_duplicate": DETECT_DUPLICATE,
        "classify_issue": CLASSIFY_ISSUE,
        "generate_digest": GENERATE_DIGEST_SUMMARY,
    }
    if name not in prompts:
        raise ValueError(f"Unknown prompt: {name}. Available: {list(prompts.keys())}")
    return prompts[name]