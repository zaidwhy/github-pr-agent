"""PR plan: draft a markdown implementation plan for one issue - the handoff to the skill.

`llm(prompt) -> str` is injected. The output lists the proposed approach plus a checklist the
`/github-pr` skill (Claude Code) executes to actually write and open the PR.
"""

from __future__ import annotations

import re
from typing import Callable

from github_pr_agent.issues import Issue
from github_pr_agent.repo import RepoAnalysis

LlmFn = Callable[[str], str]


_MAX_PROMPT_FILES = 60
_WORD = re.compile(r"[a-z][a-z0-9]{2,}")
# A token that looks like a path: has a slash, or ends in a file extension.
_PATHLIKE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]*|[\w-]+(?:\.[\w-]+)*\.(?:py|pyi|js|jsx|ts|tsx|go|rs|java|rb|c|h|cpp|cc|cs|php|swift|kt|sh|sql|md|rst|txt|toml|cfg|ini|ya?ml|json|html|css))(?![\w/])")
# "new file: x", "a new file `x`", "**New File**: `x`": models declare new files in several styles
_NEW_FILE = re.compile(r"new file[\s:*`]*([^\s`*]+)", re.IGNORECASE)


def _words(text: str) -> set[str]:
    # split snake_case and camelCase so "retry_state" and "RetryState" both give "retry" and "state"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).replace("_", " ")
    return set(_WORD.findall(text.lower()))


def _relevant_files(issue: Issue, files: list[str], k: int = _MAX_PROMPT_FILES) -> list[str]:
    """The checkout's paths ranked by word overlap with the issue, then shallow code files to fill."""
    wanted = _words(f"{issue.title} {issue.body}")
    scored = [(len(wanted & _words(f)), f) for f in files]
    ranked = [f for s, f in sorted(scored, key=lambda x: (-x[0], x[1])) if s > 0]
    rest = sorted((f for s, f in scored if s == 0), key=lambda f: (f.count("/"), f))
    return (ranked + rest)[:k]


def _plan_prompt(issue: Issue, analysis: RepoAnalysis) -> str:
    files = _relevant_files(issue, analysis.files)
    listing = "\n".join(f"- {f}" for f in files) or "(no file listing available)"
    return (
        "You are a staff engineer planning a pull request for the issue below. Propose a "
        "concrete implementation approach: which files change, the steps to take, and how to "
        "test it. Do not write the full code; keep it a plan, 4-8 bullet points.\n"
        "Name only files from the list below. If the change needs a file that does not exist "
        "yet, write it as `new file: <path>`. Never guess any other path.\n\n"
        f"Repo primary language: {analysis.primary_language}\n"
        f"Top-level dirs: {analysis.top_level_dirs}\n"
        f"Files in the checkout (most relevant first, {len(files)} of {len(analysis.files)}):\n{listing}\n\n"
        f"Issue #{issue.number}: {issue.title}\n"
        f"Labels: {', '.join(issue.labels) or 'none'}\n"
        f"Body:\n{issue.body[:2000]}\n"
    )


def _unknown_paths(approach: str, files: list[str]) -> list[str]:
    """Path-like tokens in the plan that are neither a file, a directory of the checkout, nor a declared new file.

    A bare name that matches several files is returned with its candidates, e.g. "retry.py (2 files: ...)".
    """
    known = set(files)
    # a bare file name counts when it names exactly one file in the checkout ("retry.py" for tenacity/retry.py)
    base_counts: dict[str, int] = {}
    for f in files:
        name = f.rsplit("/", 1)[-1]
        base_counts[name] = base_counts.get(name, 0) + 1
    dirs = {"/".join(f.split("/")[:i]) for f in files for i in range(1, f.count("/") + 1)}
    declared = {m.group(1).strip(".,;:").lstrip("./") for m in _NEW_FILE.finditer(approach)}
    out = []
    for m in _PATHLIKE.finditer(approach.replace("\\", "/")):
        p = m.group(1).strip(".,;:").lstrip("./")
        if p.startswith(("http:", "https:", "www.")) or "://" in approach[max(0, m.start() - 8):m.start() + 3]:
            continue
        bare_ok = "/" not in p and base_counts.get(p) == 1
        if not p or p in known or bare_ok or p.rstrip("/") in dirs or p in declared or any(o.split(" ")[0] == p for o in out):
            continue
        n = base_counts.get(p, 0) if "/" not in p else 0
        if n > 1:
            matches = sorted(f for f in files if f.rsplit("/", 1)[-1] == p)
            out.append(f"{p} (ambiguous, {n} files: {', '.join(matches[:4])})")
        else:
            out.append(p)
    return out


def _path_bullet(entry: str) -> str:
    """'retry.py (ambiguous, ...)' -> '- `retry.py` (ambiguous, ...)'; a plain path is just code-formatted."""
    path, _, note = entry.partition(" ")
    return f"- `{path}`" + (f" {note}" if note else "")


def _credit_prior_discussion_block() -> str:
    return (
        "## Prior discussion\n"
        "Someone has already commented interest in this issue without opening a PR "
        "(e.g. \"I'd like to work on this\"). Credit that comment in the PR description - "
        "link it or @-mention its author - instead of silently duplicating the conversation."
    )


def build_pr_plan(issue: Issue, analysis: RepoAnalysis, llm: LlmFn) -> str:
    approach = llm(_plan_prompt(issue, analysis)).strip()
    lines = [
        f"# PR plan: #{issue.number} {issue.title}",
        "",
        f"- Repo: {analysis.root} (primary language: {analysis.primary_language or 'unknown'})",
        f"- Issue: {issue.url}",
        f"- Labels: {', '.join(issue.labels) or 'none'}",
        "",
    ]
    if issue.soft_claim:
        lines += [_credit_prior_discussion_block(), ""]
    lines += ["## Proposed approach", approach, ""]
    unknown = _unknown_paths(approach, analysis.files) if analysis.files else []
    if unknown:
        lines += [
            "## Paths to check",
            "The approach names paths that are not in the checkout (or match several files) and were not "
            "declared as new files. Check them before editing:",
            *[_path_bullet(p) for p in unknown],
            "",
        ]
    lines += [
        "## Handoff checklist (for /github-pr)",
        "- [ ] Reproduce or confirm the issue",
        "- [ ] Make the change on a new branch",
        "- [ ] Add or update tests",
        "- [ ] Run the test suite until green",
        "- [ ] Open the PR after approval",
    ]
    return "\n".join(lines)
