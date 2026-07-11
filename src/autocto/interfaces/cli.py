"""AutoCTO CLI - analyze, report, triage, and plan.

The engineering-manager layer of the GitHub PR Agent. It understands a repo and drafts a PR
plan, then hands implementation to the `/github-pr` skill. Personal LLM (used only for the
prose commentary) is imported lazily, so the module loads without heavy deps.
"""

from __future__ import annotations

from pathlib import Path

import typer

from autocto.config import get_settings

app = typer.Typer(help="AutoCTO - understand a repo, report on it, triage issues, draft a PR plan.")


def _llm():
    """An llm(prompt)->str backed by the free Personal LLM router (Ollama/Gemini, no new keys).

    Never raises: if the Personal LLM core is not installed or the router cannot be built, it
    returns a stub that reports the reason, so the structural report/plan still gets produced.
    """
    import os

    os.environ.setdefault("OLLAMA_MODEL", get_settings().ollama_model)
    try:
        from personal_llm.router import ModelRouter
        from personal_llm.router.schemas import Message

        router = ModelRouter()
    except Exception as exc:  # core not installed, or the router failed to initialize
        note = f"(model unavailable: {exc})"
        return lambda _prompt: note

    def llm(prompt: str) -> str:
        try:
            return router.complete([Message(role="user", content=prompt)]).text
        except Exception as exc:  # a report is still useful without the prose section
            return f"(model unavailable: {exc})"

    return llm


@app.command()
def analyze(path: Path = typer.Argument(Path("."), help="Local repo path.")) -> None:
    """Summarize a local repository (languages, deps, layout)."""
    from autocto.repo import scan_repo

    try:
        a = scan_repo(path, get_settings().ignore_dirs)
    except OSError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1)
    typer.echo(f"Repo: {a.root}")
    typer.echo(f"Primary language: {a.primary_language or 'unknown'}")
    typer.echo(f"Files: {a.total_files} | deps: {', '.join(a.dep_files) or 'none'}")
    typer.echo(f"Languages: {a.languages}")
    typer.echo(f"Top-level: {', '.join(a.top_level_dirs) or '(flat)'}")


@app.command()
def triage(
    repo: str = typer.Argument(..., help="owner/repo"),
    label: str = typer.Option(None, "--label", help="Filter by a label, e.g. 'good first issue'."),
    limit: int = typer.Option(30, help="Max issues to fetch."),
    unclaimed_only: bool = typer.Option(
        True, "--unclaimed-only/--all",
        help="Drop issues already covered by an open PR (default). --all keeps them (ranked last).",
    ),
    enrich: int = typer.Option(
        12, help="How many top candidates to check for open PRs / soft claims (0 disables).",
    ),
) -> None:
    """List and rank open issues, best first-issue candidates first.

    Claim-aware: the top candidates are checked against their timeline for an already-open
    cross-referenced PR (excluded under --unclaimed-only) and their latest comment for a soft
    claim (de-ranked). This is the swarm-avoidance pass - most "unclaimed" issues on hot repos
    already have a PR in flight.
    """
    from autocto.github import (
        GhError, fetch_issue_timeline, fetch_issues, fetch_latest_comment_body,
    )
    from autocto.issues import (
        enrich_claims, open_linked_pr_numbers, parse_issues, rank_issues,
    )

    try:
        issues = parse_issues(fetch_issues(repo, label=label, limit=limit))
    except GhError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1)
    if not issues:
        typer.echo("No open issues found.")
        return

    # Enrich only the top base-ranked candidates - one timeline + one comment call each -
    # so a 30-issue triage does not fan out into 60 API calls.
    if enrich > 0:
        top = [i for i, _ in rank_issues(issues, unclaimed_only=False)[:enrich]]
        linked: dict[int, list[int]] = {}
        latest: dict[int, str] = {}
        for issue in top:
            try:
                linked[issue.number] = open_linked_pr_numbers(fetch_issue_timeline(repo, issue.number))
                latest[issue.number] = fetch_latest_comment_body(repo, issue.number)
            except GhError:
                pass  # a partial enrichment is still better than none; leave this one clean
        enrich_claims(issues, linked, latest)

    ranked = rank_issues(issues, unclaimed_only=unclaimed_only)
    if not ranked:
        typer.echo("No unclaimed open issues found (all top candidates already have PRs).")
        return
    for issue, score in ranked:
        flags = []
        if issue.has_open_linked_pr:
            flags.append("PR#" + ",".join(str(n) for n in issue.open_linked_prs))
        if issue.soft_claim:
            flags.append("soft-claim")
        tag = f"  [{'; '.join(flags)}]" if flags else ""
        typer.echo(
            f"[{score:5.1f}] #{issue.number} {issue.title}  "
            f"({', '.join(issue.labels) or 'no labels'}){tag}"
        )


@app.command()
def report(
    path: Path = typer.Argument(Path("."), help="Local repo path."),
    repo: str = typer.Option(None, "--repo", help="owner/repo to also pull and triage issues from."),
    out: Path = typer.Option(None, help="Write the report here instead of printing."),
) -> None:
    """Write a markdown engineering report, optionally including issue triage."""
    from autocto.repo import scan_repo
    from autocto.report import build_report

    try:
        analysis = scan_repo(path, get_settings().ignore_dirs)
    except OSError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1)
    ranked = []
    if repo:
        from autocto.github import GhError, fetch_issues
        from autocto.issues import parse_issues, rank_issues

        try:
            ranked = rank_issues(parse_issues(fetch_issues(repo)))
        except GhError as exc:
            # A local report is still worth writing even if the issue fetch failed.
            typer.echo(f"Warning: could not fetch issues: {exc}")
    markdown = build_report(analysis, ranked, llm=_llm())
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        typer.echo(f"Wrote {out}")
    else:
        typer.echo(markdown)


@app.command()
def plan(
    repo: str = typer.Argument(..., help="owner/repo"),
    number: int = typer.Argument(..., help="Issue number to plan a PR for."),
    path: Path = typer.Option(Path("."), help="Local checkout for repo context."),
    out: Path = typer.Option(None, help="Write the plan here instead of printing."),
) -> None:
    """Draft a PR plan for a specific issue - the handoff artifact for /github-pr."""
    from autocto.github import GhError, fetch_issues
    from autocto.issues import parse_issues
    from autocto.plan import build_pr_plan
    from autocto.repo import scan_repo

    try:
        issues = parse_issues(fetch_issues(repo, limit=100))
    except GhError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1)
    match = next((i for i in issues if i.number == number), None)
    if match is None:
        typer.echo(f"Issue #{number} not found among open issues.")
        raise typer.Exit(1)
    try:
        analysis = scan_repo(path, get_settings().ignore_dirs)
    except OSError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(1)
    markdown = build_pr_plan(match, analysis, _llm())
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        typer.echo(f"Wrote {out}")
    else:
        typer.echo(markdown)


if __name__ == "__main__":
    app()
