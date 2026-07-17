"""Report assembly: structure, health flags, and injected LLM commentary."""

from __future__ import annotations

from autocto.issues import Issue
from autocto.repo import RepoAnalysis
from autocto.report import benchmark_score, build_report, health_flags


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


def test_benchmark_score_strong_signal():
    scores = benchmark_score(_analysis())
    assert scores["Documentation (README)"] == 25
    assert scores["Dependency clarity"] == 25
    assert scores["Test signal"] == 25
    assert scores["License"] == 0  # fixture has no LICENSE in key_files
    assert scores["Total"] == 75


def test_benchmark_score_weak_signal():
    scores = benchmark_score(_analysis(key_files=[], dep_files=[], top_level_dirs=["src"]))
    assert scores["Documentation (README)"] == 0
    assert scores["License"] == 0
    assert scores["Dependency clarity"] == 0
    assert scores["Test signal"] == 0
    assert scores["Total"] == 0


def test_benchmark_score_total_is_sum_of_sub_scores_and_bounded():
    for kw in (
        {},
        dict(key_files=[], dep_files=[], top_level_dirs=["src"]),
        dict(key_files=["README.md", "LICENSE"], top_level_dirs=["test"]),
    ):
        scores = benchmark_score(_analysis(**kw))
        sub_scores = [v for k, v in scores.items() if k != "Total"]
        assert scores["Total"] == sum(sub_scores)
        assert 0 <= scores["Total"] <= 100


def test_build_report_includes_benchmark_section():
    md = build_report(_analysis())
    assert "## Benchmark" in md
    assert "Documentation (README): 25/25" in md
    assert "License: 0/25" in md
    assert "**Total: 75/100**" in md
    # Benchmark comes after the Health checklist, as the quantified version of it.
    assert md.index("## Health checklist") < md.index("## Benchmark")
