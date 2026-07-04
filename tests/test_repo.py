"""Repo scan: language counts, key/dep files, ignored dirs, primary language."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_scan_missing_path_raises(tmp_path):
    # A missing path must not look like a valid but empty repo.
    with pytest.raises(FileNotFoundError):
        scan_repo(tmp_path / "nope")


def test_scan_non_directory_raises(tmp_path):
    f = tmp_path / "file.txt"
    _write(f)
    with pytest.raises(NotADirectoryError):
        scan_repo(f)


def test_nested_ignored_dir_is_pruned(tmp_path):
    # An ignored dir nested below the top level must also be skipped, not just at the root.
    _write(tmp_path / "src" / "app.py")
    _write(tmp_path / "src" / "__pycache__" / "app.cpython.pyc")
    _write(tmp_path / "src" / "node_modules" / "dep" / "index.js")

    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.languages.get("Python") == 1  # only src/app.py
    assert "JavaScript" not in a.languages  # nested node_modules pruned


def test_primary_language_tie_is_deterministic(tmp_path):
    # Equal counts must resolve the same way every run (alphabetical), never by walk order.
    _write(tmp_path / "a.py")
    _write(tmp_path / "b.go")
    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.languages.get("Python") == 1 and a.languages.get("Go") == 1
    assert a.primary_language == "Go"  # "Go" sorts before "Python"


def test_empty_repo_has_no_primary_language(tmp_path):
    (tmp_path / "empty").mkdir()
    a = scan_repo(tmp_path / "empty", get_settings().ignore_dirs)
    assert a.total_files == 0
    assert a.primary_language is None
