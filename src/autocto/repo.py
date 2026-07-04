"""Repository analysis: read a local checkout and summarize what it is.

Pure filesystem work, no LLM and no Personal LLM import, so it is fully testable offline.
"""

from __future__ import annotations

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
        return max(self.languages, key=self.languages.get) if self.languages else None


def scan_repo(path: str | Path, ignore_dirs: tuple[str, ...] = ()) -> RepoAnalysis:
    root = Path(path)
    ignore = set(ignore_dirs)
    analysis = RepoAnalysis(root=str(root))
    if not root.exists():
        return analysis

    analysis.top_level_dirs = sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name not in ignore
    )

    for file in root.rglob("*"):
        if not file.is_file():
            continue
        if any(part in ignore for part in file.relative_to(root).parts):
            continue
        analysis.total_files += 1
        lang = _LANG_BY_EXT.get(file.suffix.lower())
        if lang:
            analysis.languages[lang] = analysis.languages.get(lang, 0) + 1
        name = file.name.lower()
        if name in _KEY_FILES and file.name not in analysis.key_files:
            analysis.key_files.append(file.name)
        if name in _DEP_FILES and file.name not in analysis.dep_files:
            analysis.dep_files.append(file.name)

    analysis.key_files.sort()
    analysis.dep_files.sort()
    return analysis
