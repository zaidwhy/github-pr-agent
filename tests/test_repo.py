"""Repo scan: language counts, key/dep files, ignored dirs, primary language."""

from __future__ import annotations

from pathlib import Path

import pytest

from github_pr_agent.config import get_settings
from github_pr_agent.repo import scan_repo


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


def test_test_coverage_proxy_counts(tmp_path):
    _write(tmp_path / "app.py")
    _write(tmp_path / "util.py")
    _write(tmp_path / "web" / "index.ts")
    _write(tmp_path / "tests" / "test_app.py")  # test-dir + test_ prefix, counted once
    _write(tmp_path / "web" / "index.test.ts")  # .test. naming convention, no test dir
    _write(tmp_path / "README.md")  # not a _CODE_EXTS file, never counted either way

    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.source_files == 3  # app.py, util.py, web/index.ts
    assert a.test_files == 2  # tests/test_app.py, web/index.test.ts


def test_test_coverage_proxy_todo_fixme_density(tmp_path):
    _write(tmp_path / "app.py", "# TODO: refactor this\ndef f():\n    pass  # FIXME\n")
    _write(tmp_path / "util.py", "def g():\n    return 1\n")

    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.todo_fixme_count == 2
    assert a.source_files == 2


def test_test_coverage_proxy_ignores_lowercase_todo_in_prose(tmp_path):
    _write(tmp_path / "app.py", "# a todo list feature, not a marker\n")
    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.todo_fixme_count == 0


def test_primary_language_prefers_code_over_config_and_docs(tmp_path):
    # jd/tenacity keeps 63 release-note YAML files beside 20 Python files; it is a Python project.
    for i in range(5):
        _write(tmp_path / "releasenotes" / f"note{i}.yaml")
        _write(tmp_path / "docs" / f"page{i}.md")
    _write(tmp_path / "tenacity" / "__init__.py")
    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.primary_language == "Python"


def test_primary_language_falls_back_to_any_file_type(tmp_path):
    # a docs-only repository still reports what it is made of
    _write(tmp_path / "a.md")
    _write(tmp_path / "b.md")
    _write(tmp_path / "c.yml")
    a = scan_repo(tmp_path, get_settings().ignore_dirs)
    assert a.primary_language == "Markdown"
