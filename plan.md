# GitHub PR Agent (AutoCTO) - Build Plan

> "The AI Staff Engineer Every Repository Deserves." Understands any repo, finds real work, implements it, tests it, and opens production-quality pull requests - like an experienced staff engineer who never sleeps.

## What it is / why it matters

The GitHub PR Agent ships as **two halves that also run alone**:

1. **AutoCTO** (this Python project, package `autocto`) - the engineering-manager layer. It reads a
   codebase, reports on its health, triages open issues, and drafts a PR plan. It never touches a
   PR itself.
2. **The `/github-pr` skill** (Claude Code, keyless) - the implementer. It picks up an issue (or an
   AutoCTO plan), writes the fix on a branch, runs the tests, and opens a real PR after approval.

This split is deliberate: on the free/local model the ecosystem uses, **analysis and planning are
reliable while unattended code generation is not**, so the judgment lives in Python and the
implementation lives in the skill (which runs on Claude Code itself - the same keyless flow as the
adk-python contribution). Either half is useful on its own.

**Resume angle:** the single highest-payoff project on the list. Merged open-source PRs opened
through this pairing are undeniable proof of skill, visible on your GitHub profile, and a perfect
build-in-public narrative. Build this third for exactly that reason.

## Where it sits in the ecosystem

- **Depends on:** Personal LLM (#1) for the agent framework, tool layer, and security.
- **Provides to downstream:** a battle-tested autonomous agent loop and sandboxing that HackMind (#6) and AI Scientist (#7) reuse.

## MVP scope (v0.1) - DONE

**AutoCTO (this project):** four commands over a local checkout + the `gh` CLI, no new keys.

- `analyze` - scan a repo (languages, dependency manifests, layout) from the filesystem alone.
- `triage` - pull open issues via `gh` and rank the best first-issue candidates heuristically.
- `report` - a markdown engineering report: health checklist + languages + triage + a short
  model-written assessment (free router, degrades gracefully when no model is reachable).
- `plan` - draft a PR implementation plan for one issue: the handoff artifact for `/github-pr`.

**`/github-pr` skill:** resolve target (fork/clone if external) to pick issue to plan to
approve-first to implement to green tests to `gh pr create`. Keyless, on-demand.

**Non-goals for v0.1:** autonomous repo discovery across GitHub, the 16-agent org,
DevOps/Kubernetes deployment, the reputation dashboard, multi-cloud, unattended code generation.
Get one clean merged PR through the pairing first.

## Phased roadmap

- **Prototype (S):** repo scan + architecture/dependency summary. **Done** (`analyze`).
- **MVP (M):** triage + report + plan in Python; the skill takes plan to code to passing tests to
  PR on a repo you control. **Done** (v0.1 shipped: 12 tests, CLI live, skill written).
- **v1 (M):** run against a real open-source "good first issue"; add a code-review pass and quality
  gates in the skill before it opens the PR; richer health metrics in the report.
- **Stretch (L):** autonomous repo/issue discovery, scheduled CTO reports, security + performance
  engines, multi-agent specialists, dashboard.

## Tech stack

- **AutoCTO:** Python + Typer CLI + pydantic-settings. Filesystem scan for `analyze`; the
  authenticated `gh` CLI for issue data (no GitHub API keys); the Personal LLM core router (Gemini
  free tier / local Ollama) for prose only, imported lazily so the test suite stays offline.
- **`/github-pr`:** Claude Code itself + `git` + `gh`. No sandbox/API layer needed because the
  skill runs interactively under Zaid's approval rather than as an unattended service.

## First tasks - COMPLETE

1. Repo ingestion: `scan_repo` walks the tree, detects languages, finds key/dep files. Done.
2. Issue data via the `gh` CLI (`fetch_issues`) + heuristic ranking (`rank_issues`). Done.
3. Issue-to-plan step (`build_pr_plan`) that emits a `/github-pr` handoff checklist. Done.
4. The `/github-pr` skill: approve-first implementation, real tests, keyless `gh pr create`. Done.
5. **Next:** run the pairing against a live "good first issue" and land the first real PR.

## Reference

Full north-star vision: `C:\Users\Asus\Documents\fable 5\github pr.txt`.
