"""gh wrapper: every failure mode surfaces as GhError, never a raw traceback.

No real network calls: subprocess is monkeypatched.
"""

from __future__ import annotations

import subprocess

import pytest

from github_pr_agent import github


def _ok(stdout: str):
    """Fake a successful `gh` run returning the given stdout."""
    return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=stdout, stderr="")


def _have_gh(monkeypatch):
    monkeypatch.setattr(github.shutil, "which", lambda _name: "/usr/bin/gh")


def test_ghnotavailable_is_a_gherror():
    # The CLI catches GhError; GhNotAvailable must be caught by that too.
    assert issubclass(github.GhNotAvailable, github.GhError)


def test_fetch_issues_raises_when_gh_missing(monkeypatch):
    monkeypatch.setattr(github.shutil, "which", lambda _name: None)
    assert github.gh_available() is False
    with pytest.raises(github.GhNotAvailable):
        github.fetch_issues("owner/repo")


def test_bad_repo_string_rejected_before_shelling_out(monkeypatch):
    # No slash -> rejected up front, so gh is never invoked (which is not even patched here).
    with pytest.raises(github.GhError):
        github.fetch_issues("not-a-repo")


def test_non_positive_limit_rejected(monkeypatch):
    _have_gh(monkeypatch)
    with pytest.raises(github.GhError):
        github.fetch_issues("owner/repo", limit=0)


def test_nonzero_exit_becomes_gherror_with_detail(monkeypatch):
    _have_gh(monkeypatch)

    def fake_run(*_a, **_k):
        return subprocess.CompletedProcess(
            args=["gh"], returncode=1, stdout="", stderr="could not resolve to a Repository"
        )

    monkeypatch.setattr(github.subprocess, "run", fake_run)
    with pytest.raises(github.GhError) as exc:
        github.fetch_issues("owner/does-not-exist")
    assert "could not resolve" in str(exc.value)


def test_timeout_becomes_gherror(monkeypatch):
    _have_gh(monkeypatch)

    def fake_run(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd=["gh"], timeout=60)

    monkeypatch.setattr(github.subprocess, "run", fake_run)
    with pytest.raises(github.GhError):
        github.fetch_issues("owner/repo")


def test_malformed_json_becomes_gherror(monkeypatch):
    _have_gh(monkeypatch)
    monkeypatch.setattr(github.subprocess, "run", lambda *a, **k: _ok("this is not json"))
    with pytest.raises(github.GhError):
        github.fetch_issues("owner/repo")


def test_non_array_json_becomes_gherror(monkeypatch):
    _have_gh(monkeypatch)
    monkeypatch.setattr(github.subprocess, "run", lambda *a, **k: _ok('{"unexpected": true}'))
    with pytest.raises(github.GhError):
        github.fetch_issues("owner/repo")


def test_empty_output_is_empty_list(monkeypatch):
    _have_gh(monkeypatch)
    monkeypatch.setattr(github.subprocess, "run", lambda *a, **k: _ok(""))
    assert github.fetch_issues("owner/repo") == []


def test_happy_path_returns_parsed_list(monkeypatch):
    _have_gh(monkeypatch)
    monkeypatch.setattr(
        github.subprocess, "run", lambda *a, **k: _ok('[{"number": 1, "title": "x"}]')
    )
    out = github.fetch_issues("owner/repo")
    assert out == [{"number": 1, "title": "x"}]


@pytest.mark.parametrize("repo", ["a/b/c", "owner/", "/name", "owner/../x", "own er/name", "owner/name?x=1"])
@pytest.mark.parametrize(
    "call",
    [
        lambda r: github.fetch_issues(r),
        lambda r: github.fetch_issue_timeline(r, 1),
        lambda r: github.fetch_latest_comment_body(r, 1),
    ],
    ids=["issues", "timeline", "comment"],
)
def test_malformed_repo_rejected_before_shelling_out(monkeypatch, repo, call):
    # The timeline call builds a `gh api repos/{repo}/...` path, so a stray slash or ".."
    # would reach a different endpoint; every fetcher rejects it before gh runs.
    _have_gh(monkeypatch)

    def never(*_a, **_k):
        raise AssertionError("gh must not be invoked for a malformed repo")

    monkeypatch.setattr(github.subprocess, "run", never)
    with pytest.raises(github.GhError, match="owner/name"):
        call(repo)


def test_dotted_and_dashed_names_are_accepted(monkeypatch):
    _have_gh(monkeypatch)
    monkeypatch.setattr(github.subprocess, "run", lambda *_a, **_k: _ok("[]"))
    assert github.fetch_issues("my-org/repo.name_2") == []
