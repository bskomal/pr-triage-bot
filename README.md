# πŸ€– PR Triage Bot

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
| πŸ†• Auto-label | Type, priority, complexity on every PR/Issue |
| 🚫 Slop detection | Flag AI-generated junk before it wastes your time |
| πŸ"Š Quality scoring | 0-100 score across 6 dimensions |
| πŸ" Duplicate detection | Semantic duplicate issue detection |
| πŸ"… Daily digest | "Here's what actually needs your eyes today" |
| πŸ" Privacy-first | Runs on local Ollama by default |
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
pip install pr-triage-bot

# Run triage
triage triage --repo owner/repo --token ghp_xxx

# Analyze single PR
triage analyze-pr --repo owner/repo --pr 42

# Dry run (preview only)
triage triage --repo owner/repo --dry-run
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
bot:
  dry_run: false

ai:
  provider: ollama       # Local by default (privacy-first)
  model: llama3.2

slop_detection:
  enabled: true
  threshold: 0.75        # 0-1, higher = more aggressive

scoring:
  weights:
    has_tests: 25
    has_docs: 20
    description_quality: 20

digest:
  enabled: true
  output_format: markdown
```

---

## Quality Score

Every PR receives a score across 6 dimensions:

| Dimension | Weight | What it checks |
|-----------|--------|---------------|
| Test Coverage | 25% | Test files included |
| Description Quality | 20% | Length, structure, specificity |
| Documentation | 20% | Docs updated |
| Scope Focus | 15% | PR size appropriate |
| Commit Quality | 10% | Conventional commits |
| Issue Linkage | 10% | Linked to an issue |

**Tiers:** 🌟 Excellent (80+) | βœ… Good (60+) | ⚠️ Needs Work (40+) | ❌ Poor (<40)

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
       β"‚
       β–Ό
   Analyzer (orchestrator)
    β"œβ"€β"€ SlopDetector (heuristic + LLM)
    β"œβ"€β"€ PRScorer (6-dimension quality)
    β"œβ"€β"€ Classifier (type + priority)
    └── DuplicateDetector (semantic)
       β"‚
       β–Ό
   LLMClient (Ollama / OpenAI)
       β"‚
       β–Ό
   GitHubClient (labels + comments)
       β"‚
       β–Ό
   DigestGenerator (markdown/slack/discord)
```

---

## License

MIT — Use it, fork it, ship it.