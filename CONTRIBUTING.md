# Contributing

Thanks for looking at AutoCTO (GitHub PR Agent). It is a personal project, but issues
and small, focused PRs are welcome.

## Ground rules

1. **Tests stay offline and keyless.** The logic modules (`repo`, `issues`, `report`,
   `plan`, `github`) take injected callables and fake data - no `gh`, network, or model
   needed. Keep it that way, and inject fakes in tests rather than adding a real
   dependency or a network call. A PR that adds a networked or model-backed test will
   be asked to mock it.
2. **`gh` and `personal_llm` imports stay lazy.** Only import them inside the CLI
   command bodies (`src/autocto/interfaces/`), never at module top level elsewhere -
   that is what keeps the core test suite fast and dependency-light.
3. **Every `gh` failure becomes a readable `GhError`** (exit 1, no traceback). Keep new
   `gh` call sites consistent with that contract.
4. **This project plans, it does not implement.** AutoCTO reports, triages, and drafts
   PR plans; it must never write code or open PRs itself - that belongs to the
   `/github-pr` Claude Code skill. Keep that scope boundary in mind for new features.
5. **One concern per PR.** Small and surgical beats broad and clever.

## Dev setup

Follow the Quickstart in [README.md](README.md) (Python 3.12, plus the sibling
`personal-llm` core installed alongside it), then:

```powershell
& "venv\Scripts\python" -m pytest tests/ -q
```

All tests should pass before and after your change. CI runs the same command on every
push and PR.

## Design context

`plan.md` in this repo has the original design notes. If your change alters scope or
direction, update it in the same PR.
