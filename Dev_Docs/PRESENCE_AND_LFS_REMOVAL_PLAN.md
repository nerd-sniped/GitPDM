# GitPDM — Advisory Presence Indicator & LFS Mode Removal (Design Brief)

**Status:** Draft — not started. Written 2026-07-20 from a design discussion, not yet
reviewed against an implementation attempt.
**Audience:** a coding agent (Claude Code) implementing this work in
`nerd-sniped/GitPDM`. Companion to `GITPDM_DEV_PLAN.md`/`GITPDM_REQUIREMENTS.md`;
this file stands alone rather than assigning new R-numbers until the work starts.

## Background: why this exists

GitPDM's storage-mode split (`core/storage_mode.py`, Phase G3) offers a "delta"
mode (default, free, git-native delta compression) and an "lfs" mode (opt-in,
for teams) whose entire stated justification is **file locking** — Git LFS's
ability to reserve a `.FCStd` file so a teammate can't edit it at the same time,
since binary CAD files can't be merged.

That locking was never actually built. Every provider —
`providers/github/provider.py`, `gitlab`, `bitbucket`, `gitea`, `sourcehut` — sets
`supports_lfs_locking=False`, each with the same comment: `# D1, deferred until
a real lfs-mode team user exists`. `core/session_lock.py` exists but solves a
different problem (two GitPDM instances on one shared working tree, e.g. a
hosted container — advisory, local-filesystem-scoped, PID-liveness-based, not
cross-machine).

A closer look at what locking would actually buy a customer: since `.FCStd`
files can't be merged either way, an unprevented conflict just means someone
manually reconciles two versions in FreeCAD — recoverable, since GitPDM already
retains every state via git history (see `core/checkpoint.py`'s recovery
branch) and nothing is ever truly lost. Locking's real value isn't data safety
(git already provides that) — it's **preventing wasted duplicate editing
effort** by telling the second person someone's already in there, before they
sink an hour into work that's doomed to collide.

That value doesn't require Git LFS's storage model at all. LFS mode currently
carries real, measured costs (full-version storage, no delta compression,
counted against GitHub's ~1 GiB free LFS allowance — see `docs/README.md`'s
Storage Modes benchmark) for a benefit (locking) that doesn't exist. Conclusion:
replace the *intent* behind LFS mode with a cheap, provider-agnostic advisory
indicator, then remove LFS mode entirely rather than carry unused, misleadingly
documented capability.

**Sequencing:** implement Plan A before starting Plan B, so there's never a
window where GitPDM has neither real locking nor its advisory replacement.

---

## Plan A — Advisory "file currently open" indicator

**Goal:** warn, never block. Surface "this file may be open elsewhere" with no
enforcement — matching the philosophy `core/session_lock.py` already states
explicitly: "advisory, not enforced... exists to warn, not to block."

### Why not extend `session_lock.py` directly

Its lock lives at `.git/gitpdm.lock` on the local filesystem, and its liveness
check is a literal OS `PID` query (`_pid_alive()`). That's correct for its own
job — two GitPDM instances sharing one working tree — but it fundamentally
cannot cross machines. Two different users on two different computers share
exactly one channel: the git remote itself. Presence has to travel through git,
the same way checkpoints already do via `gitpdm/recovery`.

### Mechanism

- **New module `core/presence.py`**, shaped like `session_lock.py` (a
  dataclass for an entry, the same staleness-by-age pattern as
  `STALE_LOCK_SECONDS`) but backed by a dedicated ref — e.g. `gitpdm/presence`
  — holding one small JSON file (`open-files.json`) mapping file path →
  `{user, host, opened_at, last_heartbeat}`.
- **Reuse existing plumbing, don't duplicate it.** `git/client.py` already has
  everything this needs — `write-tree`/`commit-tree`/`update-ref`/`push_ref`/
  `rev_parse`, built for `gitpdm/recovery` in Phase G6. Generalize those
  methods to take a ref name instead of hardcoding `gitpdm/recovery`, so
  `core/presence.py` calls the same low-level methods pointed at a different
  ref, rather than growing a second set of plumbing.
- **On document open:** fetch `gitpdm/presence` (best-effort, silent-fail if
  offline — identical tolerance to how the recovery push already degrades).
  Check for a live entry on that file under a different user/host; if found,
  show a **non-blocking** info dialog: *"Also open by Alice, last seen 3m ago.
  You can keep working — if you both save, you'll get a conflict to resolve
  manually."* Then write/commit/push our own entry.
- **Heartbeat:** reuse the panel's existing 5-minute timer (the one already
  driving `session_lock.refresh_lock` — see `ui/panel.py`'s
  `_lock_refresh_timer`/`_on_lock_refresh_tick`) to refresh our entry's
  timestamp while the document stays open.
- **On close:** remove our entry, commit, push — best-effort. If it fails
  (crash, offline), the entry just ages out; reuse the same staleness
  threshold pattern as `STALE_LOCK_SECONDS` so a dead session degrades
  gracefully to "last seen 47m ago" rather than a false "currently open."
- **UI:** one status row next to the repo selector in `ui/panel.py`, using the
  existing semantic colors from `ui/label_style.py` (green "you have this
  open" / amber "also open by X").

### Why this is provider-agnostic by construction

It's plain git under the hood — no host API calls, no per-provider
integration. This directly closes the gap that `supports_lfs_locking=False` is
stuck at on every provider today, permanently, without ever needing a host's
native locking API.

### Rough file list

| File | Change |
| --- | --- |
| `core/presence.py` | **New.** Data model, read/write/heartbeat/prune against the `gitpdm/presence` ref. |
| `git/client.py` | Generalize the recovery-branch plumbing methods to accept a ref name parameter. |
| `ui/panel.py` | Hook document open/close (FreeCAD document observer, alongside the existing checkpoint dirty-tracking hook) to call `presence.announce_open()`/`announce_close()`; wire heartbeat into the existing timer. |
| `ui/dialogs.py` | New non-blocking "also open by X" notice. |
| `ui/label_style.py` | Reuse existing semantic colors for the new status row. |
| `tests/test_presence.py` | **New.** Mirrors `tests/test_session_lock.py`'s structure, exercising read/write/staleness against a temp repo. |

---

## Plan B — Cleanly remove LFS mode

Scoped against the current codebase: **195 references to "lfs" across 23
files.**

### Removals and edits

1. **Delete outright:**
   - `core/storage_mode.py`
   - `ui/storage_mode_dialog.py`
   - `tools/storage_mode_benchmark.py`
   - `tests/test_storage_mode.py`
2. **`core/scaffold.py`** — drop the `mode` parameter; always write the delta
   `.gitattributes` line (`*.FCStd binary`); stop writing `storageMode` into
   `.freecad-pdm/config.json`.
3. **`core/checkpoint.py`** — remove `LFS_MAX_INTERVAL_SECONDS` and the mode
   branch in `max_interval_seconds_for_repo()`; always return
   `DEFAULT_MAX_INTERVAL_SECONDS`.
4. **Compression scoping** — wherever `core/settings.py`'s
   `enter_git_friendly_compression_scope` (or its caller) currently gates on
   `storage_mode.get_storage_mode() == MODE_DELTA`, make it unconditional,
   since delta becomes the only mode.
5. **`git/client.py`** — remove `lfs_install()` (currently line 2296), which
   becomes uncalled once `storage_mode.py` is gone.
6. **`commands.py`** — remove `GitPDMChangeStorageModeCommand` and its "Git
   PDM" menu entry (wired in `InitGui.py`).
7. **`ui/new_repo_wizard.py`** (23 refs) — remove the storage-mode step/radio
   from repo creation; new repos are just delta, no user-facing choice.
8. **`ui/panel.py`** (2 refs) — remove the Storage Mode row and its dialog
   wiring.
9. **`providers/base.py`** and all five provider files (`github`, `gitlab`,
   `gitea`, `bitbucket`, `sourcehut`) — remove `supports_lfs_locking` from
   `ProviderCapabilities` and every provider's instantiation of it. Dead once
   there's no LFS mode to gate — and Plan A replaces its intent anyway.
10. **`docs/README.md`** (24 refs) — remove both "Storage Modes" sections (the
    Technical Reference table and the "Storage Modes (Delta vs. LFS)"
    user-facing section); simplify "Why GitPDM Sets FreeCAD's Compression
    Level to 0" to unconditional wording (no more "in Delta Mode" qualifier);
    fix any TOC/cross-reference links to the removed anchors.
11. **Dev docs** — `GITPDM_DEV_PLAN.md` (20 refs), `GITPDM_REQUIREMENTS.md` (19
    refs), `MANUAL_TEST_CHECKLIST.md` (11 refs): add a status-ledger note that
    R1.1/G3's mode choice was retired, with the rationale (locking was never
    implemented; LFS mode had no compensating benefit over delta), rather than
    silently deleting the historical record — matches this project's existing
    convention of narrating decisions in place rather than scrubbing them.
12. **Tests** — strip LFS-mode branches from `tests/test_checkpoint.py` (4
    refs) and `tests/test_providers.py` (3 refs, likely asserting the
    `supports_lfs_locking` capability shape).
13. **`tools/architecture_baseline.json`** — remove baseline entries for
    deleted files; adjust the entry for `new_repo_wizard.py`'s reduced line
    count.
14. **`CLAUDE.md`** — update the one reference to reflect removal.

### The one non-deletion concern: existing LFS-mode repos

A repo that's already been switched to `"lfs"` (a `.freecad-pdm/config.json`
with `storageMode: "lfs"` plus an LFS-filter line in `.gitattributes`) will
suddenly be unrecognized once storage-mode code is gone. Since locking never
actually worked, no team is depending on a real payoff — but the removal PR
should still handle this gracefully rather than silently ignoring it:
`ui/repo_validator.py` should detect that state on repo open and surface a
one-time notice — *"This repo was set to LFS mode, which GitPDM no longer
manages. Your files and `.gitattributes` are untouched, but switching back to
plain git tracking is now a manual step."* — rather than doing nothing and
leaving the user to wonder why the option disappeared.

### Verification after removal

- `ruff check` / `ruff format --check`
- Full `pytest`
- `python tools/architecture_guard.py`
- Manual: create a new repo end-to-end and confirm no storage-mode UI appears
  anywhere (wizard, panel, "Git PDM" menu).
- Manual: open a repo with a pre-existing `storageMode: "lfs"` config and
  confirm the compatibility notice appears instead of a crash or silent
  no-op.

---

## Status ledger

| Item | Status |
| --- | --- |
| Plan A — advisory presence indicator | ✅ Implemented, `dev`, 2026-07-20 |
| Plan B — LFS mode removal | ✅ Implemented, `dev`, 2026-07-20 |

### Plan A — as built (2026-07-20)

Implemented essentially as designed above, with a few things worth recording
for whoever touches this next:

- **`GitClient` gained six new plumbing methods** (`hash_object`,
  `make_tree_with_file`, `commit_tree_with_parent`, `update_ref_cas`,
  `read_file_at_ref`, `fetch_ref`) rather than generalizing
  `commit_recovery_checkpoint`/`push_ref` as originally suggested --
  `push_ref`/`rev_parse` already took a ref-name parameter and needed no
  changes at all; `commit_recovery_checkpoint` was left alone because its
  whole-working-tree snapshot semantics (via a throwaway index + `add -A`)
  are a poor fit for a single-small-JSON-file commit, so presence writes its
  tree directly with `hash-object`/`mktree` instead of reusing that method.
- **Real bug caught by the real-git tests, not code review**: feeding
  `mktree`'s stdin entry via `subprocess.run(text=True, input=...)` corrupted
  the filename with a trailing `\r` on Windows -- text-mode stdin silently
  translates `\n` to `\r\n` on write, and `mktree` splits entries on `\n`, so
  the `\r` ends up baked into the tree object's path permanently. Fixed by
  encoding the input to bytes and decoding output ourselves in a new
  `_run_command_with_input` helper, sidestepping platform newline
  translation entirely. Caught by
  `TestGitClientPresencePlumbing::test_hash_object_and_read_back_via_tree_commit`
  against a real repo -- exactly the kind of bug a mocked subprocess test
  would have missed.
- **Race handling is optimistic-concurrency, not force-push**: a
  read-latest/merge/CAS-write/retry-once loop (`_MAX_WRITE_ATTEMPTS = 2` in
  `core/presence.py`), never a force-push -- consistent with this repo's
  existing rule that nothing touches the recovery/presence branches
  destructively. A repeated race (very unlikely for human-paced document
  opens/heartbeats) just skips that cycle silently; the next heartbeat
  re-asserts.
- **Identity resolution needed a two-step fallback.**
  `GitClient.get_config(repo_root, key, local=True/False)` is an explicit
  either/or (local flag forces `--local`, its absence forces `--global`),
  not "prefer local, fall back to global" -- so `core/presence.py`'s
  `_own_identity()` calls it twice (local first, then global) to get the
  same effective value a plain `git commit` in that repo would use. Worth
  fixing at the `GitClient.get_config` layer itself if another caller needs
  the same effective-config behavior later.
- **UI hook points**: `ui/panel.py`'s `_DocumentObserver.slotCreatedDocument`
  (already existed) now also announces an open when `doc.FileName` is
  already set (covers File > Open; a brand-new unsaved document has no
  FileName yet, so nothing to announce); a first Save/Save As is covered
  separately in `slotFinishSaveDocument`. A new `slotDeletedDocument`
  announces the close. Heartbeat rides the existing 5-minute
  `_lock_refresh_timer`/`_on_lock_refresh_tick` (already used for
  `session_lock`) rather than a new timer. All of it runs through
  `self._job_runner.run_callable` (background thread), never on the UI
  thread -- `fetch_ref`/`push_ref` have network timeouts up to a couple of
  minutes, and neither opening/closing a document nor closing the panel
  should ever be able to hang on them.
- **Architecture guard bumped** in the same change:
  `freecad_gitpdm/ui/panel.py` 2850->3000 lines,
  `freecad_gitpdm/git/client.py` 2400->2600 lines (see
  `tools/architecture_baseline.json` for the itemized notes).
- **Tests**: `tests/test_presence.py`, 18 tests, run against a real temp
  repo + a real bare-repo remote (two simulated users), the same style as
  `test_checkpoint.py`/`test_generic_provider_flow.py` -- deliberately not
  mocked, since the whole point is proving real cross-repo git state
  behaves as designed.

### Plan B — as built (2026-07-20)

Implemented essentially as scoped above (195 references across 23 files at
the time of the original scope), with a couple of things that came up
during the actual removal:

- **`core/scaffold.py` keeps a `.gitattributes` writer, just a simpler
  one.** Rather than deleting `.gitattributes` handling outright, it now
  writes the single `*.FCStd binary` line directly (a small inlined
  `_ensure_fcstd_gitattributes_line()`, preserving any other lines already
  present) instead of delegating to `storage_mode.apply_storage_mode()`.
  `.freecad-pdm/config.json` itself is untouched by scaffolding now --
  `core/provider_config.py` already creates/merges into that file on its
  own (it never depended on scaffold having created it first), so once
  `storageMode` was the only other thing writing to it, scaffold had
  nothing left to do there.
- **Compression scoping lost its mode gate, not its existence.**
  `core/settings.py`'s `enter_git_friendly_compression_scope()` mechanism
  is unrelated to the mode split conceptually (it's about making `.FCStd`
  saves delta-friendly) and stays exactly as it was -- only the
  `if storage_mode.get_storage_mode(repo_root) == MODE_DELTA:` gate in
  `ui/panel.py`'s `_maybe_enter_compression_scope()` came out, so it now
  applies to every save unconditionally.
- **One genuine compatibility gap handled, not just deleted around:**
  `ui/repo_validator.py` gained `_check_legacy_lfs_storage_mode()`, a
  one-time-per-session `QMessageBox.information()` for any repo whose
  `.freecad-pdm/config.json` still has `"storageMode": "lfs"` from before
  this change -- read-only, never touches `.gitattributes` or the config
  file, just makes the removal visible instead of silent.
- **Nothing needed a capability-flag migration.** `supports_lfs_locking`
  was `False` on every provider already, so removing the field from
  `ProviderCapabilities` and all five `provider.py` files was a pure
  deletion with no behavior change to reconcile.
- **Docs got a straight swap, not just deletions:** `docs/README.md`'s
  Technical Reference "Storage Modes" section became "Advisory File
  Presence" (describing Plan A instead), and the Explanations-layer
  "Storage Modes (Delta vs. LFS)" section became "Why GitPDM Doesn't Offer
  Git LFS File Locking" -- pointing at the presence indicator as the
  replacement rather than just disappearing. `Dev_Docs/GITPDM_DEV_PLAN.md`,
  `GITPDM_REQUIREMENTS.md`, and `MANUAL_TEST_CHECKLIST.md` all got
  retirement notes added in place rather than having the historical G3
  brief/requirements deleted, matching this repo's existing convention of
  narrating decisions rather than scrubbing history --
  `MANUAL_TEST_CHECKLIST.md`'s G3 section did get its actual test steps
  replaced (T3.4/T3.5 mode-switch tests, T3.7 benchmark-script test), since
  a checklist testing deleted UI is actively misleading in a way a
  historical build log isn't; it also gained a new "Advisory File
  Presence" section (TP.1-TP.5) for Plan A, which had no manual-test
  coverage recorded anywhere yet.
- **No architecture-baseline changes needed** -- every file that lost
  storage-mode code shrank (most notably `ui/panel.py` and
  `ui/repo_validator.py`), so nothing crossed a limit in the other
  direction.
- **Verification:** `ruff check`/`format --check` clean, full `pytest`
  (434 passed, 1 skipped -- down from 449 by exactly the deleted
  `test_storage_mode.py` suite plus the one retired LFS-interval test in
  `test_checkpoint.py`), `tools/architecture_guard.py` clean.
