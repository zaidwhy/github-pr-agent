"""PR plan: draft a markdown implementation plan for one issue - the handoff to the skill.

`llm(prompt) -> str` is injected. The output lists the proposed approach plus a checklist the
`/github-pr` skill (Claude Code) executes to actually write and open the PR.
"""

from __future__ import annotations

from typing import Callable

from autocto.issues import Issue
from autocto.repo import RepoAnalysis

LlmFn = Callable[[str], str]


def _plan_prompt(issue: Issue, analysis: RepoAnalysis) -> str:
    return (
        "You are a staff engineer planning a pull request for the issue below. Propose a "
        "concrete implementation approach: which parts of the codebase likely change, the steps "
        "to take, and how to test it. Do not write the full code and do not invent file paths "
        "you cannot infer; keep it a plan, 4-8 bullet points.\n\n"
        f"Repo primary language: {analysis.primary_language}\n"
        f"Top-level dirs: {analysis.top_level_dirs}\n"
        f"Issue #{issue.number}: {issue.title}\n"
        f"Labels: {', '.join(issue.labels) or 'none'}\n"
        f"Body:\n{issue.body[:2000]}\n"
    )


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
    lines += [
        "## Proposed approach",
        approach,
        "",
        "## Handoff checklist (for /github-pr)",
        "- [ ] Reproduce or confirm the issue",
        "- [ ] Make the change on a new branch",
        "- [ ] Add or update tests",
        "- [ ] Run the test suite until green",
        "- [ ] Open the PR after approval",
    ]
    return "\n".join(lines)
