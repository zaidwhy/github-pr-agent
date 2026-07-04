"""Thin wrapper over the authenticated `gh` CLI for read-only GitHub data.

No LLM. It shells out to `gh`, which must be installed and authenticated (`gh auth status`).
Kept separate from the ranking logic so tests can feed fake JSON without touching the network.
"""

from __future__ import annotations

import json
import shutil
import subprocess


class GhNotAvailable(RuntimeError):
    """Raised when the `gh` CLI is missing."""


def gh_available() -> bool:
    return shutil.which("gh") is not None


def fetch_issues(repo: str, label: str | None = None, limit: int = 30, timeout: int = 60) -> list[dict]:
    """Return open issues for `owner/repo` as a list of dicts (gh's JSON output)."""
    if not gh_available():
        raise GhNotAvailable(
            "The `gh` CLI was not found. Install GitHub CLI and run `gh auth login`."
        )
    cmd = [
        "gh", "issue", "list", "--repo", repo, "--state", "open",
        "--json", "number,title,url,labels,body,comments", "--limit", str(limit),
    ]
    if label:
        cmd += ["--label", label]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    return json.loads(result.stdout or "[]")
