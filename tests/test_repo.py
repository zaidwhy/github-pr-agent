"""Repo scan: language counts, key/dep files, ignored dirs, primary language."""

from __future__ import annotations

from pathlib import Path

from autocto.config import get_settings
from autocto.repo import scan_repo


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_basic(tmp_path):
    _write(tmp_path / "app.py")
    _write(tmp_path / "util.py")
    _write(tmp_path / "web" / "index.ts")
    _write(tmp_path / "README.md")
    _write(tmp_path / "pyproject.toml")
    _write(tmp_path / "tests" / "test_app.py")
    _write(tmp_path / "node_modules" / "dep" / "index.js")  # ignored

    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.primary_language == "Python"
    assert a.languages.get("Python") == 3  # app, util, test_app
    assert a.languages.get("TypeScript") == 1
    assert "JavaScript" not in a.languages  # node_modules ignored
    assert "README.md" in a.key_files
    assert "pyproject.toml" in a.dep_files
    assert "tests" in a.top_level_dirs
    assert "node_modules" not in a.top_level_dirs


def test_scan_missing_dir(tmp_path):
    a = scan_repo(tmp_path / "nope")
    assert a.total_files == 0 and a.primary_language is None
