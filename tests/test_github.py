"""gh wrapper: the not-installed guard (no real network calls in tests)."""

from __future__ import annotations

import pytest

from autocto import github


def test_fetch_issues_raises_when_gh_missing(monkeypatch):
    monkeypatch.setattr(github.shutil, "which", lambda _name: None)
    assert github.gh_available() is False
    with pytest.raises(github.GhNotAvailable):
        github.fetch_issues("owner/repo")
