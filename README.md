# GitHub PR Agent - AutoCTO

**The AI Staff Engineer every repository deserves.** Project #3 in the
[AI ecosystem roadmap](../ROADMAP.md).

This repo is the **engineering-manager layer**: it understands a repository, reports on its
health, triages its issues, and drafts a pull-request plan. It deliberately does **not** write
the code. On the free/local model the ecosystem uses, analysis and planning are reliable while
code generation is not - so implementation is handed to the **`/github-pr` Claude Code skill**,
which does the real PR work (write the fix, run tests, open the PR after your approval).

> **One-click run:** the ecosystem launcher one level up (`..\run.cmd`) can run this alongside
> the other projects. Or use it standalone below.

## What it does

- **`analyze`** - summarize a local repo: languages, dependency manifests, layout.
- **`triage`** - pull open issues via the GitHub CLI and rank the best first-issue candidates.
- **`report`** - a markdown engineering report (health checklist + languages + optional triage
  + a short model-written assessment).
- **`plan`** - draft a PR implementation plan for one issue: the handoff artifact for `/github-pr`.

Triage/report/plan reuse the authenticated `gh` CLI for GitHub data and the free Personal LLM
router (Gemini free tier or local Ollama) only for the prose. No new API keys.

## Setup

```powershell
cd C:\Users\Asus\projects\ai-ecosystem\github-pr-agent
py -3.12 -m venv venv
& "venv\Scripts\python" -m pip install -r requirements.txt

# Personal LLM core (for the prose commentary). Its runtime deps live in its requirements.txt.
& "venv\Scripts\python" -m pip install -r ..\personal-llm\requirements.txt
& "venv\Scripts\python" -m pip install -e ..\personal-llm
& "venv\Scripts\python" -m pip install -e .

# The `gh` CLI must be installed and authenticated for triage/plan:
gh auth status
```

## Use

```powershell
# Analyze any local repo
& "venv\Scripts\python" -m autocto.interfaces.cli analyze ..\second-brain

# Triage issues on any GitHub repo (best first-issue candidates first)
& "venv\Scripts\python" -m autocto.interfaces.cli triage syzayd/second-brain --label "good first issue"

# Full engineering report (local analysis + remote triage)
& "venv\Scripts\python" -m autocto.interfaces.cli report ..\second-brain --repo syzayd/second-brain --out data\report.md

# Draft a PR plan for one issue, then hand it to /github-pr to implement
& "venv\Scripts\python" -m autocto.interfaces.cli plan syzayd/second-brain 12 --path ..\second-brain --out data\pr-plan.md
```

## How it pairs with the skill

AutoCTO produces the plan; the `/github-pr` skill executes it. You can run either alone:
`/github-pr` can find and fix an issue on its own, and AutoCTO can report/triage without ever
opening a PR. Together, AutoCTO scopes the work and the skill does it.

## Tests

```powershell
& "venv\Scripts\python" -m pytest tests/ -q
```

The logic modules (`repo`, `issues`, `report`, `plan`, `github`) take injected callables and
fake data - no `gh`, network, or model needed - so the suite runs fully offline. Only the CLI
touches `gh` and Personal LLM, and it imports them lazily.

North-star vision: `C:\Users\Asus\Documents\fable 5\github pr.txt`.
