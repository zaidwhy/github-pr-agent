"""Settings for AutoCTO. Env-overridable with the AUTOCTO_ prefix."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AutoCtoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTOCTO_", env_file=".env", extra="ignore")

    # Local model used for reasoning (report commentary, issue refinement, PR plans) when no
    # OLLAMA_MODEL / Gemini key is set. Matches Second Brain's default.
    ollama_model: str = "qwen2.5:3b-instruct"
    # Directories never worth scanning as source.
    ignore_dirs: tuple[str, ...] = (
        ".git", "venv", ".venv", "node_modules", "__pycache__", "dist", "build",
        ".pytest_cache", ".mypy_cache", ".next", "target", ".idea", ".vscode",
    )


_settings: AutoCtoSettings | None = None


def get_settings() -> AutoCtoSettings:
    global _settings
    if _settings is None:
        _settings = AutoCtoSettings()
    return _settings
