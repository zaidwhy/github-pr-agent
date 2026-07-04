"""End-to-end CLI behavior via Typer's runner: exit codes and clean error messages.

The model and gh are stubbed so these run offline and fast. The point is to prove the
command layer never leaks a raw traceback and always exits with the right code.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from autocto import github
from autocto.interfaces import cli

runner = CliRunner()


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_analyze_good_path(tmp_path):
    _write(tmp_path / "app.py")
    result = runner.invoke(cli.app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0
    assert "Primary language: Python" in result.stdout


def test_analyze_missing_path_exits_1_cleanly(tmp_path):
    result = runner.invoke(cli.app, ["analyze", str(tmp_path / "nope")])
    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Traceback" not in result.stdout  # no raw traceback leaked


def test_triage_gh_error_exits_1_cleanly(monkeypatch):
    def boom(*_a, **_k):
        raise github.GhError("could not resolve to a Repository")

    monkeypatch.setattr(github, "fetch_issues", boom)
    result = runner.invoke(cli.app, ["triage", "owner/nope"])
    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "could not resolve" in result.stdout


def test_report_writes_file_without_touching_the_model(tmp_path, monkeypatch):
    _write(tmp_path / "app.py")
    _write(tmp_path / "README.md")
    monkeypatch.setattr(cli, "_llm", lambda: (lambda _p: "stubbed assessment"))
    out = tmp_path / "report.md"
    result = runner.invoke(cli.app, ["report", str(tmp_path), "--out", str(out)])
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "# Engineering report" in text
    assert "stubbed assessment" in text


def test_report_missing_path_exits_1(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_llm", lambda: (lambda _p: "x"))
    result = runner.invoke(cli.app, ["report", str(tmp_path / "nope")])
    assert result.exit_code == 1
    assert "Error:" in result.stdout


def test_plan_issue_not_found_exits_1(monkeypatch):
    monkeypatch.setattr(github, "fetch_issues", lambda *a, **k: [])  # no issues
    monkeypatch.setattr(cli, "_llm", lambda: (lambda _p: "x"))
    result = runner.invoke(cli.app, ["plan", "owner/repo", "999"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_llm_degrades_when_router_fails(monkeypatch):
    # If the router cannot initialize, _llm must return a stub that reports it, never raise.
    plr = pytest.importorskip("personal_llm.router")

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("no backend")

    monkeypatch.setattr(plr, "ModelRouter", Boom)
    fn = cli._llm()
    out = fn("anything")
    assert "model unavailable" in out
