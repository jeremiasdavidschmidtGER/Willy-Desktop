# Willy Desktop

Desktop creature app (PySide6). Gate A: creature foundation.

- Read `CLAUDE.md` first, then `docs/ARCHITECTURE.md`, `docs/INTERFACES.md`,
  and your task brief in `docs/GATE_A_BACKLOG.md`.
- Art comes from the asset factory repo
  (`...\Willy App\Python-Test`, `assets/gate_a/`) — right-facing canon,
  AnimationManifest JSON per clip. Do not author art here.

## Setup

```powershell
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Standard commands (run before reporting any task done)

```powershell
.\venv\Scripts\python.exe -m pytest
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m ruff format --check .
```

## Run

```powershell
.\venv\Scripts\python.exe -m willy --version
```
