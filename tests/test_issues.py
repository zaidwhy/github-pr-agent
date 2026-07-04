"""Issue parsing and good-first-issue ranking heuristics."""

from __future__ import annotations

from autocto.issues import Issue, parse_issues, rank_issues, suitability_score


def test_parse_issues_from_gh_json():
    gh = [
        {
            "number": 12,
            "title": "Fix typo in README",
            "url": "https://github.com/o/r/issues/12",
            "labels": [{"name": "good first issue"}, {"name": "docs"}],
            "body": "small fix",
            "comments": 1,
        }
    ]
    issues = parse_issues(gh)
    assert issues[0].number == 12
    assert issues[0].labels == ["good first issue", "docs"]
    assert issues[0].comments == 1


def test_good_first_label_boosts_score():
    good = Issue(number=1, title="Add docs", labels=["good first issue"], body="short", comments=0)
    plain = Issue(number=2, title="Add docs", labels=["enhancement"], body="short", comments=0)
    assert suitability_score(good) > suitability_score(plain)


def test_long_body_penalized():
    short = Issue(number=1, title="t", body="a" * 500)
    huge = Issue(number=2, title="t", body="a" * 5000)
    assert suitability_score(short) > suitability_score(huge)


def test_rank_orders_best_first():
    issues = [
        Issue(number=1, title="complex", labels=["enhancement"], body="a" * 5000, comments=20),
        Issue(number=2, title="easy", labels=["good first issue"], body="short", comments=0),
    ]
    ranked = rank_issues(issues)
    assert ranked[0][0].number == 2  # the good-first, crisp one wins
