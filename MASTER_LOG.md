# GitHub PR Agent (AutoCTO) - Master Log

Append-only. Newest entries at the bottom. Read just the tail for recent context.

## 2026-07-04 - Project created (v0.1 scaffold)

- Project #3 in the AI ecosystem: the engineering-manager layer of the GitHub PR Agent.
- Decided split (with Zaid): this Python project does analysis + triage + planning on the free
  core router (no new keys); the `/github-pr` Claude Code skill does the actual implementation
  (write fix, run tests, open PR after approval), exactly like the adk-python PR - no API keys.
- v0.1 modules: `repo` (scan a checkout: languages, key/dep files, layout), `issues` (parse gh
  JSON + heuristic good-first-issue ranking), `report` (markdown CTO report: health checklist +
  languages + triage + model assessment), `plan` (draft a PR plan handoff), `github` (gh CLI
  wrapper), and a Typer `cli` (analyze / triage / report / plan) that lazy-imports the core.
- Logic modules inject their dependencies (no personal_llm, no network), so the suite runs
  fully offline and keyless.

## 2026-07-04 - Refinement pass (refine-repo)

- Em dash scan: 0 found across all tracked files.
- Environment: installed the Personal LLM core into the venv (`-r ..\personal-llm\requirements.txt`
  then `-e ..\personal-llm`) so the documented `report`/`plan` path works, not just `analyze`.
  `pip check` clean; `personal_llm 1.0.0` and all `autocto` modules import.
- Tests: 12/12 pass offline.
- Verified end to end: `report ..\second-brain` produced a full markdown report, including a real
  model-written assessment from local Ollama (graceful-degrade path confirmed working when a model
  is reachable). No feature changes - refinement only.

## 2026-07-04 - Deep hardening pass (on branch fix/scan-missing-path, PR #2)

Staff-engineer audit of every module, then repair. No new features; every change closes a real
crash path or nondeterminism. Tests went 13 -> 32.

- **github.py (critical):** any `gh` failure used to raise a raw `CalledProcessError` (nonexistent
  repo, not authenticated, no access, rate limit, network down), plus unhandled `TimeoutExpired`
  and `JSONDecodeError`. Rebuilt around a `GhError` base (with `GhNotAvailable` as a subclass):
  validates the `owner/name` form and limit up front, drops `check=True` to inspect the return
  code and surface stderr, and wraps timeout / spawn / parse / non-array failures. Every failure is
  now a readable `GhError`.
- **cli.py (critical):** `_llm()` imported `personal_llm` outside any guard, so a clone without the
  core installed crashed `report`/`plan`. It now degrades to a stub that reports the reason and
  never raises. All three gh-backed commands catch the broad `GhError` (was only `GhNotAvailable`);
  `report --repo` downgrades a fetch failure to a warning and still writes the local report.
- **repo.py (medium):** `primary_language` was nondeterministic on ties (max over a
  filesystem-ordered dict) - now alphabetical and stable. Rewrote the walk with `os.walk` that
  prunes ignored dirs in place (never descends into `.git` / `node_modules` / `venv`, faster on big
  repos) and uses `onerror` so a locked subtree is skipped, not fatal.
- **Tests:** new `test_cli.py` (Typer `CliRunner`: exit codes + no leaked tracebacks on every error
  path), full gh-failure matrix in `test_github.py`, determinism + nested-prune cases in
  `test_repo.py`. 32/32 pass offline.
- **Live-verified:** `triage` on a missing repo and a malformed repo string, `report --repo` on a
  missing repo (warn + still write), and `analyze .` (venv/.git pruned) - all clean, correct codes.
