@echo off
REM One-click run parity (PROJECT-GENESIS.md Tier 6 item 43): mirrors this project's
REM "help" (default) action in jarvis-launcher's jarvis.config.json so the launcher and
REM this repo never drift. AutoCTO's default action is a one-shot foreground CLI command
REM with no server to start and no browser to open, so - unlike the CivilizationOS/recall
REM "spawn a server, poll a port, open a browser" shape - this script just cds here and
REM runs that exact command directly. The config entry sets no env var, so this doesn't
REM either.
setlocal

cd /d "%~dp0"
venv\Scripts\python -m github_pr_agent.interfaces.cli --help

endlocal
