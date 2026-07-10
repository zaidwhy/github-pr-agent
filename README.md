# GitHub PR Agent - AutoCTO

[![CI](https://github.com/syzayd/github-pr-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/syzayd/github-pr-agent/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-32%20passed%20offline-brightgreen)
![Python](https://img.shields.io/badge/python-3.12-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**The AI Staff Engineer every repository deserves.** Project #3 in a larger local-first
AI ecosystem built on the [Personal LLM](https://github.com/syzayd/personal-llm) core.

This repo is the **engineering-manager layer**: it understands a repository, reports on its
health, triages its issues, and drafts a pull-request plan. It deliberately does **not** write
the code. On the free/local model the ecosystem uses, analysis and planning are reliable while
code generation is not - so implementation is handed to the **`/github-pr` Claude Code skill**,
which does the real PR work (write the fix, run tests, open the PR after your approval).

Its pattern is proven: the manager layer triaged a real issue, the implementer skill
wrote the fix, and the resulting PR ([#2](https://github.com/syzayd/github-pr-agent/pull/2),
a hardening pass with the full 32-test suite) was reviewed and merged.

## What it does

- **`analyze`** - summarize a local repo: languages, dependency manifests, layout.
- **`triage`** - pull open issues via the GitHub CLI and rank the best first-issue candidates.
- **`report`** - a markdown engineering report (health checklist + languages + optional triage
  + a short model-written assessment).
- **`plan`** - draft a PR implementation plan for one issue: the handoff artifact for `/github-pr`.

Triage/report/plan reuse the authenticated `gh` CLI for GitHub data and the free Personal LLM
router (Gemini free tier or local Ollama) only for the prose. No new API keys.

## Setup (under 5 minutes)

Clone this repo and the core side by side, then install both:

```powershell
git clone https://github.com/syzayd/personal-llm
git clone https://github.com/syzayd/github-pr-agent
cd github-pr-agent
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

32 tests. The logic modules (`repo`, `issues`, `report`, `plan`, `github`) take injected
callables and fake data - no `gh`, network, or model needed - so the suite runs fully
offline (CI runs it keyless on every push). Only the CLI touches `gh` and Personal LLM,
and it imports them lazily. Hardened invariants: every `gh` failure becomes a readable
`GhError` (exit 1, no traceback), the LLM degrades to a stub if the core is missing, and
repo scanning is deterministic.

## Demo

<!-- TODO(zaid): record a real 30-second GIF - `triage` a known repo, then `plan` one
issue and show the generated pr-plan.md. Never fabricate. -->
Demo GIF coming soon. Until then, `analyze` on any local repo runs offline with zero setup
beyond the Quickstart.

## Contributing

Small, focused PRs welcome - the one hard rule is that tests stay offline and keyless
(logic modules inject their dependencies; `gh` and `personal_llm` imports stay lazy in
the CLI only).

## License

[MIT](LICENSE).
