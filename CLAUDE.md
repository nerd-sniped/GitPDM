# CLAUDE.md

Guidance for Claude Code (or any coding agent) working in this repository.

## What this project is

GitPDM (`freecad-gitpdm`) is a FreeCAD workbench addon that adds Git version
control and GitHub collaboration inside FreeCAD. It targets CAD users who want
commit/push/pull history and shareable previews for `.FCStd` documents without
leaving FreeCAD. Full user-facing documentation (tutorials, how-tos, reference)
lives in `docs/README.md` — read that for feature behavior; this file is about
working on the code.

Current version: 0.4.0 (kept in sync across `docs/README.md`,
`pyproject.toml`, `freecad_gitpdm/__init__.py`, and `Init.py` — bump all four
together when releasing).

## Entry points / how FreeCAD loads this

- `Init.py` / `InitGui.py` — FreeCAD addon bootstrap (workbench registration).
  These run inside FreeCAD's embedded Python, not a normal interpreter.
- `freecad_gitpdm/workbench.py` — workbench definition (toolbar/menu wiring).
- `freecad_gitpdm/commands.py` — FreeCAD command objects (the UI entry actions).

Because `FreeCAD`/`FreeCADGui` only exist inside the FreeCAD process, they are
mocked in tests via `tests/conftest.py` (`mock_freecad` autouse fixture,
`mock_qt` fixture for PySide6). Don't assume a real FreeCAD/Qt is importable
when running tests or scripts outside the app.

## Module layout (`freecad_gitpdm/`)

- `auth/` — GitHub OAuth device flow (`oauth_device_flow.py`), token storage
  abstracted per-OS (`token_store_wincred.py` / `_macos.py` / `_linux.py` via
  `token_store_factory.py`), scope validation, token refresh.
- `git/client.py` — subprocess wrapper around the `git` CLI; all Git
  operations (commit/push/pull/fetch/branch) go through here.
- `github/` — GitHub REST API client, rate limiting, repo creation, identity,
  response caching.
- `export/` — preview/publish pipeline: mesh export (`stl_converter.py`,
  `model_export.py`), thumbnails (`thumbnail.py`, `view_helper.py`), manifest
  generation (`manifest.py`), and orchestration (`exporter.py`,
  `publish.py` in `core/`). Driven by the optional
  `.freecad-pdm/preset.json` (`export/preset.py`, `export/mapper.py`).
- `core/` — cross-cutting utilities: logging to FreeCAD Report View
  (`log.py`, prefix `[GitPDM]`), background job handling (`jobs.py`), path
  resolution (`paths.py`), settings persistence via FreeCAD parameter store
  (`settings.py`), input validation, diagnostics, scaffolding new repos.
- `ui/` — the dockable panel (`panel.py`, the largest file in the codebase)
  and its feature handlers: `branch_ops.py`, `commit_push.py`,
  `fetch_pull.py`, `file_browser.py`, `github_auth.py`, `repo_picker.py`,
  `repo_validator.py`, `new_repo_wizard.py`, `dialogs.py`.

## Key behavioral constraint: branch switching safety

`.FCStd` files are ZIP archives. If the working tree changes under an *open*
FreeCAD document, the file can corrupt. Code that touches branch
switching/checkout/worktrees must account for this — the existing pattern is
to require documents closed before risky Git operations. Don't relax this
without understanding why it's there (see `docs/README.md` "Why Branch
Switching Is Tricky with FreeCAD Files").

## Working with the code

### Tests

```bash
pip install -e ".[dev]"
pytest
```

- Tests live in `tests/`, mirroring module names (`test_git_client.py`,
  `test_oauth_device_flow.py`, etc.).
- `FreeCAD`/`FreeCADGui` are auto-mocked (see `tests/conftest.py`) — don't add
  a real FreeCAD dependency to test setup.
- Stray `.pyc` files under `__pycache__/` and `freecad_gitpdm/**/__pycache__/`
  reference some modules/tests that no longer exist as source (e.g.
  `test_stl_converter`, `test_worktree_corruption`). These are just build
  byproducts, not evidence of missing files — don't treat them as a signal
  that something was deleted by mistake.

### Lint

```bash
ruff check .
ruff format --check .
```

Ruff's `select` list is intentionally small (`E9, F63, F7, F82` — syntax
errors and undefined names only). Don't silently expand it as part of an
unrelated change.

### Architecture guard

`tools/architecture_guard.py` enforces max line counts for specific files
listed in `tools/architecture_baseline.json` (mostly `ui/` and `export/`
modules), to push back on files growing unboundedly. Run it locally:

```bash
python tools/architecture_guard.py
```

If a change legitimately grows one of these files past its limit, bump the
limit in `tools/architecture_baseline.json` in the same PR — don't just let
CI fail.

### CI

`.github/workflows/ci.yml` runs on push/PR to `main` and `dev`: ruff lint
and format check, pytest across Python 3.10/3.11/3.12 on Linux/Windows/macOS,
and the architecture guard. All three must pass.

## Conventions worth following

- Log via `core/log.py` with the `[GitPDM]` prefix so messages show up
  consistently in FreeCAD's Report View — don't use bare `print`.
- Settings go through `core/settings.py` (FreeCAD parameter store at
  `User parameter:BaseApp/Preferences/Mod/GitPDM`), not ad-hoc config files.
- Git operations go through `git/client.py`'s subprocess wrapper rather than
  shelling out to `git` directly elsewhere.
- Platform-specific code (token storage) is split into per-OS files selected
  by a factory (`token_store_factory.py`) — follow that pattern rather than
  branching on `sys.platform` inline throughout the codebase.
