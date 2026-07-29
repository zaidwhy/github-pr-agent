"""Tests for run.cmd (PROJECT-GENESIS.md Tier 6 item 43: one-click run parity).

Static-content checks only - run.cmd is a Windows batch script and this suite runs
on Linux CI, so it asserts the script's shape rather than executing it. AutoCTO's
jarvis.config.json default action ("help") is a one-shot foreground CLI command, not a
spawned server console, so unlike the CivilizationOS/resume-job-fit-ai precedents this
script has no `start ... cmd /k "..."` span at all - see test_no_spawned_console_quoting
below for why the nested-quoting guard from those precedents does not apply here.
"""
from __future__ import annotations

from pathlib import Path

RUN_CMD = Path(__file__).resolve().parents[1] / "run.cmd"


def _text() -> str:
    return RUN_CMD.read_text(encoding="utf-8")


def test_run_cmd_exists():
    assert RUN_CMD.is_file()


def test_runs_the_help_action_matching_jarvis_config():
    text = _text()
    assert "venv\\Scripts\\python -m autocto.interfaces.cli --help" in text


def test_no_env_var_line_since_config_sets_none():
    # jarvis.config.json's "help" action for AutoCTO has no "env" key (unlike
    # ghostwriter/resume-job-fit-ai/recall's entries), so run.cmd must not invent one.
    text = _text()
    assert "set PYTHONIOENCODING" not in text
    for line in text.splitlines():
        assert not line.strip().lower().startswith("set "), f"unexpected env var line: {line!r}"


def test_no_spawned_console_quoting():
    """Mirrors the exact bug class jarvis-launcher's launcher rewrite fixed (a quote
    nested inside a quoted string makes cmd execute the literal, corrupted text) - but
    this script has no `start ... cmd /k "..."` span to begin with, since the config's
    "help" action is a one-shot foreground command rather than a spawned server console.
    The guard still runs in case a future edit reintroduces one without the discipline
    the precedents established."""
    for line in _text().splitlines():
        if "cmd /k" not in line:
            continue
        assert '\\"' not in line, f"escaped quote (nesting) found in: {line!r}"
        assert '""' not in line, f"doubled quote (nesting) found in: {line!r}"
        opens = line.count('"')
        assert opens % 2 == 0, f"unbalanced quotes in: {line!r}"
