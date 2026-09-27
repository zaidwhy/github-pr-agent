"""PR plan handoff: header, injected approach, and the skill checklist."""

from __future__ import annotations

from github_pr_agent.issues import Issue
from github_pr_agent.plan import build_pr_plan
from github_pr_agent.repo import RepoAnalysis


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


# --- grounding: the plan may only name files that exist (tenacity#534 once got invented paths) ---

def _tenacity_like() -> RepoAnalysis:
    return RepoAnalysis(
        root="/tmp/tenacity",
        languages={"Python": 4},
        top_level_dirs=["doc", "tenacity", "tests"],
        files=[
            "tenacity/__init__.py", "tenacity/retry.py", "tenacity/stop.py",
            "tests/test_tenacity.py", "doc/source/index.rst", "pyproject.toml",
        ],
    )


def test_prompt_lists_real_files_ranked_by_the_issue():
    issue = Issue(number=534, title="Incorrect exception raised with two retrying blocks", url="u", labels=[],
                  body="The retry state leaks between two Retrying blocks in tenacity.")
    captured = {}
    build_pr_plan(issue, _tenacity_like(), lambda p: captured.setdefault("prompt", p) and "1. Fix it.")
    prompt = captured["prompt"]
    assert "tenacity/retry.py" in prompt and "tests/test_tenacity.py" in prompt
    assert prompt.index("tenacity/retry.py") < prompt.index("doc/source/index.rst")
    assert "new file:" in prompt


def test_invented_paths_are_flagged():
    issue = Issue(number=534, title="t", url="u", labels=[], body="b")
    md = build_pr_plan(issue, _tenacity_like(), lambda p: "1. Edit `tenacity/strategy.py`.\n2. Document in doc/issue-534.md.")
    assert "## Paths to check" in md
    assert "tenacity/strategy.py" in md.split("## Paths to check")[1]
    assert "doc/issue-534.md" in md.split("## Paths to check")[1]


def test_real_and_declared_new_paths_are_not_flagged():
    issue = Issue(number=534, title="t", url="u", labels=[], body="b")
    approach = "1. Change `tenacity/retry.py` and tests/test_tenacity.py.\n2. new file: tests/test_nested.py\n3. Touch the tests/ folder."
    md = build_pr_plan(issue, _tenacity_like(), lambda p: approach)
    assert "## Paths to check" not in md


def test_bare_names_of_real_files_and_other_new_file_phrasings_are_not_flagged():
    # from the live tenacity#534 run: models name files by basename and declare new files in several styles
    issue = Issue(number=534, title="t", url="u", labels=[], body="b")
    approach = (
        "1. Update `retry.py` and run test_tenacity.py.\n"
        "2. Create a new file `tests/test_issue_534.py`.\n"
        "3. **New File**: `tenacity/nested.py`\n"
    )
    md = build_pr_plan(issue, _tenacity_like(), lambda p: approach)
    assert "## Paths to check" not in md


def test_a_basename_shared_by_two_files_is_not_enough_to_ground_a_wrong_directory():
    issue = Issue(number=1, title="t", url="u", labels=[], body="b")
    md = build_pr_plan(issue, _tenacity_like(), lambda p: "1. Edit `src/retry.py`.")
    assert "src/retry.py" in md.split("## Paths to check")[1]


def test_an_ambiguous_bare_name_lists_its_candidates():
    analysis = _tenacity_like()
    analysis.files.append("tenacity/asyncio/retry.py")
    md = build_pr_plan(Issue(number=1, title="t", url="u", labels=[], body="b"), analysis, lambda p: "1. Edit `retry.py`.")
    section = md.split("## Paths to check")[1]
    assert "`retry.py` (ambiguous, 2 files: tenacity/asyncio/retry.py, tenacity/retry.py)" in section
