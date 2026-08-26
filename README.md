# 🤖 PR Triage Bot

> AI-powered maintainer co-pilot for GitHub repositories.
> Stop drowning in pull requests. Start shipping.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Privacy First](https://img.shields.io/badge/AI-Local%20First-green.svg)](https://ollama.ai)

---

## The Problem

GitHub added 36M developers in 2025. Maintainers now face:
- **AI slop** — auto-generated PRs with zero real value
- **Volume overload** — more contributors than reviewers
- **Signal-to-noise collapse** — finding the 3 PRs that matter in 300

**PR Triage Bot solves all three.**

---

## Features

| Feature | Description |
|---------|-------------|
| 🏷️ Auto-label | Type, priority, complexity on every PR/Issue |
| 🚫 Slop detection | Flag AI-generated junk before it wastes your time |
| 📊 Quality scoring | 0-100 score across 6 dimensions |
| 🔍 Duplicate detection | Semantic duplicate issue detection |
| 📅 Daily digest | "Here's what actually needs your eyes today" |
| 🔒 Privacy-first | Runs on local Ollama by default |
| 🐳 Self-hostable | Full Docker support |

---

## Quick Start

### Option 1 — GitHub Action (recommended)

Add to your repository:

```yaml
# .github/workflows/triage.yml
name: PR Triage

on:
  pull_request:
    types: [opened, synchronize]
  issues:
    types: [opened]
  schedule:
    - cron: '0 9 * * 1-5'

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: your-org/pr-triage-bot@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          ai-provider: openai          # or 'ollama' for local
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Option 2 — CLI

```bash
# Install
pip install -r requirements.txt

# Run triage
python -m src.cli.main triage --repo owner/repo --token ghp_xxx

# Analyze single PR
python -m src.cli.main analyze-pr --repo owner/repo --pr 42

# Dry run (preview only)
python -m src.cli.main triage --repo owner/repo --dry-run
```

### Option 3 — Docker

```bash
# Clone and run
git clone https://github.com/your-org/pr-triage-bot
cd pr-triage-bot

GITHUB_TOKEN=ghp_xxx \
GITHUB_REPO=owner/repo \
docker-compose -f docker/docker-compose.yml up
```

---

## Configuration

Create `config/triage.yml` in your repository:

```yaml
rules:
  auto_close_slop: false
  min_quality_score: 50
  auto_label: true
```

---

## Quality Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Description | 20% | Quality and detail of PR description |
| Test Coverage | 25% | Presence and quality of unit tests |
| Documentation | 20% | Docs updated alongside code |
| Scope Focus | 15% | Focused, atomic changes |
| Commit Quality | 10% | Conventional commits |
| Issue Linkage | 10% | Linked to an issue |

**Tiers:** 🌟 Excellent (80+) | ✅ Good (60+) | ⚠️ Needs Work (40+) | ❌ Poor (<40)

---

## Slop Detection Signals

- Generic commit messages ("fix", "update", "changes")
- Template descriptions left unchanged
- AI phrase patterns ("I hope this helps", "as per your request")
- Whitespace-only changes
- No tests for code changes
- Generic PR titles

---

## Privacy

PR Triage Bot is **privacy-first by design**:
- Defaults to **Ollama** (local LLM, no data leaves your machine)
- OpenAI is an opt-in fallback
- No data is stored or logged externally
- Fully self-hostable

---

## Architecture

```
GitHub Action / CLI
       │
       ▼
   Analyzer (orchestrator)
    ├── SlopDetector (heuristic + LLM)
    ├── PRScorer (6-dimension quality)
    ├── Classifier (type + priority)
    └── DuplicateDetector (semantic)
       │
       ▼
   LLMClient (Ollama / OpenAI)
       │
       ▼
   GitHubClient (labels + comments)
       │
       ▼
   DigestGenerator (markdown/slack/discord)
```

---

## License

MIT — Use it, fork it, ship it.