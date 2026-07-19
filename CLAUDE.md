# CLAUDE.md

Guidance for Claude Code (or any coding agent) working in this repository.

## What this project is

GitPDM (`freecad-gitpdm`) is a FreeCAD workbench addon that adds Git version
control and GitHub collaboration inside FreeCAD. It targets CAD users who want
commit/push/pull history and shareable previews for `.FCStd` documents without
leaving FreeCAD. Full user-facing documentation (tutorials, how-tos, reference)
lives in `docs/README.md` — read that for feature behavior; this file is about
working on the code.

Current version: 0.5.0 (kept in sync across `docs/README.md`,
`pyproject.toml`, `freecad_gitpdm/__init__.py`, and `Init.py` — bump all four
together when releasing). `v0.4.0` was tagged from pre-credential-engine
`main`; `v0.5.0` carries G1 (credential engine) + G2 (release automation),
tagged and pushed 2026-07-17 — `.github/workflows/release.yml` ran clean
(verify, build, container-smoke, publish all green) and the release page is
live with the archive attached.

Note for future releases: pushing any change under `.github/workflows/` can
fail with `refusing to allow an OAuth App to create or update workflow ...
without 'workflow' scope` if the local git credential is an OAuth App token
(e.g. GitHub Desktop's helper) — it needs a short-lived PAT with `workflow`
scope for that one push instead.

## Roadmap / current status

Development follows `GITPDM_DEV_PLAN.md` (phases G1–G8, one phase = one PR)
with `GITPDM_REQUIREMENTS.md` as the requirements companion — both at the
repo root on the `dev` branch. Read the phase brief before implementing,
and update the plan's **Status ledger** in the same PR as the work.
Feature work happens on `dev`; CI runs on push/PR to both `main` and `dev`.

Status: **G1 (credential engine), G2 (release + CI), G3 (storage modes), G4
(provider abstraction), G5 (container ergonomics), G6 (continuous
checkpointing), and G7 (docs sweep) are all implemented and merged** on
`dev`, plus two unnumbered efforts built on top per explicit user request:
**multi-provider hosts** (GitLab/Bitbucket/Gitea-Forgejo/SourceHut join
GitHub with real PAT-paste workflows) and a **bottom-dock UI simplification**
(panel collapsed into a short bottom dock, credentials/rare actions moved to
a "Git PDM" menu, native FreeCAD thumbnails for preview). **Next up:** G8's
spike (HistoryWorkbench interop) — needs a real FreeCAD install with both
addons present, so it can't run in this environment; otherwise the only
outstanding item is actually submitting to the FreeCAD Addon Manager index
(R3.3) — `package.xml` is prepared but the submission itself (a GitHub issue
against `FreeCAD/Addons`) needs a maintainer's real contact email and an
icon GitPDM has never had, both flagged in `package.xml`. G6's FreeCAD
busy/dirty API surface was live-verified 2026-07-19 in a real user session
— `slotChangedObject`/`Document.isTouched()` both work as designed, and a
real bug was found and fixed: `FreeCADGui.Control.activeDialog()` returns a
**bool**, not the dialog object or `None`, so checking it with `is not
None` made `_is_freecad_busy()` permanently report "busy" and silently
block every checkpoint (fixed: check truthiness directly). Two items
remain flagged as needing a real-environment verification pass: SourceHut's
GraphQL schema (unverified live) and the embedded-thumbnail zip path/casing
(unverified against a live FreeCAD save — the checkpoint fix above at least
confirms `read_embedded_thumbnail()`'s consumer code runs against real
saves without crashing, but not yet that the rendered image content is
correct) — see `GITPDM_DEV_PLAN.md`'s status ledger for details. The overriding constraint
for every phase: desktop behavior must be a no-op or an improvement ("the
desktop user is sacred").

## Entry points / how FreeCAD loads this

- `Init.py` / `InitGui.py` — FreeCAD addon bootstrap (workbench registration).
  These run inside FreeCAD's embedded Python, not a normal interpreter.
  `InitGui.py`'s `Initialize()` keeps the toolbar to just two frequent
  one-click commands (Toggle Panel, Save Into Repo); everything else lives
  only in the sectioned "Git PDM" menu-bar dropdown it also builds there.
- `freecad_gitpdm/workbench.py` — workbench definition (toolbar/menu wiring).
- `freecad_gitpdm/commands.py` — FreeCAD command objects (the UI entry
  actions). `_find_or_create_dock()` / `_show_dock()` are the shared
  find-or-create-the-panel-then-delegate helpers every command (and
  `InitGui.py`'s auto-open) goes through, so the dock area/tabify behavior
  can't drift between entry points.

Because `FreeCAD`/`FreeCADGui` only exist inside the FreeCAD process, they are
mocked in tests via `tests/conftest.py` (`mock_freecad` autouse fixture,
`mock_qt` fixture for PySide6). Don't assume a real FreeCAD/Qt is importable
when running tests or scripts outside the app.

## Module layout (`freecad_gitpdm/`)

- `auth/` — OAuth device flow (`oauth_device_flow.py`), token storage
  abstracted per-OS (`token_store_wincred.py` / `_macos.py` / `_linux.py` via
  `token_store_factory.py`), scope validation, token refresh. Headless
  credential resolution (`credential_chain.py`): `GITPDM_TOKEN_FILE` >
  `GITPDM_TOKEN` > keyring, with an opt-in file store
  (`token_store_file.py`, only reachable when `GITPDM_ALLOW_FILE_TOKENS=1` —
  a security invariant asserted by tests). `python -m freecad_gitpdm.auth.check`
  is the keyring-less container smoke test; it must keep working without
  FreeCAD installed. When env credential backends are active, `git/client.py`
  bridges the token into network git commands via an inline credential
  helper; on desktop (no env vars) that bridge must stay a no-op.
  `auth/config.py`'s OAuth endpoint constants are re-exports of
  `providers/github/provider.py`'s `GitHubProvider` — that class is the
  actual owner (Phase G4); don't add a second source of truth for them.
- `git/client.py` — subprocess wrapper around the `git` CLI; all Git
  operations (commit/push/pull/fetch/branch) go through here. Host-agnostic
  by design (Phase G4's forcing test relies on this): no provider
  conditionals belong in here. One narrow, deliberate exception:
  `_headless_credential_username()` asks the active provider (via
  `GITPDM_PROVIDER` → `providers.get_provider_class()`) for its
  `credential_username` *property* — the same capability-delegation
  pattern used everywhere else (read a property, never branch on provider
  id), needed because hosts disagree on the username to send alongside a
  PAT over HTTPS (e.g. GitLab requires `oauth2`, Bitbucket requires
  `x-token-auth`). Don't "simplify" this back to a hardcoded value. Phase G6
  added the recovery-branch checkpoint plumbing here too: `rev_parse()`,
  `commit_recovery_checkpoint()`, `push_ref()`, `restore_from_recovery()`,
  `delete_recovery_branch()` — all pure git plumbing (`write-tree`/
  `commit-tree`/`update-ref`, a throwaway `GIT_INDEX_FILE`), never HEAD-
  moving or working-tree-touching porcelain except `restore_from_recovery()`,
  which deliberately does touch the working tree (that's its job) via
  `checkout <sha> -- .` rather than a branch switch, so it doesn't trip the
  branch-switching corruption guard below. `core/checkpoint.py` is the only
  caller; don't call these plumbing methods from `ui/` directly.
- `providers/` — git host abstraction (Phase G4; R5.1-R5.3), extended to
  five hosts in the multi-provider phase (see `GITPDM_DEV_PLAN.md`).
  `base.py` defines `ProviderCapabilities` (`supports_device_flow`,
  `supports_repo_creation`, `supports_lfs_locking`, `supports_pull_requests`,
  plus `requires_manual_token`/`requires_host_url`/`requires_workspace` for
  the PAT-paste hosts) and `BaseProvider`; `GenericProvider` (plain git +
  PAT/SSH, zero host API calls) is the base case, not a fallback.
  `github/` is a subpackage (`GitHubProvider` in `provider.py`, plus the
  REST API client, rate limiting, repo creation, identity, response
  caching it composes) — untouched by the multi-provider work, to keep
  zero regression risk to the one host with real OAuth device-flow
  support. `gitlab/`, `gitea/`, `bitbucket/`, `sourcehut/` are subpackages
  following the same shape, all PAT-paste auth (no device flow: none of
  these has a pre-registered OAuth app GitPDM can use — R5.2 calls PAT/SSH
  "the universal floor" for exactly this reason). `shared/` holds the
  genuinely host-agnostic parts extracted from `github/` for the new
  providers to build on (`http_client.BaseApiClient`'s retry/circuit-
  breaker skeleton, `errors.ProviderApiError`, `cache.ApiCache`,
  `rate_limiter.RateLimiter`) — `github/cache.py` and `rate_limiter.py`
  are now 3-line re-export shims pointing at `shared/`, kept for backward
  compatibility. GitHub's own `GitHubApiError` is deliberately **not** a
  subclass of `ProviderApiError` (avoids any risk to GitHub's working
  error-handling code) — code that needs to catch "any provider's API
  error" (e.g. `ui/new_repo_wizard.py`'s session-expiry handling) catches
  `(GitHubApiError, ProviderApiError)` as an explicit tuple, not a shared
  base class. SourceHut's schema was never live-verified (its GraphQL
  endpoint requires auth even for introspection) — treat it as needing a
  real-token acceptance pass before trusting it in production; the other
  three were all verified against real live endpoints during development.
  `providers/__init__.py`'s `get_provider()`/`get_provider_class()`
  registry is the only place outside `providers/` that should import a
  concrete provider class — UI and `core/` code reads `capabilities`
  flags, never provider ids, to decide what to offer. Per-repo provider
  selection lives in `core/provider_config.py` (`.freecad-pdm/config.json`'s
  `provider` field, defaulting to `"github"` for repos that predate it).
  Connection *credentials* are provider-namespaced too (`core/settings.py`'s
  `save_provider_connected()`/`load_provider_host()` etc., keyed by
  `provider_id`) so a GitHub connection and a GitLab connection coexist
  without one clobbering the other's settings — `core/services.py`'s
  `api_client_for(provider)` resolves host/account through these, not a
  single hardcoded GitHub slot (that was a real bug, found and fixed
  while wiring up the picker/wizard for the new providers).
- `export/` — preview/publish pipeline: mesh export (`stl_converter.py`,
  `model_export.py`), thumbnails (`thumbnail.py`, `view_helper.py`), manifest
  generation (`manifest.py`), and orchestration (`exporter.py`,
  `publish.py` in `core/`). Driven by the optional
  `.freecad-pdm/preset.json` (`export/preset.py`, `export/mapper.py`).
- `core/` — cross-cutting utilities: logging to FreeCAD Report View
  (`log.py`, prefix `[GitPDM]`), background job handling (`jobs.py`), path
  resolution (`paths.py`), settings persistence via FreeCAD parameter store
  (`settings.py`), input validation, diagnostics, scaffolding new repos,
  per-repo provider selection (`provider_config.py`). `checkpoint.py`
  (Phase G6 / R2.5) is the continuous-checkpointing scheduler/policy layer —
  deliberately FreeCAD-agnostic (no `import FreeCAD`, testable with plain
  pytest): `should_checkpoint()` (idle-debounce + max-interval backstop, the
  backstop measured from the last checkpoint, not the last edit, so
  continuous active editing still gets checkpointed periodically),
  `should_auto_push_recovery()` (settings override, else defaults to `True`
  everywhere — desktop and headless alike, revised 2026-07-19 per explicit
  user decision; see R2.5's amendment note in `GITPDM_REQUIREMENTS.md`), and
  `run_checkpoint()`/
  `run_shutdown_checkpoint()`, which take FreeCAD-only concerns
  (`is_busy`/`save_if_dirty`) as injected callables rather than importing
  FreeCAD themselves — `ui/panel.py` supplies the real ones. The git
  plumbing itself lives on `GitClient`, not here (see `git/client.py`
  above).
- `ui/` — the dockable panel (`panel.py`, the largest file in the codebase)
  and its feature handlers: `branch_ops.py`, `commit_push.py`,
  `fetch_pull.py`, `github_auth.py` (GitHub's OAuth
  device-flow connect/disconnect/verify), `pat_auth.py` (the equivalent
  PAT-paste connect/disconnect/verify for GitLab/Bitbucket/Gitea-Forgejo/
  SourceHut — meaningfully simpler, no device-code polling; every method
  takes an explicit `provider_id` since more than one of these can be
  connected at once), `repo_picker.py`, `repo_validator.py`,
  `new_repo_wizard.py`, `dialogs.py`, `connections_dialog.py`,
  `label_style.py`. `GitPDMDockWidget` (`panel.py`) docks at the *bottom*
  of the FreeCAD window (tabbed with Report view/Python console), not the
  side — its content is three columns sharing one row (Repository / Status
  / Actions), not stacked group boxes, so the whole thing stays short. The
  GitHub Account and Other Git Hosts connect/disconnect UI lives in
  `connections_dialog.py`'s `ConnectionsDialog` (opened from the "Git PDM"
  menu, not embedded inline) — constructed eagerly and hidden alongside the
  panel so `GitHubAuthHandler`'s startup checks keep running regardless of
  whether it's currently shown; `github_auth.py`/`pat_auth.py` address
  their parent generically (`self.panel.<attr>`) so they work unmodified
  against either the dock widget or the dialog. `label_style.py` holds the
  meta/strong label styling functions both files use. Rarely-touched or
  dense actions (Connections, Generate Previews, Change Storage Mode,
  Deepen History) are `commands.py` entries reachable
  only from the "Git PDM" top menu-bar dropdown now, not the panel or the
  toolbar — see `commands.py`'s `_find_or_create_dock()`/`_show_dock()`.
  **`ui/file_browser.py` was removed entirely 2026-07-19** per explicit
  user request: its "Repository Browser" dock (a left-side sidebar,
  eagerly created and added to the main window on every panel init,
  tabbed with Tree view) duplicated the OS's own file explorer for
  browsing/opening files and its own click-to-preview duplicated the same
  embedded thumbnail Explorer/Finder already show — real screen space
  spent on functionality the OS already provides for free. Its one
  GitPDM-specific extra, per-file backup-count configuration (max
  `.FCBak` files kept), was removed with it rather than rehomed; it now
  always uses the `move_fcbak_to_previews()` default (3) with no UI to
  change it. `export/exporter.py`'s committed, GitHub-facing `preview.png`
  is now `read_embedded_thumbnail()`'s only consumer (previously shared
  with `file_browser.py`'s in-app preview) — see `export/thumbnail.py`'s
  module docstring; that function itself is unchanged, only its second
  caller went away. `preset.json`'s `thumbnail` sub-block is still
  accepted but no longer consulted by anything (unrelated prior change,
  2026-07-19, when the custom viewport-render pipeline that used to
  generate the exported thumbnail — `set_view_for_thumbnail`/
  `save_thumbnail` — was deleted in favor of the same embedded-thumbnail
  read; see `GITPDM_DEV_PLAN.md`'s bottom-dock-UI "as built" section).
  Also found and fixed while removing this: `branch_ops.py`'s
  `refresh_after_branch_operation()` called
  `self._parent._refresh_repo_browser_files()` — a method deleted from
  `GitPDMDockWidget` by a December 2025 refactor that missed this one
  caller (verified via `git log -S`; see `GITPDM_DEV_PLAN.md`), leaving a
  latent `AttributeError` after every branch switch/create/delete ever
  since, unrelated to and long predating this session's other work.

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
- Provider-specific behavior (GitHub vs. generic vs. GitLab) is gated on
  `provider.capabilities.*` flags, not on provider id or `isinstance` checks
  — UI should never offer an action the active provider can't perform. All
  branching on concrete provider classes lives in `providers/`; `core/`,
  `export/`, and `git/client.py` stay provider-agnostic.
