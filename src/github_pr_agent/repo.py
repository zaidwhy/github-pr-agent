"""Repository analysis: read a local checkout and summarize what it is.

Pure filesystem work, no LLM and no Personal LLM import, so it is fully testable offline.
The scan is deterministic (sorted traversal) and resilient (ignored directories are pruned, not
descended into, and unreadable directories are skipped rather than raising).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Extension -> human language/label. Small, extend as needed.
_LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cs": "C#", ".php": "PHP",
    ".swift": "Swift", ".kt": "Kotlin", ".sh": "Shell", ".sql": "SQL", ".md": "Markdown",
    ".css": "CSS", ".scss": "CSS", ".html": "HTML", ".yml": "YAML", ".yaml": "YAML",
}

# Files that signal how a project is built / documented.
_KEY_FILES = {
    "readme.md", "readme.rst", "readme.txt", "license", "license.md", "license.txt",
    "contributing.md", "code_of_conduct.md", "changelog.md", "dockerfile", "makefile",
}
_DEP_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile",
    "package.json", "cargo.toml", "go.mod", "pom.xml", "build.gradle", "gemfile",
}

# Extensions counted toward the test-coverage-proxy signal (source_files/test_files/
# todo_fixme_count below) - a subset of _LANG_BY_EXT that excludes docs/style/config
# formats (.md, .css, .html, .yml, ...) that aren't "source" for that signal's purpose.
_CODE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb",
    ".c", ".h", ".cpp", ".cc", ".cs", ".php", ".swift", ".kt", ".sh",
}
_TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "specs"}
_TODO_FIXME_RE = re.compile(r"\b(?:TODO|FIXME)\b")


def _is_test_file(fname: str, parent_dir_names: set[str]) -> bool:
    """Test-file naming/location conventions: test_x.py, x_test.py, x.test.js, x.spec.ts,
    or anything under a tests/test/__tests__/spec(s) directory at any depth."""
    stem = Path(fname).stem.lower()
    if stem.startswith("test_") or stem.endswith(("_test", ".test", "_spec", ".spec")):
        return True
    return bool(parent_dir_names & _TEST_DIR_NAMES)


def _count_todo_fixme(fpath: Path) -> int:
    try:
        text = fpath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(_TODO_FIXME_RE.findall(text))


@dataclass
class RepoAnalysis:
    root: str
    total_files: int = 0
    languages: dict[str, int] = field(default_factory=dict)  # language -> file count
    key_files: list[str] = field(default_factory=list)
    dep_files: list[str] = field(default_factory=list)
    top_level_dirs: list[str] = field(default_factory=list)
    # Test-coverage-proxy signal (see report.coverage_proxy_signal): counts over _CODE_EXTS
    # files only, so docs/style/config files never dilute the ratio.
    source_files: int = 0
    test_files: int = 0
    todo_fixme_count: int = 0

    @property
    def primary_language(self) -> str | None:
        """The most common language, ties broken alphabetically so the result is stable."""
        if not self.languages:
            return None
        # Iterate keys in sorted order so max() resolves ties deterministically (first seen wins).
        return max(sorted(self.languages), key=self.languages.__getitem__)


def scan_repo(path: str | Path, ignore_dirs: tuple[str, ...] = ()) -> RepoAnalysis:
    """Scan a local checkout. Raises FileNotFoundError / NotADirectoryError for a bad path."""
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    ignore = set(ignore_dirs)
    analysis = RepoAnalysis(root=str(root))

    top_level_captured = False
    # onerror swallows per-directory failures (e.g. PermissionError) so one locked subtree
    # does not abort the whole scan.
    for _dirpath, dirnames, filenames in os.walk(root, onerror=lambda _e: None):
        # Prune ignored directories in place so os.walk never descends into them. This drops
        # .git / node_modules / venv at any depth and keeps the walk fast on large repos.
        dirnames[:] = sorted(d for d in dirnames if d not in ignore)
        if not top_level_captured:
            analysis.top_level_dirs = list(dirnames)
            top_level_captured = True
        dirpath = Path(_dirpath)
        parent_dir_names = {p.lower() for p in dirpath.relative_to(root).parts}
        for fname in filenames:
            analysis.total_files += 1
            suffix = Path(fname).suffix.lower()
            lang = _LANG_BY_EXT.get(suffix)
            if lang:
                analysis.languages[lang] = analysis.languages.get(lang, 0) + 1
            lname = fname.lower()
            if lname in _KEY_FILES and fname not in analysis.key_files:
                analysis.key_files.append(fname)
            if lname in _DEP_FILES and fname not in analysis.dep_files:
                analysis.dep_files.append(fname)
            if suffix in _CODE_EXTS:
                if _is_test_file(fname, parent_dir_names):
                    analysis.test_files += 1
                else:
                    analysis.source_files += 1
                analysis.todo_fixme_count += _count_todo_fixme(dirpath / fname)

    analysis.key_files.sort()
    analysis.dep_files.sort()
    return analysis
