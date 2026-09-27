"""Issue triage: parse `gh issue list --json ...` output and rank good-first-issue candidates.

Ranking is a deterministic heuristic with no LLM or Personal LLM import, so it is fully
testable. The CLI can pass the top results through the model for a nicer explanation, but the
ranking stands on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

GOOD_FIRST_LABELS = {
    "good first issue", "good-first-issue", "good first contribution", "help wanted",
    "help-wanted", "documentation", "docs", "beginner", "easy", "low-hanging-fruit",
}

# Phrases a contributor uses to softly claim an issue without opening a PR. An issue whose
# latest comment matches one of these is de-ranked (someone is mid-conversation) but not
# excluded - a soft claim with no PR after a while is still fair game. Learned the hard way
# on the AutoCTO sprint: half the "unclaimed" issues on hot repos are already covered.
SOFT_CLAIM_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bi('?d| would| will| can| want to| would like to| am going to| plan to)\b.*\bwork(ing)? on\b",
        r"\b(can|may|could) i (work on|take|pick up|be assigned)\b",
        r"\b(assign|working on) (this|it|me)\b",
        r"\bi'?ll (take|handle|do) (this|it)\b",
        r"\bi'?m (on|taking) (this|it)\b",
    )
]


def is_soft_claim(text: str) -> bool:
    """True if a comment reads as 'I'd like to work on this' with no linked PR."""
    if not text:
        return False
    return any(p.search(text) for p in SOFT_CLAIM_PATTERNS)


def open_linked_pr_numbers(timeline_json: list[dict]) -> list[int]:
    """Open PR numbers cross-referenced from an issue's timeline (`gh api .../timeline`).

    A `cross-referenced` event whose source is a PR (`source.issue.pull_request` present)
    and still OPEN means the issue is already being worked - the swarm-avoidance signal.
    """
    numbers: list[int] = []
    for event in timeline_json or []:
        if event.get("event") != "cross-referenced":
            continue
        source_issue = (event.get("source") or {}).get("issue") or {}
        if source_issue.get("pull_request") and source_issue.get("state") == "open":
            num = source_issue.get("number")
            if isinstance(num, int) and num not in numbers:
                numbers.append(num)
    return numbers


@dataclass
class Issue:
    number: int
    title: str
    url: str = ""
    labels: list[str] = field(default_factory=list)
    body: str = ""
    comments: int = 0
    # Enrichment set by enrich_claims() from timeline/comment data (default: unknown-clean).
    open_linked_prs: list[int] = field(default_factory=list)
    soft_claim: bool = False

    @property
    def has_open_linked_pr(self) -> bool:
        return bool(self.open_linked_prs)


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


def enrich_claims(
    issues: list[Issue],
    linked_prs: dict[int, list[int]] | None = None,
    latest_comments: dict[int, str] | None = None,
) -> list[Issue]:
    """Set open_linked_prs and soft_claim on each issue from timeline/comment lookups.

    Pure: the CLI does the `gh` calls and passes plain dicts keyed by issue number, so the
    claim logic stays fully offline-testable. Mutates and returns the same issues.
    """
    linked_prs = linked_prs or {}
    latest_comments = latest_comments or {}
    for issue in issues:
        issue.open_linked_prs = list(linked_prs.get(issue.number, []))
        issue.soft_claim = is_soft_claim(latest_comments.get(issue.number, ""))
    return issues


def suitability_score(issue: Issue) -> float:
    """Higher = better first-issue candidate. Rewards clear scope and a beginner label,
    penalizes a soft claim. An open linked PR is handled by filtering in rank_issues, but
    also scores it far below anything clean so it sinks even in --all mode."""
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
    if issue.soft_claim:
        score -= 1.5  # someone is mid-conversation - courteous to rank them below clean picks
    if issue.has_open_linked_pr:
        score -= 10.0  # already covered by an open PR - do not duplicate
    return score


def rank_issues(issues: list[Issue], unclaimed_only: bool = True) -> list[tuple[Issue, float]]:
    """Issues sorted best-first (score desc, then issue number asc for stable ties).

    With unclaimed_only (default), issues already covered by an open cross-referenced PR are
    dropped entirely - the swarm-avoidance filter. Pass unclaimed_only=False to keep them
    (they still sink to the bottom via the score penalty).
    """
    considered = issues if not unclaimed_only else [i for i in issues if not i.has_open_linked_pr]
    scored = [(issue, suitability_score(issue)) for issue in considered]
    scored.sort(key=lambda pair: (-pair[1], pair[0].number))
    return scored
