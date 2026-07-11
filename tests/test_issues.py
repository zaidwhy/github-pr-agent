"""Issue parsing and good-first-issue ranking heuristics."""

from __future__ import annotations

from autocto.issues import (
    Issue,
    enrich_claims,
    is_soft_claim,
    open_linked_pr_numbers,
    parse_issues,
    rank_issues,
    suitability_score,
)


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


# --- swarm-avoidance: open linked PRs (#61) ---------------------------------------

def test_open_linked_pr_numbers_finds_open_cross_referenced_prs():
    timeline = [
        {"event": "commented"},
        {"event": "cross-referenced", "source": {"issue": {"number": 385, "state": "open",
                                                            "pull_request": {"url": "u"}}}},
        {"event": "cross-referenced", "source": {"issue": {"number": 300, "state": "closed",
                                                            "pull_request": {"url": "u"}}}},
        {"event": "cross-referenced", "source": {"issue": {"number": 128, "state": "open"}}},  # an issue, not a PR
    ]
    assert open_linked_pr_numbers(timeline) == [385]  # open PR only; closed PR and plain issue ignored


def test_open_linked_pr_numbers_handles_empty():
    assert open_linked_pr_numbers([]) == []
    assert open_linked_pr_numbers(None) == []


def test_unclaimed_only_filters_issues_with_open_pr():
    covered = Issue(number=1, title="easy", labels=["good first issue"], body="short", open_linked_prs=[385])
    clean = Issue(number=2, title="easy", labels=["good first issue"], body="short")
    ranked = rank_issues([covered, clean], unclaimed_only=True)
    assert [i.number for i, _ in ranked] == [2]  # the covered one is dropped


def test_all_mode_keeps_covered_issue_but_ranks_it_last():
    covered = Issue(number=1, title="easy", labels=["good first issue"], body="short", open_linked_prs=[385])
    clean = Issue(number=2, title="plain", labels=[], body="short")
    ranked = rank_issues([covered, clean], unclaimed_only=False)
    assert [i.number for i, _ in ranked] == [2, 1]  # covered kept but sinks below a plain clean issue


# --- soft claims (#62) ------------------------------------------------------------

def test_is_soft_claim_matches_intent_phrases():
    assert is_soft_claim("Hi! I'd like to work on this issue.")
    assert is_soft_claim("can I work on this?")
    assert is_soft_claim("I'll take this one")
    assert is_soft_claim("I'm on it")


def test_is_soft_claim_ignores_unrelated_comments():
    assert not is_soft_claim("This also affects the Neo4j builder.")
    assert not is_soft_claim("")
    assert not is_soft_claim("Here is a repro with the stack trace.")


def test_soft_claim_deranks_but_does_not_exclude():
    claimed = Issue(number=1, title="easy", labels=["good first issue"], body="short", soft_claim=True)
    clean = Issue(number=2, title="easy", labels=["good first issue"], body="short")
    ranked = rank_issues([claimed, clean], unclaimed_only=True)
    assert [i.number for i, _ in ranked] == [2, 1]  # clean first, soft-claimed still present


def test_enrich_claims_sets_flags_from_lookups():
    issues = [Issue(number=252, title="t"), Issue(number=253, title="t")]
    enrich_claims(
        issues,
        linked_prs={253: [385]},
        latest_comments={252: "I would like to work on this"},
    )
    by_num = {i.number: i for i in issues}
    assert by_num[252].soft_claim and not by_num[252].has_open_linked_pr
    assert by_num[253].has_open_linked_pr and not by_num[253].soft_claim
