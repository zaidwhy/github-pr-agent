"""Repository analysis: read a local checkout and summarize what it is.

Pure filesystem work, no LLM and no Personal LLM import, so it is fully testable offline.
The scan is deterministic (sorted traversal) and resilient (ignored directories are pruned, not
descended into, and unreadable directories are skipped rather than raising).
"""

from __future__ import annotations

import os
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


@dataclass
class RepoAnalysis:
    root: str
    total_files: int = 0
    languages: dict[str, int] = field(default_factory=dict)  # language -> file count
    key_files: list[str] = field(default_factory=list)
    dep_files: list[str] = field(default_factory=list)
    top_level_dirs: list[str] = field(default_factory=list)

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
        for fname in filenames:
            analysis.total_files += 1
            lang = _LANG_BY_EXT.get(Path(fname).suffix.lower())
            if lang:
                analysis.languages[lang] = analysis.languages.get(lang, 0) + 1
            lname = fname.lower()
            if lname in _KEY_FILES and fname not in analysis.key_files:
                analysis.key_files.append(fname)
            if lname in _DEP_FILES and fname not in analysis.dep_files:
                analysis.dep_files.append(fname)

    analysis.key_files.sort()
    analysis.dep_files.sort()
    return analysis
