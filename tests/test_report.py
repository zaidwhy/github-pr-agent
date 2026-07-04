"""Report assembly: structure, health flags, and injected LLM commentary."""

from __future__ import annotations

from autocto.issues import Issue
from autocto.repo import RepoAnalysis
from autocto.report import build_report, health_flags


def _analysis(**kw):
    base = dict(
        root="/tmp/repo",
        total_files=10,
        languages={"Python": 8, "Markdown": 2},
        key_files=["README.md"],
        dep_files=["pyproject.toml"],
        top_level_dirs=["src", "tests"],
    )
    base.update(kw)
    return RepoAnalysis(**base)


def test_health_flags_positive():
    flags = health_flags(_analysis())
    joined = " ".join(flags)
    assert "Has a README" in joined and "Has a tests directory" in joined


def test_health_flags_negative():
    flags = health_flags(_analysis(key_files=[], dep_files=[], top_level_dirs=["src"]))
    joined = " ".join(flags)
    assert "MISSING a README" in joined and "No dependency manifest" in joined


def test_build_report_structure_without_llm():
    md = build_report(_analysis())
    assert "# Engineering report" in md
    assert "| Language | Files |" in md
    assert "## Health checklist" in md
    assert "## Assessment" not in md  # no llm -> no assessment section


def test_build_report_with_issues_and_llm():
    ranked = [(Issue(number=5, title="Fix bug", labels=["good first issue"]), 4.0)]
    md = build_report(_analysis(), ranked, llm=lambda prompt: "Looks solid.")
    assert "[#5] Fix bug" in md
    assert "## Assessment" in md and "Looks solid." in md
