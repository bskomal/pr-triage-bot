"""
AI Slop Detector — Identifies low-quality, auto-generated PRs.
Uses both heuristic signals and LLM analysis.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

from src.ai.llm_client import LLMClient
from src.ai.prompts import DETECT_AI_SLOP

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Heuristic signal patterns
# ─────────────────────────────────────────────

GENERIC_COMMIT_PATTERNS = [
    r"^fix\s*(issue|bug|problem|error)?\s*$",
    r"^update\s*(code|file|files)?\s*$",
    r"^improve\s*(performance|code|quality)?\s*$",
    r"^minor\s*(fix|change|update)?\s*$",
    r"^changes?\s*(made)?\s*$",
    r"^wip\s*$",
    r"^initial\s*(commit|changes?)?\s*$",
    r"^add\s*(feature|functionality|stuff)?\s*$",
]

AI_PHRASE_PATTERNS = [
    r"as per your request",
    r"i hope this (helps|resolves|fixes)",
    r"please (let me know|feel free)",
    r"this (implementation|solution|code) (ensures|guarantees|provides)",
    r"leveraging (the power of|advanced)",
    r"utilizing (state-of-the-art|cutting-edge)",
    r"in order to (achieve|accomplish|ensure)",
    r"it is (important|crucial|essential) to note",
    r"as an ai (language model|assistant)",
    r"i (cannot|can't) (browse|access|check) the",
]

TEMPLATE_UNCHANGED_MARKERS = [
    "describe the changes you made",
    "what type of pr is this",
    "related issues",
    "checklist:",
    "[ ] i have performed a self-review",
    "<!-- describe",
    "<!-- please",
    "add a description here",
    "no description provided",
]


@dataclass
class SlopSignal:
    name: str
    detected: bool
    weight: float
    detail: str = ""


@dataclass
class SlopResult:
    is_suspected_slop: bool
    confidence: float
    severity: str  # "low" | "medium" | "high"
    signals: list[SlopSignal] = field(default_factory=list)
    llm_explanation: Optional[str] = None
    recommendation: str = ""

    @property
    def signal_names(self) -> list[str]:
        return [s.name for s in self.signals if s.detected]

    @property
    def heuristic_score(self) -> float:
        """0.0 - 1.0 score from heuristic signals alone."""
        if not self.signals:
            return 0.0
        total_weight = sum(s.weight for s in self.signals)
        triggered_weight = sum(s.weight for s in self.signals if s.detected)
        return triggered_weight / total_weight if total_weight > 0 else 0.0


class SlopDetector:
    """
    Multi-layer AI slop detector.
    Layer 1: Fast heuristic checks (no LLM needed)
    Layer 2: LLM deep analysis (for borderline cases)
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        threshold: float = 0.75,
    ):
        self.llm = llm_client
        self.threshold = threshold

    async def analyze(
        self,
        title: str,
        description: str,
        commit_messages: list[str],
        diff_sample: str = "",
        files_changed: list[str] | None = None,
    ) -> SlopResult:
        """
        Full slop analysis pipeline.
        Returns detailed result with all signals.
        """
        logger.info("Running slop detection", pr_title=title[:60])

        signals = self._run_heuristics(
            title=title,
            description=description,
            commit_messages=commit_messages,
            diff_sample=diff_sample,
            files_changed=files_changed or [],
        )

        heuristic_score = self._compute_score(signals)

        # Run LLM analysis if heuristic score is borderline
        llm_explanation = None
        llm_confidence = None

        if self.llm and heuristic_score > 0.3:
            try:
                llm_result = await self._llm_analyze(
                    title=title,
                    description=description,
                    commit_messages=commit_messages,
                    diff_sample=diff_sample,
                )
                llm_explanation = llm_result.get("explanation", "")
                llm_confidence = llm_result.get("confidence", heuristic_score)

                # Blend heuristic + LLM scores
                final_confidence = (heuristic_score * 0.4) + (llm_confidence * 0.6)

                # Add LLM signals to our list
                for signal_name in llm_result.get("signals_found", []):
                    signals.append(
                        SlopSignal(
                            name=f"llm:{signal_name}",
                            detected=True,
                            weight=0.3,
                            detail="Detected by LLM analysis",
                        )
                    )
            except Exception as e:
                logger.warning("LLM slop analysis failed", error=str(e))
                final_confidence = heuristic_score
        else:
            final_confidence = heuristic_score

        is_slop = final_confidence >= self.threshold
        severity = self._compute_severity(final_confidence)
        recommendation = self._build_recommendation(signals, is_slop, severity)

        result = SlopResult(
            is_suspected_slop=is_slop,
            confidence=round(final_confidence, 3),
            severity=severity,
            signals=signals,
            llm_explanation=llm_explanation,
            recommendation=recommendation,
        )

        logger.info(
            "Slop detection complete",
            is_slop=is_slop,
            confidence=final_confidence,
            severity=severity,
            signals=result.signal_names,
        )

        return result

    def _run_heuristics(
        self,
        title: str,
        description: str,
        commit_messages: list[str],
        diff_sample: str,
        files_changed: list[str],
    ) -> list[SlopSignal]:
        """Run all heuristic checks. Fast, no LLM needed."""
        signals = []

        # 1. Generic commit messages
        generic_commits = self._check_generic_commits(commit_messages)
        signals.append(
            SlopSignal(
                name="generic_commit_messages",
                detected=generic_commits["detected"],
                weight=0.20,
                detail=generic_commits["detail"],
            )
        )

        # 2. Template description unchanged
        template_unchanged = self._check_template_unchanged(description)
        signals.append(
            SlopSignal(
                name="description_template_unchanged",
                detected=template_unchanged["detected"],
                weight=0.25,
                detail=template_unchanged["detail"],
            )
        )

        # 3. AI phrase patterns in description
        ai_phrases = self._check_ai_phrases(description)
        signals.append(
            SlopSignal(
                name="ai_phrase_patterns",
                detected=ai_phrases["detected"],
                weight=0.30,
                detail=ai_phrases["detail"],
            )
        )

        # 4. Empty or minimal description
        minimal_desc = self._check_minimal_description(description)
        signals.append(
            SlopSignal(
                name="minimal_description",
                detected=minimal_desc["detected"],
                weight=0.15,
                detail=minimal_desc["detail"],
            )
        )

        # 5. Whitespace-only changes
        whitespace_only = self._check_whitespace_changes(diff_sample)
        signals.append(
            SlopSignal(
                name="excessive_whitespace_changes",
                detected=whitespace_only["detected"],
                weight=0.10,
                detail=whitespace_only["detail"],
            )
        )

        # 6. No tests added for feature/fix
        no_tests = self._check_no_tests(files_changed)
        signals.append(
            SlopSignal(
                name="no_tests_added",
                detected=no_tests["detected"],
                weight=0.15,
                detail=no_tests["detail"],
            )
        )

        # 7. Title is generic
        generic_title = self._check_generic_title(title)
        signals.append(
            SlopSignal(
                name="generic_title",
                detected=generic_title["detected"],
                weight=0.15,
                detail=generic_title["detail"],
            )
        )

        return signals

    def _check_generic_commits(
        self, commit_messages: list[str]
    ) -> dict[str, str | bool]:
        if not commit_messages:
            return {"detected": True, "detail": "No commit messages found"}

        generic_count = 0
        for msg in commit_messages:
            clean_msg = msg.strip().lower()
            for pattern in GENERIC_COMMIT_PATTERNS:
                if re.match(pattern, clean_msg, re.IGNORECASE):
                    generic_count += 1
                    break

        ratio = generic_count / len(commit_messages)
        detected = ratio >= 0.6

        return {
            "detected": detected,
            "detail": f"{generic_count}/{len(commit_messages)} commits are generic",
        }

    def _check_template_unchanged(
        self, description: str
    ) -> dict[str, str | bool]:
        if not description or len(description.strip()) < 20:
            return {"detected": True, "detail": "Description is empty or too short"}

        desc_lower = description.lower()
        markers_found = [
            marker
            for marker in TEMPLATE_UNCHANGED_MARKERS
            if marker in desc_lower
        ]

        detected = len(markers_found) >= 2
        return {
            "detected": detected,
            "detail": f"Found {len(markers_found)} template markers: {markers_found[:3]}",
        }

    def _check_ai_phrases(self, description: str) -> dict[str, str | bool]:
        if not description:
            return {"detected": False, "detail": "No description"}

        desc_lower = description.lower()
        found_phrases = []

        for pattern in AI_PHRASE_PATTERNS:
            if re.search(pattern, desc_lower, re.IGNORECASE):
                found_phrases.append(pattern[:30])

        detected = len(found_phrases) >= 2
        return {
            "detected": detected,
            "detail": f"Found {len(found_phrases)} AI phrase patterns",
        }

    def _check_minimal_description(
        self, description: str
    ) -> dict[str, str | bool]:
        if not description:
            return {"detected": True, "detail": "No description provided"}

        clean = description.strip()
        word_count = len(clean.split())

        detected = word_count < 15
        return {
            "detected": detected,
            "detail": f"Description has only {word_count} words",
        }

    def _check_whitespace_changes(
        self, diff_sample: str
    ) -> dict[str, str | bool]:
        if not diff_sample:
            return {"detected": False, "detail": "No diff available"}

        lines = diff_sample.split("\n")
        changed_lines = [
            l for l in lines if l.startswith("+") or l.startswith("-")
        ]

        if not changed_lines:
            return {"detected": False, "detail": "No changed lines"}

        whitespace_lines = [
            l for l in changed_lines if len(l.strip()) <= 1
        ]

        ratio = len(whitespace_lines) / len(changed_lines)
        detected = ratio >= 0.8

        return {
            "detected": detected,
            "detail": f"{ratio:.0%} of changes are whitespace only",
        }

    def _check_no_tests(
        self, files_changed: list[str]
    ) -> dict[str, str | bool]:
        if not files_changed:
            return {"detected": False, "detail": "No file information"}

        test_files = [
            f for f in files_changed
            if "test" in f.lower() or "spec" in f.lower()
        ]

        detected = len(test_files) == 0
        return {
            "detected": detected,
            "detail": "No test files included in this PR",
        }

    def _check_generic_title(self, title: str) -> dict[str, str | bool]:
        if not title:
            return {"detected": True, "detail": "No title"}

        generic_titles = [
            r"^fix(es)?\s*(bug|issue|problem|error)s?\s*$",
            r"^update\s*(readme|docs?|code)\s*$",
            r"^(minor|small)\s*(fix|change|update|improvement)\s*$",
            r"^improvements?\s*$",
            r"^changes?\s*$",
        ]

        title_lower = title.strip().lower()
        for pattern in generic_titles:
            if re.match(pattern, title_lower, re.IGNORECASE):
                return {"detected": True, "detail": f"Title matches generic pattern: '{title}'"}

        # Check if title is too short to be meaningful
        if len(title.strip()) < 10:
            return {"detected": True, "detail": f"Title too short: '{title}'"}

        return {"detected": False, "detail": "Title appears specific"}

    async def _llm_analyze(
        self,
        title: str,
        description: str,
        commit_messages: list[str],
        diff_sample: str,
    ) -> dict:
        """Deep LLM analysis for borderline cases."""
        response = await self.llm.complete(
            prompt=DETECT_AI_SLOP,
            variables={
                "title": title,
                "description": description[:800],
                "commit_messages": "\n".join(commit_messages[:5]),
                "diff_sample": diff_sample[:1000],
            },
            expect_json=True,
        )
        return response.parsed or {}

    def _compute_score(self, signals: list[SlopSignal]) -> float:
        """Weighted score from heuristic signals."""
        if not signals:
            return 0.0
        total_weight = sum(s.weight for s in signals)
        triggered = sum(s.weight for s in signals if s.detected)
        return triggered / total_weight if total_weight > 0 else 0.0

    def _compute_severity(self, confidence: float) -> str:
        if confidence >= 0.85:
            return "high"
        elif confidence >= 0.60:
            return "medium"
        else:
            return "low"

    def _build_recommendation(
        self,
        signals: list[SlopSignal],
        is_slop: bool,
        severity: str,
    ) -> str:
        if not is_slop:
            return "PR passes quality checks."

        triggered = [s for s in signals if s.detected]

        if severity == "high":
            return (
                "This PR shows strong signs of AI-generated or low-effort content. "
                "Recommend requesting the contributor to rewrite with specific details. "
                f"Issues: {', '.join(s.name for s in triggered[:3])}"
            )
        elif severity == "medium":
            return (
                "This PR has several quality concerns. "
                "Request more context before review. "
                f"Issues: {', '.join(s.name for s in triggered[:3])}"
            )
        else:
            return (
                "Minor quality concerns detected. "
                "May need additional context from contributor."
            )