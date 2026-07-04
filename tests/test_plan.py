"""PR plan handoff: header, injected approach, and the skill checklist."""

from __future__ import annotations

from autocto.issues import Issue
from autocto.plan import build_pr_plan
from autocto.repo import RepoAnalysis


def test_build_pr_plan():
    issue = Issue(number=7, title="Add retry to client", url="https://x/7", labels=["bug"], body="It fails once.")
    analysis = RepoAnalysis(root="/tmp/repo", languages={"Python": 5}, top_level_dirs=["src", "tests"])
    captured = {}

    def llm(prompt):
        captured["prompt"] = prompt
        return "1. Add a retry wrapper.\n2. Test it."

    md = build_pr_plan(issue, analysis, llm)
    assert "# PR plan: #7 Add retry to client" in md
    assert "Add a retry wrapper" in md
    assert "## Handoff checklist (for /github-pr)" in md
    assert "Open the PR after approval" in md
    # The prompt should carry issue context to the model.
    assert "Add retry to client" in captured["prompt"]
