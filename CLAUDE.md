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

Development follows `Dev_Docs/GITPDM_DEV_PLAN.md` (phases G1–G8, one phase =
one PR) with `Dev_Docs/GITPDM_REQUIREMENTS.md` as the requirements companion
— both in `Dev_Docs/` on the `dev` branch. Read the phase brief before
implementing, and update the plan's **Status ledger** in the same PR as the
work.
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
— `slotChangedObject` fires correctly, and a real bug was found and fixed:
`FreeCADGui.Control.activeDialog()` returns a **bool**, not the dialog
object or `None`, so checking it with `is not None` made `_is_freecad_busy()`
permanently report "busy" and silently block every checkpoint (fixed:
check truthiness directly). A second, more serious bug in the same area
was found later the same day via a further real-world test:
`Document.isTouched()` had originally been claimed to "work as designed"
alongside the fix above, but that was never actually exercised by the
session that found the `activeDialog()` bug — `isTouched()` tracks
FreeCAD's recompute dependency graph, not "unsaved relative to disk," and
since recompute settles almost immediately (well inside the checkpoint
scheduler's 45s idle window), this made `_save_active_document_if_dirty()`
silently skip the real `doc.save()` on the vast majority of genuine edits,
with no exception and no visible symptom — every checkpoint still
committed *something* to `gitpdm/recovery`, just a re-snapshot of
already-stale disk content. Removed outright rather than replaced; see
`core/checkpoint.py`'s entry below and `GITPDM_DEV_PLAN.md`'s
seamless-recovery follow-ups for the full trail. Two items
remain flagged as needing a real-environment verification pass: SourceHut's
GraphQL schema (unverified live) and the embedded-thumbnail zip path/casing
(unverified against a live FreeCAD save — the checkpoint fix above at least
confirms `read_embedded_thumbnail()`'s consumer code runs against real
saves without crashing, but not yet that the rendered image content is
correct) — see `GITPDM_DEV_PLAN.md`'s status ledger for details. The overriding constraint
for every phase: desktop behavior must be a no-op or an improvement ("the
desktop user is sacred").

**G3 (storage modes) was retired 2026-07-20** — see
`Dev_Docs/PRESENCE_AND_LFS_REMOVAL_PLAN.md` for the full record. Real Git
LFS file locking (the entire justification for the "lfs" storage mode) was
never actually implemented on any provider (`supports_lfs_locking` was
`False` everywhere, permanently deferred) — a closer look concluded that
locking's real value is preventing *wasted editing effort*, not preventing
data loss (checkpoints/recovery already make every state recoverable), and
that value doesn't require Git LFS's storage model at all. Two changes
landed together: an advisory, provider-agnostic "who else has this file
open" presence indicator (`core/presence.py`, a `gitpdm/presence` branch,
built on the same git-plumbing pattern as the recovery branch), then the
entire storage-mode split was removed (`core/storage_mode.py`,
`ui/storage_mode_dialog.py`, the wizard's mode picker, the `Change Storage
Mode…` command, `supports_lfs_locking`, `git lfs install` — all deleted).
Every repo behaves like the old "delta" mode now, unconditionally.
`ui/repo_validator.py` surfaces a one-time notice for any repo whose
`.freecad-pdm/config.json` still declares `"storageMode": "lfs"` from
before this, rather than silently ignoring it.

## Entry points / how FreeCAD loads this

- `Init.py` / `InitGui.py` — FreeCAD addon bootstrap (workbench registration).
  These run inside FreeCAD's embedded Python, not a normal interpreter.
  `InitGui.py`'s `Initialize()` keeps the toolbar to just two frequent
  one-click commands (Toggle Panel, Save Into Repo); everything else lives
  only in the sectioned "Git PDM" menu-bar dropdown it also builds there.
  A real-environment install (2026-07-20, right after the workbench icon
  was added) walked through four live iterations to get `Icon` (a
  `GitPDMWorkbench` class attribute) working, mapping out real FreeCAD
  behavior GitPDM now depends on. FreeCAD needs `Icon`/`MenuText`/`ToolTip`
  for *every installed* addon up front (to populate the workbench
  selector), without running each one's full `Init`/`InitGui` — so it
  reads the class body via some lightweight scan, in an execution context
  visibly different from a normal full-file exec: (1) `__file__` is never
  defined there (`Icon = os.path.join(os.path.dirname(__file__), ...)` →
  `name '__file__' is not defined`) — consistent with documented FreeCAD
  behavior that Init.py/InitGui.py are exec'd, never imported, so there's
  no `__file__` the way a normally-imported module gets one. (2) Moving
  that computation into a module-level variable assigned via `try/except`
  one line above the class (`_ADDON_ICON = ...`) failed the same way
  (`name '_ADDON_ICON' is not defined`), even though the plain
  `import os` / `import FreeCADGui` statements above it resolved fine in
  every iteration — so this scan replays plain top-level `import`
  statements from the rest of the file, but not other top-level statement
  shapes (assignments, try/except). (3) Swapping in a plain, unconditional
  `import freecad_gitpdm` (no intermediate variable) to get a reliable
  `__file__` from *that* package still failed
  (`name 'freecad_gitpdm' is not defined`) — unlike `os`/`FreeCADGui`
  (modules already loaded into the embedded interpreter before any addon
  code runs), `freecad_gitpdm` is a real filesystem package needing
  `sys.path` to include the addon's own directory, and this scan
  apparently runs *before* that happens, so the import silently failed
  and the name was never bound — meaning nothing that depends on this
  addon's own files being importable/path-relative can work at this
  point, only FreeCAD's own already-loaded modules are reliably
  available. **Working fix**: derive the path from `FreeCAD`'s own
  `getUserAppDataDir()` instead (joined with the literal `Mod/GitPDM/...`
  layout this project's own install docs tell users to use), computed
  entirely *inside* the class body via a same-scope `try`/`except` (proven
  safe unlike a module-level one — `MenuText`/`ToolTip`/`Icon` assignments
  already ran sequentially in this same class-body namespace across all
  four iterations; a class-body-local variable like `_icon_candidate`
  assigned one line above `Icon`, in the *same* scope, is a fundamentally
  different thing from a *module*-level one per (2)) falling back to `""`
  if the guessed path doesn't exist on disk (e.g. a non-standard install
  location) rather than blocking registration. Confirmed against a local
  Python interpreter with `FreeCAD`/`FreeCADGui` stubbed in, both for the
  file-exists and file-missing branches, before the live FreeCAD retest
  that confirmed it end-to-end.
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
  `supports_repo_creation`, `supports_pull_requests`,
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
  above). `save_if_dirty` returns a `bool` (True = nothing to do or saved
  fine, False = a save was attempted and raised), carried into
  `CheckpointResult.save_ok` (added 2026-07-19): `commit_recovery_checkpoint()`
  is pure git plumbing that snapshots *whatever's currently on disk*
  regardless of whether the save that was supposed to put fresh content
  there actually worked, so a commit landing on `gitpdm/recovery` was
  previously indistinguishable from the outside between "genuinely captured
  the edit" and "no-op re-commit of stale pre-edit content because the
  document save silently failed" — exactly what a 2026-07-19 user report
  described (checkpoint visibly reached GitHub, but the restored file was
  the pre-edit version). `_save_active_document_if_dirty` also now logs a
  failed `doc.save()` at `warning`, not `debug`, so it's visible in Report
  View by default instead of silently swallowed. **That `save_ok` machinery
  turned out to be necessary but not sufficient** — a further real-world
  test (same day) showed `_save_active_document_if_dirty()` was silently
  skipping `doc.save()` entirely (a clean early return, not a raise, so
  invisible to `save_ok`) via a `Document.isTouched()` gate that assumed
  "not touched" meant "no unsaved changes." It doesn't:
  `App::Document.isTouched()` is about FreeCAD's recompute dependency
  graph, and recompute settles almost immediately after an edit — well
  inside the 45s idle-debounce window `should_checkpoint()` waits before a
  tick even fires — so this gate was very likely wrong on close to every
  real checkpoint, not just this one report. Removed outright; the
  function now calls `doc.save()` unconditionally whenever there's an
  active, already-saved document, relying entirely on the outer
  scheduler's `CheckpointState.dirty` (set by `slotChangedObject`, which
  *was* genuinely live-verified) to gate whether it runs at all.

  `note_last_checkpoint_file()`/`load_last_checkpoint_file()` (added
  2026-07-19, seamless-recovery follow-up) persist the absolute path of
  whichever document a checkpoint's `save_if_dirty()` just saved, so a
  later session's restore knows which file to reopen — needed because the
  in-memory `ActiveDocument` is gone after a crash. Written directly to a
  plain JSON file at `.git/gitpdm-last-checkpoint.json`, **not** through
  `core/settings.py`'s FreeCAD-parameter-store (that was this function's
  first version, same day — a *second* user report showed it came back
  empty after a force-quit: FreeCAD's parameter tree is only reliably
  flushed to disk on a clean shutdown, exactly the condition a crash
  violates). Mirrors `core/session_lock.py`'s own reasoning for the same
  choice. `export_recovery_snapshot()` (same follow-up) is the
  non-destructive companion to `restore_recovery_checkpoint()`: instead of
  (in `ui/repo_validator.py`, in addition to) overwriting the working tree
  in place, it extracts the recovery tree into a dated, browsable folder at
  `.git/gitpdm-recovery/<sha8>-<timestamp>/` via `GitClient.
  export_recovery_snapshot()` — a throwaway `GIT_INDEX_FILE` plus an
  alternate `--work-tree` so `git checkout` (binary-safe by construction,
  since git itself writes the bytes — no Python-side text decoding of file
  content is ever involved) lands there instead of `repo_root`, without
  touching the real working tree, index, or HEAD. Lives under `.git/`
  specifically so it can never be walked by `git add -A`/recursively
  capture itself into a later checkpoint, without depending on any
  `.gitignore` entry existing. `ui/repo_validator.py`'s
  `_finish_recovery_restore()` uses both, but asymmetrically: reopening the
  exact file automatically (via `load_last_checkpoint_file()`) is the
  success path and involves no Explorer at all — an initial version of
  this always surfaced (or auto-opened) the export folder too, as a
  "here's proof it worked" safety net from back when the reopened content
  itself couldn't be fully trusted (before the `isTouched()` fix below); a
  direct user report once that was fixed called the Explorer popup out as
  pure friction once the native reopened view already shows the right
  thing, so it's gone from the success path. `export_recovery_snapshot()`
  still runs every time (cheap, no UI) and its folder is still the
  fallback — via `ui/panel.py`'s `_open_folder_in_explorer_selecting()`,
  Explorer-with-file-preselected — for the one case that still needs it:
  the exact file can't be reopened automatically.

  `GitClient.list_recovery_checkpoints()` (added 2026-07-19, same day)
  lists every commit on `gitpdm/recovery` newest-first via `git log
  <ref> --not HEAD` — the `--not HEAD` matters: without it, the log walk
  includes whatever commit the recovery branch forked from (see
  `commit_recovery_checkpoint()`'s `parent_sha`), not just the
  checkpoint-specific commits (caught by the tests for this, which counted
  one extra entry before the fix). `core/checkpoint.py`'s
  `list_recovery_checkpoints()` wraps it for the usual testability reason.
  Exists because "restore the latest" is often a no-op once checkpoints
  correctly auto-save the real working file too (see the `isTouched()` fix
  above) — the working file and the latest checkpoint end up identical in
  the common case, so recovering an *older* point in the session is what
  actually uses the branch's continuous history rather than restoring
  something already on disk. `ui/dialogs.py`'s new `RecoveryHistoryDialog`
  (a `QListWidget` of timestamp+short-SHA entries) surfaces this, wired
  into `ui/repo_validator.py`'s `_pick_recovery_checkpoint()` — but **only**
  for the on-demand "Restore Recovery Checkpoint" menu command
  (`interactive_when_unavailable=True`); the automatic restore-on-start
  offer stays a fast single Yes/No on the latest tip, since browsing
  history isn't the right friction for the "just crashed, want my work
  back" moment.

  Same-day follow-up, per a further user report: history browsing alone
  still required opening GitPDM's UI and explicitly restoring to see a
  past checkpoint. `export_recovery_snapshot()` now runs automatically
  after *every* successful checkpoint (`ui/panel.py`'s
  `_on_checkpoint_timer_tick()`, silent/best-effort — a convenience on top
  of an already-successful checkpoint, not something that should surface
  its own error UI on every tick), so `.git/gitpdm-recovery/` builds a
  standing, self-populating history in Explorer with zero GitPDM
  interaction needed, not just a one-off export at restore time. Two
  things had to change to make that folder actually useful as a
  chronological trail: (1) export folders are now named
  `<timestamp>-<sha8>` (timestamp first, was `<sha8>-<timestamp>`) so
  Explorer's default alphabetical sort is chronological order for free;
  (2) that timestamp comes from `GitClient.commit_timestamp()` — the
  checkpoint commit's own `%cI` committer date — not wall-clock "now" at
  export time, since those two can differ arbitrarily (restoring an old
  entry from the history browser exports it long after it was made) and a
  user report specifically called out that using export-time made
  chronological tracking impossible. Unbounded folder-per-checkpoint
  growth over a long session is a real disk-usage risk (each export is a
  full checked-out copy, not a diff) — `_prune_old_recovery_exports()`
  caps retained exports at `MAX_RETAINED_RECOVERY_EXPORTS` (30), safe to
  prune by plain lexicographic name sort given the timestamp-first naming.
  `prune_recovery_branch()` (already called after every real commit, and
  from "Clear Recovery Checkpoint") now also wipes the entire export
  folder tree via `shutil.rmtree(..., ignore_errors=True)`, on the same
  logic as clearing the branch itself: a real commit supersedes every
  earlier checkpoint, so the accumulated folders stop meaning anything.
- `ui/` — the dockable panel (`panel.py`, the largest file in the codebase)
  and its feature handlers: `branch_ops.py`, `commit_push.py`,
  `fetch_pull.py`, `github_auth.py` (GitHub's OAuth
  device-flow connect/disconnect/verify), `pat_auth.py` (the equivalent
  PAT-paste connect/disconnect/verify for GitLab/Bitbucket/Gitea-Forgejo/
  SourceHut — meaningfully simpler, no device-code polling; every method
  takes an explicit `provider_id` since more than one of these can be
  connected at once), `repo_picker.py`, `repo_validator.py`,
  `new_repo_wizard.py`, `dialogs.py`, `connections_dialog.py`,
  `label_style.py`. `GitPDMDockWidget` (`panel.py`) is a plain `QDockWidget`
  with no fixed home area -- `commands._find_or_create_dock()` (also used by
  `InitGui.py`'s auto-open) is the single place that decides where it lands
  on first creation: **left dock area**, tabbed with Report view/Python
  console when either is present, as of a second 2026-07-19 pass that moved
  it there from the bottom per an explicit user screenshot showing that spot
  (bottom-left corner of the left dock, tabbed alongside those two) using
  the least screen space. Its layout isn't tied to either shape though: as of
  the same day's earlier toolbar-consolidation pass, `columns_row` and a handful of
  button rows inside it (`switch_row` in `_build_repo_selector`, `row1_layout`
  in `_build_buttons_section`) are built as `QBoxLayout` rather than a fixed
  `QHBoxLayout`, and `GitPDMDockWidget.resizeEvent()` flips their
  `.setDirection()` between `LeftToRight` and `TopToBottom` based on the
  dock's own aspect ratio (with hysteresis, so it doesn't flap near-square)
  — see `_maybe_update_layout_orientation()`/`_apply_layout_orientation()`.
  This is what makes the panel usable when a user drags it to a side dock
  (narrow/tall) instead of only the bottom (wide/short); any new
  toolbar-like row of buttons should follow the same pattern (build as
  `QBoxLayout`, append to `self._responsive_layouts`) rather than a fixed
  `QHBoxLayout`. The same pass also merged the old separate "Repository"
  and "Status" group boxes/columns into one — `working_tree_label`/
  `ahead_behind_label`/`operation_status_label` now sit in a header row
  alongside `repo_name_label` inside `_build_repo_selector` instead of
  costing their own column — and replaced `repo_name_label`'s hardcoded
  black, word-wrapped text with `label_style.ElidedLabel` (single line,
  `...`-truncated, full name in the tooltip) styled in
  `label_style.REPO_NAME_ACCENT`, a legible accent distinct from the
  green/orange/red/gray/`#4db6ac` semantic status colors used elsewhere so
  the name is never mistaken for a status signal. The GitHub Account and
  Other Git Hosts connect/disconnect UI lives in
  `connections_dialog.py`'s `ConnectionsDialog` (opened from the "Git PDM"
  menu, not embedded inline) — constructed eagerly and hidden alongside the
  panel so `GitHubAuthHandler`'s startup checks keep running regardless of
  whether it's currently shown; `github_auth.py`/`pat_auth.py` address
  their parent generically (`self.panel.<attr>`) so they work unmodified
  against either the dock widget or the dialog. `label_style.py` holds the
  meta/strong label styling functions both files use. Rarely-touched or
  dense actions (Connections, Generate Previews,
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
