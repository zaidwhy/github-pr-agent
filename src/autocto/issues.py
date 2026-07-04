"""Issue triage: parse `gh issue list --json ...` output and rank good-first-issue candidates.

Ranking is a deterministic heuristic with no LLM or Personal LLM import, so it is fully
testable. The CLI can pass the top results through the model for a nicer explanation, but the
ranking stands on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GOOD_FIRST_LABELS = {
    "good first issue", "good-first-issue", "good first contribution", "help wanted",
    "help-wanted", "documentation", "docs", "beginner", "easy", "low-hanging-fruit",
}


@dataclass
class Issue:
    number: int
    title: str
    url: str = ""
    labels: list[str] = field(default_factory=list)
    body: str = ""
    comments: int = 0


def parse_issues(gh_json: list[dict]) -> list[Issue]:
    """Parse the JSON array from `gh issue list --json number,title,url,labels,body,comments`."""
    issues: list[Issue] = []
    for item in gh_json:
        labels = [lab.get("name", "") for lab in (item.get("labels") or []) if isinstance(lab, dict)]
        comments = item.get("comments")
        comment_count = comments if isinstance(comments, int) else len(comments or [])
        issues.append(
            Issue(
                number=int(item.get("number", 0)),
                title=item.get("title", "") or "",
                url=item.get("url", "") or "",
                labels=labels,
                body=item.get("body", "") or "",
                comments=comment_count,
            )
        )
    return issues


def suitability_score(issue: Issue) -> float:
    """Higher = better first-issue candidate. Rewards clear scope and a beginner label."""
    score = 0.0
    lowered = {lab.lower() for lab in issue.labels}
    if lowered & GOOD_FIRST_LABELS:
        score += 3.0
    if issue.title.strip():
        score += 0.5
    body_len = len(issue.body.strip())
    if 0 < body_len <= 1500:
        score += 1.0  # crisp, self-contained
    elif body_len > 4000:
        score -= 0.5  # sprawling, likely complex
    if issue.comments <= 3:
        score += 0.5  # less contested / less likely already in progress
    return score


def rank_issues(issues: list[Issue]) -> list[tuple[Issue, float]]:
    """Issues sorted best-first (score desc, then issue number asc for stable ties)."""
    scored = [(issue, suitability_score(issue)) for issue in issues]
    scored.sort(key=lambda pair: (-pair[1], pair[0].number))
    return scored
