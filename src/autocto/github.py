"""Thin wrapper over the authenticated `gh` CLI for read-only GitHub data.

No LLM. It shells out to `gh`, which must be installed and authenticated (`gh auth status`).
Kept separate from the ranking logic so tests can feed fake JSON without touching the network.

Every failure mode (missing CLI, bad repo, not authenticated, network error, timeout, unparseable
output) is surfaced as a `GhError` with a readable message, never a raw traceback, so the CLI can
catch one exception type and exit cleanly.
"""

from __future__ import annotations

import json
import shutil
import subprocess


class GhError(RuntimeError):
    """Any failure talking to the `gh` CLI (bad repo, auth, network, timeout, parse)."""


class GhNotAvailable(GhError):
    """Raised when the `gh` CLI is not installed or cannot be executed."""


def gh_available() -> bool:
    return shutil.which("gh") is not None


def fetch_issues(repo: str, label: str | None = None, limit: int = 30, timeout: int = 60) -> list[dict]:
    """Return open issues for `owner/repo` as a list of dicts (gh's JSON output).

    Raises GhNotAvailable if the CLI is missing, or GhError for any other failure.
    """
    if not repo or "/" not in repo:
        raise GhError(f"Expected a repository as 'owner/name', got: {repo!r}")
    if limit < 1:
        raise GhError(f"limit must be a positive integer, got: {limit}")
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

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:  # gh disappeared between the check and the call
        raise GhNotAvailable(
            "The `gh` CLI was not found. Install GitHub CLI and run `gh auth login`."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise GhError(f"`gh` timed out after {timeout}s querying {repo}.") from exc
    except OSError as exc:  # e.g. cannot spawn the process
        raise GhError(f"Could not run `gh` for {repo}: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() or "no error output"
        raise GhError(f"`gh` failed for {repo} (exit {result.returncode}): {detail}")

    try:
        data = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise GhError(f"Could not parse `gh` output for {repo}: {exc}") from exc
    if not isinstance(data, list):
        raise GhError(f"Unexpected `gh` output for {repo}: expected a JSON array of issues.")
    return data
