"""Engineering report: turn a RepoAnalysis (+ ranked issues) into a markdown CTO report.

LLM commentary is injected as `llm(prompt) -> str`, so this module has no Personal LLM import
and tests pass a stub. The structural parts (tables, health flags) need no model at all.
"""

from __future__ import annotations

from typing import Callable

from autocto.issues import Issue
from autocto.repo import RepoAnalysis

LlmFn = Callable[[str], str]


def health_flags(analysis: RepoAnalysis) -> list[str]:
    """Cheap, model-free health signals from what the scan found."""
    key = {k.lower() for k in analysis.key_files}
    dirs = {d.lower() for d in analysis.top_level_dirs}
    flags = []
    flags.append("Has a README" if any("readme" in k for k in key) else "MISSING a README")
    flags.append("Has a LICENSE" if any("license" in k for k in key) else "No LICENSE file")
    flags.append(
        "Declares dependencies" if analysis.dep_files else "No dependency manifest found"
    )
    flags.append(
        "Has a tests directory" if ("tests" in dirs or "test" in dirs) else "No obvious tests directory"
    )
    return flags


def _languages_table(analysis: RepoAnalysis) -> str:
    if not analysis.languages:
        return "_No recognized source files._"
    rows = sorted(analysis.languages.items(), key=lambda kv: kv[1], reverse=True)
    lines = ["| Language | Files |", "|---|---|"]
    lines += [f"| {lang} | {count} |" for lang, count in rows]
    return "\n".join(lines)


def _assessment_prompt(analysis: RepoAnalysis) -> str:
    return (
        "You are a staff engineer reviewing a repository. Given this summary, write 3-5 short "
        "bullet points on likely strengths, risks, and the highest-value next improvement. Be "
        "concrete and do not invent details you were not given.\n\n"
        f"Primary language: {analysis.primary_language}\n"
        f"Languages: {analysis.languages}\n"
        f"Dependency files: {analysis.dep_files}\n"
        f"Docs/meta files: {analysis.key_files}\n"
        f"Top-level dirs: {analysis.top_level_dirs}\n"
        f"Total source files: {analysis.total_files}\n"
    )


def build_report(
    analysis: RepoAnalysis,
    ranked_issues: list[tuple[Issue, float]] | None = None,
    llm: LlmFn | None = None,
) -> str:
    ranked_issues = ranked_issues or []
    parts = [
        f"# Engineering report: {analysis.root}",
        "",
        f"- Primary language: **{analysis.primary_language or 'unknown'}**",
        f"- Source files scanned: {analysis.total_files}",
        f"- Dependency manifests: {', '.join(analysis.dep_files) or 'none found'}",
        f"- Docs/meta: {', '.join(analysis.key_files) or 'none found'}",
        f"- Top-level layout: {', '.join(analysis.top_level_dirs) or '(flat)'}",
        "",
        "## Languages",
        _languages_table(analysis),
        "",
        "## Health checklist",
        *[f"- {flag}" for flag in health_flags(analysis)],
        "",
    ]
    if ranked_issues:
        parts.append("## Open issues (top candidates)")
        for issue, score in ranked_issues[:10]:
            labels = ", ".join(issue.labels) or "no labels"
            parts.append(f"- [#{issue.number}] {issue.title}  _(score {score:.1f}; {labels})_")
        parts.append("")
    if llm is not None:
        parts.append("## Assessment")
        parts.append(llm(_assessment_prompt(analysis)).strip())
        parts.append("")
    return "\n".join(parts)
