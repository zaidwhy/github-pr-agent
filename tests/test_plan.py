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
    # No soft claim on this issue - no credit-prior-discussion block.
    assert "## Prior discussion" not in md


def test_build_pr_plan_credits_prior_discussion_on_soft_claim():
    """Snapshot test: PROJECT-GENESIS.md Tier 9 item #65 - when the issue has a soft
    claim (someone said "I'd like to work on this" with no PR yet), the plan must
    template a block telling /github-pr to credit that comment rather than silently
    duplicating it."""
    issue = Issue(
        number=392, title="Flaky retry test", url="https://x/392", labels=["bug"],
        body="Fails intermittently.", soft_claim=True,
    )
    analysis = RepoAnalysis(root="/tmp/repo", languages={"Python": 5}, top_level_dirs=["src", "tests"])

    md = build_pr_plan(issue, analysis, lambda prompt: "1. Fix the race.")

    assert md == (
        "# PR plan: #392 Flaky retry test\n"
        "\n"
        "- Repo: /tmp/repo (primary language: Python)\n"
        "- Issue: https://x/392\n"
        "- Labels: bug\n"
        "\n"
        "## Prior discussion\n"
        "Someone has already commented interest in this issue without opening a PR "
        "(e.g. \"I'd like to work on this\"). Credit that comment in the PR description - "
        "link it or @-mention its author - instead of silently duplicating the conversation.\n"
        "\n"
        "## Proposed approach\n"
        "1. Fix the race.\n"
        "\n"
        "## Handoff checklist (for /github-pr)\n"
        "- [ ] Reproduce or confirm the issue\n"
        "- [ ] Make the change on a new branch\n"
        "- [ ] Add or update tests\n"
        "- [ ] Run the test suite until green\n"
        "- [ ] Open the PR after approval"
    )
