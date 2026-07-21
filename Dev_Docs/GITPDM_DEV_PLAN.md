# GitPDM — Phased Development Plan (Implementation Briefs)

**Status:** Draft v2 — reviewed against the actual codebase at v0.4.0 (commit `f94343c`, 2026-07-16)
**Audience:** a coding agent (Claude Code) implementing one phase at a time in `nerd-sniped/GitPDM`. Each phase is written as a self-contained brief; both this file and `GITPDM_REQUIREMENTS.md` are committed to the repo, so read them from there.
**Companion:** requirement IDs (R1.1, R2.1a, …) refer to `GITPDM_REQUIREMENTS.md`.

## Revision notes (v2, codebase review)

Draft v1 was written from the README; v2 corrects it against the code. Substantive changes:

- **G1 reframed from "replace" to "extend".** Token expiry/refresh (R2.1a) already exists (`auth/token_refresh.py`, `TokenResponse` with `refresh_token`/`expires_in`/`obtained_at_utc`), as does a `TokenStore` ABC with per-OS backends behind a factory. G1's real gap is the headless resolution rungs, the `provider` field, chain orchestration, and the CLI check.
- **G2 de-duplicated.** CI (ruff + pytest on 3 OSes × Python 3.10–3.12 + architecture guard) already exists in `.github/workflows/ci.yml`. Only the tag-triggered release build and container smoke job are new.
- **Versioning decided:** `v0.4.0` was tagged from pre-G1 `main` on 2026-07-16 (fixes the dead "download latest release" link immediately). The release carrying G1+G2 is **v0.5.0**.
- **G3 now points at shipped code to fix:** `core/settings.py` already silently flips the global compression preference on repo open (the exact R1.2 harm) — G3 is partly a regression fix, not greenfield.
- **G6 gained a hard constraint:** recovery-branch commits must use git plumbing (no checkout, no HEAD movement) because documents are open during checkpoints.
- **R3.2 clarified:** no FreeCAD-in-CI; the support matrix is a documented policy verified manually per release (CI mocks FreeCAD by design).
- Minor: benchmark script goes in `tools/` (repo convention), not `scripts/`; `.freecad-pdm/` config-file pattern already exists (`export/preset.py`) for G3 to mirror.

## Status ledger

Keep this table current — update it in the same PR as the work it describes.

| Phase | Status | Where / when |
|---|---|---|
| G1 credential engine | ✅ Implemented | `dev` @ `ceaa4f5`, 2026-07-17 |
| G2 release + CI | ✅ Implemented | `dev`, 2026-07-17 |
| G3 storage modes | ⛔ Retired 2026-07-20 (see below) | `dev`, 2026-07-18 → retired 2026-07-20 |
| G4 provider abstraction | ✅ Implemented & merged | `dev` @ `e5039de` (PR #7), 2026-07-18 |
| G5 container ergonomics | ✅ Implemented & merged | `dev`, 2026-07-18 |
| Multi-provider hosts (GitLab/Bitbucket/Gitea/SourceHut) | ✅ Implemented & merged | `dev`, 2026-07-18 |
| Bottom-dock UI simplification (panel layout + GitPDM menu + native thumbnails) | ✅ Implemented & committed | `dev`, 2026-07-18 |
| G6 continuous checkpointing | ✅ Implemented | `dev`, 2026-07-18 |
| G7 docs sweep | ✅ Implemented | `dev`, 2026-07-19 |
| Toolbar consolidation + left-dock default (panel merge, responsive layout, dock area move) | ✅ Implemented | `dev`, 2026-07-19 |
| Seamless recovery-checkpoint restore (on-demand command, auto-reopen) | ✅ Implemented | `dev`, 2026-07-19 |
| Checkpoint save_ok tracking + visible checkpoint feedback (root-cause fix for "restored file is pre-edit") | ✅ Implemented | `dev`, 2026-07-19 |
| Non-destructive recovery export + crash-safe last-checkpoint-file marker (fixes reopen-fell-back-to-repo-root + parameter-store-lost-on-crash) | ✅ Implemented | `dev`, 2026-07-19 |
| Checkpoint save was silently a no-op (isTouched() misuse) — real root cause of "recovered file is pre-edit" | ✅ Implemented | `dev`, 2026-07-19 |
| Recovery success path no longer pops Explorer (native reopen is trustworthy now, export stays as a silent fallback) | ✅ Implemented | `dev`, 2026-07-19 |
| Checkpoint history browsing (restore any past checkpoint, not just the latest tip) | ✅ Implemented | `dev`, 2026-07-19 |
| Automatic self-populating recovery-export folder, chronologically named + pruned | ✅ Implemented | `dev`, 2026-07-19 |
| Advisory file presence (Plan A — see `PRESENCE_AND_LFS_REMOVAL_PLAN.md`) | ✅ Implemented | `dev`, 2026-07-20 |
| LFS storage-mode removal (Plan B — see `PRESENCE_AND_LFS_REMOVAL_PLAN.md`) | ✅ Implemented | `dev`, 2026-07-20 |
| Outpost-checklist audit follow-up fixes (see `GITPDM_AUDIT_FIXES.md`) | ✅ Implemented | `dev`, 2026-07-21 |
| G8 | Not started | — |

Also landed on `dev` (2026-07-17), outside any phase:

- Fixed a `TypeError` in `list_local_branches`, `list_remote_branches`, and `pull_ff_only` (broken `timeout=N ** _get_subprocess_kwargs()` splat — these methods crashed on every call).
- Fixed dead token-refresh wiring in `github/identity.py` (imported a nonexistent `get_token_store`; the ImportError was silently swallowed, so pre-request refresh never ran).
- `v0.4.0` tagged from pre-G1 `main`.

Also landed on `dev` (2026-07-18), alongside G4:

- Fixed `git/client.py:set_config()` silently ignoring `repo_root` (missing `-C repo_root`, unlike every sibling method in the class) — `--local` writes landed in the process's cwd instead of the target repo. Dead code until G4's forcing test called it for the first time; caught by CI failing on `ubuntu-latest`/`windows-latest` (no global git identity to mask it) while passing locally and on `macos-latest`. Confirmed via a Linux container with no global git identity: fails before the fix, passes after.

Closed since the table above was first written:

- ~~**G2 release acceptance**~~ ✅ Verified 2026-07-17: tag `v0.5.0` pushed from `dev` @ `b09b27d`, `release.yml` run [29614097103](https://github.com/nerd-sniped/GitPDM/actions/runs/29614097103) completed with all four jobs green (verify, build, container-smoke, publish). Release page live at <https://github.com/nerd-sniped/GitPDM/releases/tag/v0.5.0> (not a draft/prerelease) with `GitPDM-v0.5.0.zip` attached and downloadable — Tutorial 1's release link now resolves to a real, purpose-built archive. No open items remain blocking G2.
- ~~**G1 container acceptance**~~ ✅ Verified 2026-07-17: `docker run --rm -e GITPDM_TOKEN=<pat> python:3.12-slim sh -c "pip install -q -e . && python -m freecad_gitpdm.auth.check"` → `OK — source=env provider=github host=github.com login=nerd-sniped`, exit 0. Genuinely keyring-less image, no SSH, no `.env`. R2.1's acceptance criterion is fully met; G2's container smoke job should still make this a permanent CI check rather than a one-off.
- ~~**v0.4.0 Release page**~~ ✅ Published 2026-07-17 (<https://github.com/nerd-sniped/GitPDM/releases/tag/v0.4.0>, source archive; Tutorial 1's download link now resolves). G2 still automates purpose-built archives for v0.5.0.

No open items remain blocking G1 or G2; both are fully verified end-to-end. The
critical path for the sister deployment repo (G1 → G2) is clear — it can now
build its container image pinned to `v0.5.0`. **G3, G4, and G5 have all
merged into `dev`** (G4 via PR #7 @ `e5039de`, 2026-07-18; G3 and G5 merged
locally from `g3-storage-modes` and `g5-container-ergonomics` on
2026-07-18 so all three could be tested together in one FreeCAD session).
**G6** (checkpointing, needs G5) and **G7** (docs sweep, needs G3) are both
now implemented (see their "as built" sections below). **G8**'s spike
(HistoryWorkbench interop) is the only phase left, and needs a real FreeCAD
install with both addons present to run — not something this environment
can do.

**Multi-provider hosts** (GitLab, Bitbucket, Gitea/Forgejo, SourceHut —
implemented on `multi-provider-hosts` off `dev`, 2026-07-18, not yet
merged): built ahead of G6/G7 per an explicit user request to extend R5.1's
"works with any git host" from GitHub-only to five hosts with real radio-
button workflows, not just the generic paste-a-URL fallback. Doesn't map
onto a G-numbered phase — see the "Multi-provider hosts as built" section
below (placed near Phase G4, which it extends) for the full writeup. In
short: GitLab/Bitbucket/Gitea/SourceHut all authenticate via a pasted PAT
(no device flow — none has a pre-registered OAuth app GitPDM can use;
R5.2 already calls PAT/SSH "the universal floor" for this reason), wired
into the New Repo wizard, the repo picker, and a new panel "Other Git
Hosts" connect section. Found and fixed a real latent bug along the way:
`core/services.py`'s `api_client_for(provider)` accepted a provider
argument but always read GitHub's global settings regardless — connecting
a second provider would have resolved credentials against GitHub's slot.
GitHub's own code (`providers/github/`) was deliberately left untouched
throughout to keep zero regression risk to the one host with real
device-flow support; the genuinely host-agnostic parts of its
implementation (retry/circuit-breaker HTTP client, response cache, rate
limiter) were extracted to `providers/shared/` for the new providers to
build on, with `providers/github/cache.py`/`rate_limiter.py` becoming
backward-compatible re-export shims. GitLab, Bitbucket, and Gitea were all
verified live against real endpoints during development (gitlab.com,
api.bitbucket.org, and Codeberg as a public Forgejo stand-in); **SourceHut
was not** — its GraphQL endpoint requires auth even for schema
introspection, so its mutation/query field names are built from public
API docs only and need a real-token acceptance pass before being trusted
in production (see the "Multi-provider hosts as built" section and
`providers/sourcehut/__init__.py`'s docstring). A lightweight live
smoke-check for the other three (no token needed) lives at
`tools/provider_endpoint_smoke.py`.

**G4 as built** (merged into `dev` via PR #7 @ `e5039de`, 2026-07-18 — kept
for reference; the brief below is the original spec):

- `github/` → `freecad_gitpdm/providers/github/`: moved as a subpackage
  (`api_client.py`, `cache.py`, `create_repo.py`, `errors.py`, `identity.py`,
  `rate_limiter.py`, `repos.py` unchanged apart from import paths), not a
  single `github.py` file as the brief sketched — the existing files already
  total ~700 lines and the architecture guard exists precisely to push back
  on that kind of growth. `providers/github/provider.py` adds `GitHubProvider`,
  which composes them and is the only class instantiated outside this
  subpackage.
- `providers/base.py` — `ProviderCapabilities` (the four flags from the
  brief) and `BaseProvider`, the contract every provider implements
  (`create_remote_repo`, `fetch_identity`, `build_api_client`, plus the
  auth-endpoint properties below). `GenericProvider` extends it: all
  capabilities `False`, `build_api_client()` returns `None`,
  `create_remote_repo()` raises `NotImplementedError` with the
  paste-a-URL instruction text.
- `providers/gitlab.py` — stub per spec: `supports_device_flow=True` (R5.2),
  everything else `False`, every method raises `NotImplementedError`.
- `providers/__init__.py` — `get_provider_class()` / `get_provider()`
  registry; unknown ids fall back to `GenericProvider` (the base case, not
  an error). This is the only place outside `providers/` that imports the
  concrete provider classes — the choke point the "do not leak provider
  conditionals" constraint asked for.
- **Auth endpoint ownership (R5.1):** GitHub's OAuth endpoints and client id
  moved from `auth/config.py` into `providers/github/provider.py` as
  `GitHubProvider` class-level config; `auth/config.py` now re-exports the
  same names from there so `ui/github_auth.py` and
  `providers/github/identity.py` didn't need to change. `GitLabProvider`'s
  endpoint properties raise `NotImplementedError` (no endpoints exist yet
  to own).
- **Per-repo provider selection (R5.3):** `core/provider_config.py`,
  mirroring the `.freecad-pdm/config.json` pattern (independently of G3's
  `storage_mode.py`, since the branches haven't merged — same file, disjoint
  keys, ordinary merge). Missing/malformed config defaults to `"github"`,
  never anything else — every repo GitPDM has ever created predates this
  field. `core/services.py` gained `provider_for_repo()` /
  `api_client_for()`; `github_api_client()` stays as a backward-compatible
  wrapper so existing callers are unchanged.
- **UI (capability-gated, not provider-gated):** `ui/new_repo_wizard.py`
  gained a provider-choice page ahead of the existing input page; GitHub is
  disabled there (not hidden — with an explanatory hint) when no API client
  is available, never a hard block on opening the wizard at all
  (`panel.py:_on_new_repo_clicked` no longer forces a GitHub connection
  before opening it). The progress page branches once on
  `provider.capabilities.supports_repo_creation`: the GitHub path now calls
  `provider.create_remote_repo(...)` instead of importing
  `create_user_repo`/`CreateRepoRequest` directly; the generic path skips
  straight to local init using the pasted remote URL. Both paths persist the
  chosen provider via `provider_config.set_provider_config()` on success.
  `ui/repo_picker.py`'s "clone from URL" section (already provider-agnostic
  in spirit) now accepts any well-formed git URL, not just GitHub's, and
  records `"github"` vs `"generic"` on the cloned repo based on the host.
- **Rename sweep (R4.3):** narrower than the brief implied — `docs/README.md`'s
  title was already "Git-based Product Data Management for FreeCAD" from an
  earlier pass, so no title change was needed. Repo topics are a GitHub
  project setting, not code; left as a manual follow-up. UI strings were
  updated where the provider is genuinely variable (repo picker's URL
  section); GitHub-specific flows that only GitHub supports (the device-flow
  dialog, OAuth connect/disconnect) still say "GitHub" on purpose — capability
  flags decide whether they're offered, not their wording.
- **Forcing test:** `tests/test_generic_provider_flow.py` — `git init --bare`
  as the remote, `GenericProvider` end to end (configure → clone → save →
  commit → push) via `GitClient`, with `urllib.request.urlopen` patched to
  raise `AssertionError` if ever called. Plus `tests/test_providers.py`
  (registry, capability flags per provider, `auth/config.py` backward
  compatibility) and `tests/test_provider_config.py` (defaults, malformed
  JSON, unknown ids, key preservation). 190 tests pass; ruff, format check,
  and the architecture guard are all clean.

---

**Multi-provider hosts as built** (`multi-provider-hosts` branch off `dev`,
2026-07-18 — GitLab, Bitbucket, Gitea/Forgejo, SourceHut join GitHub with
real radio-button workflows, per explicit user request; extends G4's
provider abstraction rather than being its own numbered phase):

- **`providers/shared/`** (new): `http_client.BaseApiClient` — the retry/
  backoff/circuit-breaker skeleton generalized from `GitHubApiClient`,
  with one bug fixed rather than replicated (GitHub's client took a `host`
  constructor arg but hardcoded `api.github.com` in its URL resolution
  instead of using it; this one actually uses `self._base_url`, which
  matters once it varies per host). `errors.ProviderApiError` — same
  6-field shape as `GitHubApiError` (code/message/status/retry_after_s/
  rate_limit_reset_utc/details), deliberately **not** a shared base class
  with it (avoids any risk to GitHub's working error handling — callers
  that need to catch "any provider's error" list both explicitly as a
  tuple). `cache.ApiCache`/`rate_limiter.RateLimiter` — relocated verbatim
  from `providers/github/`, since neither ever contained GitHub-specific
  logic; `providers/github/cache.py`/`rate_limiter.py` are now 3-line
  re-export shims so existing imports keep working, singleton identity
  confirmed unchanged across both import paths.
- **`providers/base.py`** gains `display_name`, a provider-neutral
  `RepoInfo` (moved from `providers/github/repos.py`, which re-exports
  it), `list_repos()` on the `BaseProvider` contract, and three new
  `ProviderCapabilities` flags: `requires_manual_token` (PAT-paste auth,
  independent of `supports_device_flow`), `requires_host_url` (Gitea/
  Forgejo only — self-hosted, no fixed `default_host`), `requires_workspace`
  (Bitbucket only — repos live under a workspace, not "your account").
  `build_api_client()`/`create_remote_repo()`/`list_repos()` all gained
  optional `host=`/`workspace=`/`cache_key_user=` parameters threaded
  through every provider's glue method (including GitHub's, one-line
  additive changes) for a uniform call shape the wizard/picker rely on.
- **`providers/gitlab/`, `providers/gitea/`, `providers/bitbucket/`,
  `providers/sourcehut/`** — each a full subpackage mirroring
  `providers/github/`'s shape (`provider.py`, `api_client.py`,
  `create_repo.py`, `repos.py`, `errors.py`, plus `identity.py` where
  relevant), built on `providers/shared/`. Host-specific facts, all
  verified live except SourceHut's (see below): GitLab uses
  `PRIVATE-TOKEN` auth + `X-Next-Page` pagination + unprefixed
  `ratelimit-*` headers; Bitbucket uses `Authorization: Bearer` +
  workspace-scoped URLs (`/repositories/{workspace}/{slug}`) + nested
  `links.clone[]`/body-embedded `next`-URL pagination; Gitea/Forgejo uses
  `Authorization: token` + a user-supplied server URL + GitHub-compatible
  field names and Link-header pagination (closest to GitHub's shape by
  design — Gitea's API deliberately mirrors GitHub's); SourceHut is
  GraphQL (`POST https://git.sr.ht/query`, one endpoint, cursor
  pagination) rather than REST — structurally different enough that its
  client overrides `_resolve_url()` to always return the single endpoint
  and adds a `graphql()` wrapper surfacing query-level `errors` arrays.
  `providers/gitlab.py`'s old capability-flagged stub file was deleted and
  replaced by the `providers/gitlab/` subpackage (`supports_device_flow`
  changed `True`→`False` on the way — the old stub's flag was
  forward-looking for GitLab 17.9+'s real device-flow support, but GitPDM
  has no registered OAuth app for GitLab, so claiming the capability
  without a working implementation would have been misleading;
  `requires_manual_token=True` reflects what's actually built).
- **SourceHut's schema is unverified against the live API** — its GraphQL
  endpoint requires `Authorization: Bearer` even for schema introspection
  (confirmed live: a fully unauthenticated introspection query still
  returns "Authorization header is required"), so the mutation/query field
  names (`createRepository`, `me.repositories(cursor)`, the `Visibility`
  enum, `canonicalName`) are built from SourceHut's public GraphQL API
  documentation only. Flagged prominently in
  `providers/sourcehut/__init__.py`'s module docstring and every
  submodule's docstring. **Outstanding, tracked here explicitly** (mirrors
  G1's docker-acceptance-run precedent): needs a real-token pass — create
  a repo, list repos, verify identity against a real git.sr.ht account —
  before being trusted in production.
- **`ui/new_repo_wizard.py`**: `_ProviderPage`'s two hardcoded GitHub/
  Generic radios became a data-driven loop over
  `providers.list_provider_ids()` in a `QButtonGroup` (GitHub first, then
  every other named host, generic last as the catch-all). `_InputPage`
  gained conditionally-shown PAT/server-URL/workspace fields alongside the
  existing name/visibility/description and remote-URL fields.
  `_ProgressPage` now builds the API client *inside* the wizard for
  PAT-paste hosts (from the token/URL just entered) instead of always
  reusing a pre-built client, and added an explicit "Verifying token…"
  step (via `provider.fetch_identity()`) before any filesystem/repo work,
  so a bad token fails fast with a clear message.
- **`ui/repo_picker.py`**: `RepoPickerDialog` gained a `provider=`
  parameter (defaults to `GitHubProvider()` for backward compatibility);
  repo listing dispatches through `provider.list_repos(...)` instead of a
  direct GitHub import; a conditional workspace field for Bitbucket.
  `_save_cloned_provider()` now takes an explicit `provider_id` for the
  table-clone path (the provider is known for certain there) and only
  falls back to URL-sniffing — extended to recognize gitlab.com/
  bitbucket.org/git.sr.ht — for the paste-URL path, where any host is
  valid regardless of which provider the dialog was opened for. The
  "cached Ns ago" status suffix was removed rather than reproduced
  per-provider: the underlying cache-key host strings aren't uniform
  across providers, and reproducing that mapping in the UI layer would
  mean branching on `provider_id` there, which this codebase's own
  convention says never to do.
- **`core/settings.py` / `core/services.py`** (the correctness fix
  underneath all of the above): `core/services.py`'s
  `api_client_for(provider)` accepted a `provider` argument but always
  read GitHub's global `load_github_host()`/`load_github_login()`
  regardless — connecting a second provider would have resolved
  credentials against GitHub's slot instead of its own. Fixed by
  `core/settings.py` gaining provider-namespaced connection-state
  functions (`save_provider_connected(provider_id, ...)` etc., keyed by an
  explicit prefix map so GitHub keeps its exact original parameter-store
  keys — zero migration for existing users, verified in
  `tests/test_provider_settings.py`'s backward-compat test class) and
  `api_client_for()` resolving through those instead. Caught by a new
  test (`tests/test_services.py`) asserting two different providers
  resolve to two different tokens via two different lookups — this test
  would have failed against the pre-fix code.
- **`ui/pat_auth.py`** (new): `PatAuthHandler`, the PAT-paste equivalent of
  `ui/github_auth.py`'s `GitHubAuthHandler` — meaningfully simpler (no
  device code, no polling, no browser handoff). Every method takes an
  explicit `provider_id` since more than one of these hosts can be
  connected at once. `ui/panel.py` gained one consolidated "Other Git
  Hosts" section (host dropdown + conditional server-URL/PAT fields +
  Connect/Disconnect/Browse Repos buttons) rather than four more
  GitHub-style sections, which would have kept growing the already-largest
  file in the codebase further. Deliberately did **not** touch the
  existing "Start New Project" button/flow — the wizard is already fully
  self-sufficient for all five providers (PAT entry happens inline), so
  this section's real value is enabling the repo *picker* (browsing
  *existing* repos), which does need a persisted, reusable connection.
- **Deferred, not done**: `auth/keys.py`'s `credential_target_name()`
  doesn't add an explicit provider-id segment to the OS-credential-store
  key (two different self-hosted forges sharing an exact hostname is
  vanishingly unlikely in practice — that would require the same DNS
  name). Fixing it properly means extending the `TokenStore` ABC and all
  four per-OS backends with real backward-compat handling for
  already-stored GitHub tokens — real scope, not load-bearing for this
  feature to work correctly, noted rather than silently dropped.
- No new dependencies (confirmed via `pyproject.toml` and a full read of
  `providers/github/*`): every new provider follows the existing
  stdlib-only `urllib.request` pattern, no `requests`.
- `tools/architecture_baseline.json`: `panel.py` bumped 2650 → 2850 (this
  file keeps growing with every phase; a real split-up pass is overdue
  rather than another repeated limit bump, not done here).
- `tools/provider_endpoint_smoke.py` (new): a cheap, no-token-needed live
  check that GitLab/Bitbucket/Gitea(via Codeberg)/SourceHut's endpoints
  are still reachable and return the expected error shape — catches host
  API drift early, doesn't prove full correctness (see SourceHut caveat
  above).
- 377 tests pass (85 new across this work); ruff, format check, and the
  architecture guard are all clean. No Qt-widget-layer tests were added
  for `new_repo_wizard.py`/`repo_picker.py`/`panel.py`/`pat_auth.py`
  changes — this codebase has zero existing precedent for testing Qt
  widget classes directly (confirmed: no PySide6/PySide2 installed in the
  development environment either), so UI changes need manual verification
  in a real FreeCAD environment before merge — not yet done, tracked as
  outstanding alongside the SourceHut real-token pass.

---

**Bottom-dock UI simplification as built** (`dev` working tree, 2026-07-18 —
per explicit user request; doesn't map onto a G-numbered phase, same as the
multi-provider hosts work above which it follows directly):

- **Ask:** collapse the tall right-side sidebar into a short strip docked at
  the bottom of the FreeCAD window (like Report view/Python console),
  showing only a repository header, a simple pending-changes/sync-status
  row, and the action buttons; move credentials and other dense/rarely-used
  controls into the "Git PDM" top menu-bar dropdown; and use FreeCAD's own
  save-time embedded thumbnail for the file browser's click-to-preview
  instead of requiring the manual "Generate Previews" export first. A
  follow-up request removed the collapse/expand toggle entirely and made
  Repository/Status/Actions share one row of columns instead of stacking,
  and un-nested the three repo-switch buttons (Browse/Join/Start New) back
  out from behind a dropdown since they're reached for often.
- **`ui/panel.py`:** `GitPDMDockWidget`'s content is now three columns
  sharing one `QHBoxLayout` row (`columns_row`, stretch factors 3/2/4) —
  Repository (bold repo name, path field, and three always-visible
  Browse…/Join Team…/New Project… buttons), Status (a pending-changes chip
  and a sync-status chip; branch/upstream/last-checked/storage-mode still
  update live but are no longer laid out on screen, surfacing instead as
  composed tooltip text via `_refresh_status_chip_tooltips()`), and Actions
  (fetch/pull/stage-all on one row — Open Browser was here too until the
  2026-07-19 file-browser removal, see below — then the commit message +
  Commit & Push). The pending-changes chip is a `QToolButton` popping the
  existing changes list via a `QWidgetAction`-wrapped popup rather than a
  permanently visible list widget. The collapse/expand toggle
  (`_set_compact_mode`, `_on_compact_clicked`, the compact mini-commit row)
  was removed outright — `hasattr()` guards already present elsewhere
  (`ui/commit_push.py`) degrade gracefully now that those widgets no longer
  exist, so no other file needed changes. No widget attribute names that
  `branch_ops.py`/`commit_push.py`/`fetch_pull.py`/`repo_validator.py`
  reach into by name were renamed or retyped (confirmed via grep before
  starting) — only container/layout/visibility changed, since none of that
  surface has pytest coverage (the 25 test files are all backend/provider
  logic, zero UI-internals tests) and a live-FreeCAD manual pass is the only
  real verification available.
- **`ui/connections_dialog.py`** (new): the GitHub Account and Other Git
  Hosts sections, moved out of `panel.py` verbatim into a standalone,
  non-modal `ConnectionsDialog`, opened from the GitPDM menu
  (`panel.open_connections_dialog()`). Constructed eagerly (hidden) inside
  `GitPDMDockWidget.__init__`, same as before, so `GitHubAuthHandler`'s
  startup connection checks keep firing against real widgets regardless of
  the dialog's visibility. `ui/github_auth.py`/`ui/pat_auth.py` needed
  **zero code changes** — they already address their parent generically as
  `self.panel.<attr>`, so pointing that at the dialog instead of the dock
  widget just worked.
- **`ui/label_style.py`** (new): `_set_meta_label`/`_set_strong_label`'s
  bodies extracted to plain functions so both `panel.py` and
  `connections_dialog.py` style status labels identically without
  duplicating the stylesheet strings.
- **`export/thumbnail.py` + `ui/file_browser.py`:** new
  `read_embedded_thumbnail(fcstd_path)` opens the `.FCStd` zip and returns
  the PNG FreeCAD embeds at save time (when "Create new thumbnail when
  saving the document" is enabled — the default), matched case-insensitively
  by folder+extension rather than one hardcoded path since exact casing
  hasn't been confirmed across FreeCAD versions. `file_browser.py`'s
  `show_preview()` tries this first; only falls back to the old
  deterministic manual-export PNG lookup (unchanged — it still feeds the
  GitHub-facing docs gallery manifest, a different consumer with different
  requirements) when no embedded thumbnail exists. **Not live-verified**
  (same caveat class as SourceHut's schema, flagged the same way): needs a
  real FreeCAD save with the thumbnail preference on to confirm the exact
  embedded zip path/casing before this is trusted end-to-end.
  **Superseded 2026-07-19** (see below): the "manual-export PNG" path this
  bullet describes as a separate consumer was itself found to be the
  problem — deprecated in favor of embedded thumbnails everywhere. The zip
  path/casing question above is still open, unrelated to the `package.xml`
  XML bug the user hit in the same real-FreeCAD session (that was purely
  an Addon Manager metadata parse error, not evidence either way about
  whether `read_embedded_thumbnail()`'s zip-path assumptions hold against
  a real save) — still needs an explicit check that the rendered preview
  image looks right end-to-end.
  **`ui/file_browser.py` deleted outright, same date, per explicit user
  request:** its "Repository Browser" `QDockWidget` was created eagerly at
  panel construction (`ensure_browser_host()` called unconditionally from
  `panel.py`'s buttons-section build) and added to the main window's left
  dock area, tabbed with Tree view — meaning it occupied real screen space
  on every session start, not just when explicitly opened. User's framing:
  redundant with the OS's own file explorer for browsing/opening files,
  and its click-to-preview thumbnail was itself just the same embedded PNG
  Explorer/Finder already show as the file's icon — screen space spent on
  functionality the OS provides for free. Removed: the dock, its file
  list/search/filter, click-to-preview, double-click-to-open, "reveal in
  file manager" context action, the "Open Browser" panel button, and the
  `GitPDM_OpenRepoBrowser` menu command. **Also removed, not rehomed:**
  per-file backup-count configuration (max `.FCBak` files kept), the one
  genuinely GitPDM-specific feature the browser's context menu offered —
  it now always uses `move_fcbak_to_previews()`'s hardcoded default (3)
  with no UI to change it; flagged here rather than silently dropped in
  case it's wanted back in a different home later. `export/thumbnail.py`'s
  `read_embedded_thumbnail()` (unchanged) now has exactly one caller,
  `export/exporter.py`. **Found and fixed a real, pre-existing, unrelated
  bug while doing this:** `ui/branch_ops.py`'s
  `refresh_after_branch_operation()` called
  `self._parent._refresh_repo_browser_files()`, a method that hadn't
  existed on `GitPDMDockWidget` since `29c8659` ("Refactor of all the code
  to not have 5k line files", 2025-12-29) — that refactor deleted the
  method definition and three of its four call sites, but missed the
  fourth (the one that later became `branch_ops.py`'s
  `refresh_after_branch_operation()` in `d0ef984`'s extraction). Every
  branch switch/create/delete since 2025-12-29 has been hitting an
  unhandled `AttributeError` at the tail end of that method, after the
  actually-useful work (branch label, branch list, status refresh)
  already completed — confirmed via `git log -S`, not guessed. Removed
  the dead call outright rather than restoring the old method, since
  there's no browser left for it to refresh.
- **`export/exporter.py` (2026-07-19, found and fixed per explicit user
  report from a real FreeCAD session):** `export_active_document()`'s
  thumbnail step used to be a custom render — deterministic camera/
  projection/draw-style setup (`set_view_for_thumbnail`) then a viewport
  screenshot with a pixel-by-pixel transparent-background pass
  (`save_thumbnail`) — run synchronously on FreeCAD's main thread via
  `ui/panel.py`'s `_schedule_auto_preview_generation()` after **every**
  save. Two problems, both raised by the user directly: it blocked the UI
  (no progress feedback, unlike the explicit "Generate Previews" button's
  modal dialog — the user just froze), and it duplicated a snapshot
  FreeCAD already takes itself at save time (the same embedded thumbnail
  `read_embedded_thumbnail()` above already reads for the local
  file-browser preview). Fixed by having `export_active_document()`'s
  thumbnail step call `read_embedded_thumbnail()` and write those bytes
  straight to the committed `preview.png`, for both the automatic
  on-save trigger and the manual "Generate Previews" button (both share
  this one function) — not just the auto-trigger, since the user's framing
  was "deprecate the snapshot we implemented," not "only fix the blocking
  case." `set_view_for_thumbnail`/`save_thumbnail` deleted outright (zero
  other callers, zero existing test coverage). New
  `tests/test_thumbnail.py` covers `read_embedded_thumbnail()` directly
  (case-insensitive matching, backslash paths, missing/malformed zip) —
  `export_active_document()` itself still has no test coverage (FreeCAD-
  GUI-dependent, pre-existing gap, not introduced by this fix).
  **Consequence, documented in `docs/README.md`:** `preset.json`'s
  `thumbnail` sub-block (size/projection/view/background/showEdges) is
  still accepted (harmless, not removed from `preset.py`'s schema or
  `core/scaffold.py`'s default template — out of scope for this fix) but
  no longer affects anything; thumbnail framing is now whatever the user's
  FreeCAD viewport looked like at their own last save, not a
  preset-controlled deterministic shot. This trades per-part visual
  consistency in the GitHub-facing Part Glossary for removing the
  duplicated, blocking render — a real tradeoff, not a strict improvement,
  but the one the user explicitly chose.
- **`commands.py` + `InitGui.py`:** the panel now docks at
  `BottomDockWidgetArea`, tabbed with "Report view"/"Python console" when
  present (falls back to a plain dock add otherwise — same fallback shape
  already used for Tree view/Tasks). A shared `_find_or_create_dock()` /
  `_show_dock()` pair in `commands.py` is used by every command and by
  `InitGui.py`'s auto-open, so the two entry points can't disagree on
  layout. Seven new commands (`GitPDM_Connections`,
  `GitPDM_GeneratePreviews`, `GitPDM_OpenPreviewFolder`,
  `GitPDM_ToggleStagePreviews`, `GitPDM_ChangeStorageMode`,
  `GitPDM_DeepenHistory`, `GitPDM_OpenRepoBrowser`) are thin entry points
  into logic that already lived on the panel/handlers — no new business
  logic. The "Git PDM" menu (a workbench's top-level menu-bar entry — this
  *is* the "top toolbar GitPDM dropdown" from the request) is now sectioned
  with separators; the toolbar itself was trimmed to just Toggle Panel +
  Save Into Repo, the two frequent one-click desktop actions.
- **Not done, deliberately:** the already-hidden "System" (git availability)
  and "Branch" (new/switch/delete work version) sections stay hidden exactly
  as before — not resurfaced, no menu entries added, since the request
  didn't ask for them back. The Sprint 7 one-click "Publish" flow
  (`_on_publish_clicked`/`_run_publish_workflow`) was already unreachable
  from any visible button and stays that way.
- `tools/architecture_baseline.json`: `ui/file_browser.py` bumped 850 → 900
  for the embedded-thumbnail-first/manual-fallback split in `show_preview()`
  (~874 lines). `ui/panel.py` actually **shrank** (2795 → ~2473 lines)
  despite the new column layout, since the GitHub/Other-Hosts sections and
  their handler-wiring methods moved out to `connections_dialog.py`.
- 377 tests still pass (no new tests — same "zero precedent for testing Qt
  widget classes directly" situation noted under G4/multi-provider hosts);
  ruff, format check, and the architecture guard are all clean. Manual
  verification in real FreeCAD is still outstanding for: the bottom-dock
  visual layout (whether three columns stay legible at typical dock widths),
  the GitPDM menu's new sectioned entries, and — most importantly — the
  embedded-thumbnail zip path/casing above.

---

**Toolbar consolidation + left-dock default, as built** (`dev` working
tree, 2026-07-19, two explicit user requests in the same session, both
unverified against a real FreeCAD/Qt install since neither PySide6 nor
PySide2 is importable in this environment — ruff, the architecture guard,
and the full pytest suite (413 passed) all stayed clean throughout, but a
real-FreeCAD manual pass on both is still outstanding):

- **Request 1 — shrink the columns further:** the repo name was taking up
  too much space and rendering in low-contrast black; the Status column
  cost a whole column for two chips that could sit next to the name; the
  Actions column was the widest and didn't adapt to a narrow dock.
  - `ui/label_style.py`: new `ElidedLabel` (single-line, `...`-truncated to
    whatever width it's given, full text always in the tooltip) and
    `REPO_NAME_ACCENT` (`#4aa8ff`) — a legible accent distinct from the
    existing green/orange/red/gray/`#4db6ac` semantic status colors, so the
    repo name never reads as a status signal.
  - `ui/panel.py`: `_build_repo_selector` now builds `repo_name_label` as an
    `ElidedLabel` and folds in a header row with the pending-changes/sync
    chips (`working_tree_label`, `ahead_behind_label`, `operation_status_label`)
    right next to it — the standalone `_build_status_section` method and its
    own `QGroupBox`/`_group_status` are gone, merged into one "Repository"
    group. `columns_row` is now 2 columns (Repository, Actions; stretch 5/4)
    instead of 3. Every widget attribute name existing call sites reach into
    (`repo_validator.py`, `fetch_pull.py`, `branch_ops.py`, `commit_push.py`)
    is unchanged — only the container/layout changed.
  - Dynamic reflow: `columns_row`, `switch_row` (Browse…/Join Team…/New
    Project…), and Actions' `row1_layout` (Check for Updates/Get
    Updates/checkbox) are built as `QBoxLayout` instead of a fixed
    `QHBoxLayout`, collected in `self._responsive_layouts`.
    `GitPDMDockWidget.resizeEvent()` → `_maybe_update_layout_orientation()`
    compares the dock's own width/height (with hysteresis so it doesn't
    flap near-square) and `_apply_layout_orientation()` flips all of them
    between `LeftToRight` (wide/short dock) and `TopToBottom` (narrow/tall
    dock) via `QBoxLayout.setDirection()` — no widget tree rebuilding
    needed. Any future toolbar-like button row should follow the same
    pattern rather than a fixed `QHBoxLayout`.
- **Request 2 — default dock location:** the user tried the panel in
  several dock spots and sent a screenshot identifying the left dock area's
  bottom-left corner (tabbed with Report view/Python console, below Tree
  view) as the best default — least screen space, good legibility, and the
  same responsive layout above already handles the narrow-width case.
  - `commands.py`'s `_find_or_create_dock()` (the single place both it and
    `InitGui.py`'s auto-open funnel through) now calls
    `mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)` instead of
    `BottomDockWidgetArea`, still tabifying with Report view/Python console
    by name when either is present. When neither is present the dock still
    lands in the left area on its own (typically its own split below Tree
    view) rather than falling back to the old bottom placement.
  - `docs/README.md`'s Tutorial 1 step 1 updated to say "left dock area"
    instead of "the bottom of the window."

---

**Seamless recovery-checkpoint restore, as built** (`dev` working tree,
2026-07-19, per explicit user report: a real-world test — edit a part, wait
for a checkpoint to fire, force-quit FreeCAD without saving — left the user
unable to find the recovered work locally even though the `gitpdm/recovery`
branch on GitHub had it. Not live-verified against a real FreeCAD/Qt install
for the same reason as the toolbar-consolidation pass above; tests/ruff/the
architecture guard all stayed clean):

- **Root-cause analysis (code-read, not live-reproduced):** the
  restore-on-start offer already existed (`_maybe_offer_recovery_restore`,
  G6/R2.5) but had two gaps that plausibly explain the report. (1) It only
  ever fires once, ~200ms after a repo is *activated* in the panel, and
  silently does nothing — no message, no retry later — if a document from
  the repo happens to already be open at that exact moment (the same
  "documents must be closed" safety guard branch-switching uses). A user
  who reopens their file via Recent Files around the same time as FreeCAD
  auto-loading GitPDM's saved repo path could easily race past the one-shot
  window with no second chance. (2) Even a successful restore only wrote
  bytes to disk via `git checkout <sha> -- .`; it never told the user
  which file to reopen or reopened it for them, so "recovered" still meant
  hunting through the repo folder manually — the opposite of "seamless."
- **`ui/repo_validator.py`:** `_maybe_offer_recovery_restore` generalized
  into `offer_recovery_restore(repo_root, interactive_when_unavailable)`,
  shared by the automatic one-shot offer (`interactive_when_unavailable=
  False`, unchanged silent behavior when there's nothing to do) and a new
  on-demand entry point (`interactive_when_unavailable=True`) that reports
  *why* nothing happened ("No Recovery Checkpoint" / "Close Your Documents
  First") instead of doing nothing, so a user who explicitly asks isn't
  left guessing. Prompt wording changed to the user's own suggested framing
  ("Your latest file save appears to be older than a recovery version…").
  New `_reopen_after_recovery_restore()`: after a successful restore, reads
  `settings.load_last_checkpoint_file()` and, if it's still inside the repo
  and present on disk, calls `FreeCADGui.openDocument()` on it directly —
  no precedent for GitPDM programmatically opening a document existed
  before this (the clone/create flow only ever offers "Open Folder" in
  Explorer, since it doesn't know which of possibly-several files is
  relevant); recovery is the one case where the exact file is known, so
  auto-opening it is the more "seconds, not minutes" behavior the report
  asked for. Falls back to opening the repo folder in Explorer (reusing
  `ui/panel.py`'s existing `_open_folder_in_explorer`) if the path is
  unknown or `openDocument()` itself fails.
- **`core/settings.py`:** new `save_last_checkpoint_file()` /
  `load_last_checkpoint_file()`, following the existing single-value
  global-setting pattern (`save_last_preview_at` etc.). Persisted rather
  than kept in memory because the whole point is surviving the crash the
  feature exists for — FreeCAD's in-memory `ActiveDocument` is gone by the
  time the next session needs to know what to reopen.
- **`ui/panel.py`:** `_save_active_document_if_dirty()` (the checkpoint
  scheduler's injected save step) now calls `settings.save_last_checkpoint_
  file(doc.FileName)` right after `doc.save()` succeeds, so the path is
  always fresh as of the most recent real checkpoint. New
  `_restore_recovery_checkpoint_clicked()`, the on-demand command's panel
  entry point, delegating to `offer_recovery_restore(...,
  interactive_when_unavailable=True)`.
- **`commands.py` + `InitGui.py`:** new `GitPDM_RestoreRecoveryCheckpoint`
  command ("Restore Recovery Checkpoint…"), added to the "Git PDM" menu
  right next to the existing "Clear Recovery Checkpoint" — same
  find-or-create-dock-then-delegate pattern as every other menu command
  here.
- **What this doesn't change:** the underlying checkpoint mechanism itself
  (idle-debounce + max-interval backstop, `commit_recovery_checkpoint`'s
  git plumbing, the busy-guard) is untouched — this pass is entirely about
  making an *existing*, already-correct checkpoint easier to actually get
  back once something interrupts the session, not about capturing more or
  differently. `tools/architecture_baseline.json`: `ui/repo_validator.py`
  bumped 650 → 720 for the generalized restore flow (~686 lines).

---

**Checkpoint `save_ok` tracking + visible feedback, as built** (`dev`
working tree, 2026-07-19, same day, per an immediate follow-up user report
after testing the restore flow above: edited a part, waited for a
checkpoint, confirmed it reached `gitpdm/recovery` on GitHub, started a new
FreeCAD session, ran the restore — and the file it opened was still the
*pre-edit* version. Also not live-verified, same caveat as the two passes
above):

- **Root-cause analysis (code-read, not live-reproduced — the strongest of
  several candidate explanations considered):** `run_checkpoint()` calls
  `save_if_dirty()` (FreeCAD's real `doc.save()`) and then unconditionally
  commits whatever is on disk to `gitpdm/recovery`, regardless of whether
  that save actually succeeded — `_save_active_document_if_dirty()`
  swallowed any `doc.save()` exception in a bare `except Exception: log.
  debug(...)`. If the save silently failed for any reason, the commit that
  followed would still succeed as pure git plumbing (`write-tree`/
  `commit-tree`/`update-ref` don't care whether the file changed), just
  re-snapshotting the same stale, pre-edit content already on disk. From
  the outside — and from GitHub — that's indistinguishable from a real,
  edit-capturing checkpoint: both are just "a new commit landed on
  `gitpdm/recovery`." A restore of that commit would then correctly write
  back exactly the content that was already there, which is precisely the
  "restored file is pre-edit" symptom reported, with zero bug needed in the
  restore path itself (verified separately: `_get_all_open_fcstd_documents()`
  checks *all* open FreeCAD documents process-wide before the restore-then-
  reopen sequence runs, so a stale in-memory document being silently reused
  by `FreeCADGui.openDocument()` instead of re-read from disk was ruled out).
- **`core/checkpoint.py`:** `save_if_dirty`'s type changed from
  `Callable[[], None]` to `Callable[[], bool]` — callers must now report
  whether the save genuinely happened (or there was nothing to do) versus
  attempted-and-failed. New `CheckpointResult.save_ok: bool = True`,
  populated from that return value and surfaced regardless of whether the
  commit landed (`ok=True` and `save_ok=False` is now a valid, meaningful
  combination, not previously representable). `run_checkpoint()`'s and
  `CheckpointResult`'s docstrings both spell out why this distinction
  matters. New tests: `test_save_failure_still_commits_but_flags_save_ok_
  false` plus updated fakes across `TestRunCheckpoint` (now explicit
  `lambda: True` / a `fake_save()` returning `True` instead of implicitly
  returning `None`, so the new field's semantics are exercised rather than
  incidentally defaulted).
- **`ui/panel.py`:** `_save_active_document_if_dirty()` now returns `True`
  for both no-op cases (nothing to save) and a successful save, `False`
  only when `doc.save()` raises — and logs that failure at `warning`
  instead of `debug`, so it shows up in Report View by default rather than
  requiring debug logging to be turned on. `_on_checkpoint_timer_tick()`
  branches on `result.save_ok`: a genuine checkpoint logs at debug as
  before *and* now shows "Checkpoint saved HH:MM:SS" (green) in the
  operation-status chip next to the repo name; a commit whose underlying
  save failed logs a `warning` and shows "Checkpoint save issue — see
  Report View" (red) instead of looking identical to a normal success. New
  `_show_checkpoint_feedback()` helper, self-clearing back to "Ready" after
  4s via the existing `_set_ready_later()` mechanism other transient
  operations already use. This closes the gap the user's report actually
  named: *"waited for the checkpoint to fire"* previously had no visible
  confirmation at all — a user could only infer timing from elapsed
  seconds, with no way to tell a real checkpoint from a silently-broken one
  short of diffing files by hand.
- **`ui/repo_validator.py`:** `_reopen_after_recovery_restore()` now takes
  the restored commit's SHA and includes its short form in every
  confirmation message (both the "reopened" and "opened the folder"
  paths), so if the working tree still doesn't look right after a restore,
  the user has the exact commit to check (`git show <sha>:<path>` or
  GitHub) rather than just "a restore happened, trust it."
- **What this doesn't change:** `commit_recovery_checkpoint()`'s git
  plumbing itself is untouched — a checkpoint still always commits
  *something* even when the underlying save failed (a stale checkpoint
  beats none, same philosophy as before); this pass is entirely about
  making that distinction visible rather than changing when a commit
  happens.

---

**Non-destructive recovery export + crash-safe marker, as built** (`dev`
working tree, 2026-07-19, same day, second immediate follow-up: the user
re-tested the restore flow above and reported three things at once — (1)
clicking Yes on the restore prompt opened Windows Explorer with no further
prompt, (2) it opened at the repo root rather than anywhere specific to the
CAD folder, and (3) the actual `.FCStd` file was still the pre-checkpoint
version. Also not live-verified, same caveat as the passes above):

- **Root-cause analysis (code-read, not live-reproduced):** (1)+(2) trace
  to `_reopen_after_recovery_restore()` falling through to its
  open-the-repo-folder fallback, which only happens when
  `settings.load_last_checkpoint_file()` comes back empty — and that
  function persisted through FreeCAD's parameter store
  (`FreeCAD.ParamGet(...).SetString(...)`), which is **not** guaranteed to
  reach disk except on a clean shutdown. A force-quit is exactly the
  unclean-shutdown case this whole feature exists for, so the marker this
  pass's predecessor (the "seamless recovery" work earlier the same day)
  added to solve "which file do I reopen" was itself not crash-safe —
  `core/session_lock.py` already avoids the parameter store for its own
  lock file for precisely this reason, a precedent this pass's fix should
  have followed from the start. (3) was separately investigated and *not*
  found to be a bug in the restore mechanism itself:
  `TestRestoreAndPrune.test_restore_from_recovery_writes_checkpointed_content`
  already proves `restore_from_recovery()`'s `git checkout <sha> -- .`
  correctly overwrites working-tree content against a real repo, and
  `_get_all_open_fcstd_documents()` (the pre-restore safety guard) checks
  *all* FreeCAD documents process-wide, ruling out a stale in-memory
  document being silently reused instead of re-read from disk. The most
  likely remaining explanation for (3) is the same `save_ok=False` failure
  mode the previous pass added visibility for — a checkpoint whose
  underlying document save silently failed still commits *something* to
  `gitpdm/recovery`, just a no-op re-snapshot of already-stale content —
  which this pass doesn't re-litigate, only makes easier to tell apart from
  a real recovery by giving the user a concrete, checkpoint-scoped artifact
  to check against instead of trusting an in-place overwrite blindly.
- **`git/client.py`:** new `export_recovery_snapshot(repo_root,
  recovery_sha, dest_dir)` — the non-destructive companion to
  `restore_from_recovery()`. Same throwaway-`GIT_INDEX_FILE` trick as
  `commit_recovery_checkpoint()`, combined with an alternate
  `--work-tree=dest_dir` passed straight to `git checkout`, so file writes
  happen entirely inside git's own binary-safe internals (no Python-side
  `git show`/stdout-capture involved, which would have corrupted binary
  `.FCStd` content via `text=True`'s decoding — considered and rejected).
  Four new tests in `TestExportRecoverySnapshot`, including one asserting
  byte-for-byte-identical binary round-tripping and one asserting zero
  effect on the real repo's HEAD/index/working tree (same `_snapshot()`
  byte-identity helper `TestCommitRecoveryCheckpoint` already used).
- **`core/checkpoint.py`:** `export_recovery_snapshot(git_client,
  repo_root, recovery_sha=None)` wrapper (mirrors
  `restore_recovery_checkpoint()`'s shape), picking the destination as
  `.git/gitpdm-recovery/<sha8>-<timestamp>/` — inside `.git/` specifically
  so it can never be walked by a later checkpoint's `git add -A` (no
  `.gitignore` dependency needed; `.git/` is unconditionally excluded from
  git's own view of the working tree, whether or not the user's
  `.gitignore` mentions anything). New `note_last_checkpoint_file()`/
  `load_last_checkpoint_file()` replace the settings.py versions entirely
  (deleted, not deprecated) — a plain JSON file at
  `.git/gitpdm-last-checkpoint.json`, written/read with ordinary
  `open()`/`json.dump()`/`json.load()`, no FreeCAD dependency. Five new
  tests in `TestLastCheckpointFileMarker`, including a corrupted-file
  case (must degrade to `""`, not raise).
- **`ui/panel.py`:** `_save_active_document_if_dirty()` now calls
  `checkpoint.note_last_checkpoint_file(self._current_repo_root, doc.
  FileName)` instead of the settings.py version. New
  `_open_folder_in_explorer_selecting(file_path)` (Windows:
  `explorer /select,<path>`, falls back to opening the parent folder on
  other platforms or on failure) — used so landing in a recovery folder
  highlights the specific recovered file instead of leaving the user to
  guess among however many files it contains.
- **`ui/repo_validator.py`:** `offer_recovery_restore()` now runs
  `export_recovery_snapshot()` immediately after the existing in-place
  `restore_recovery_checkpoint()` succeeds (best-effort — a failed export
  is logged but doesn't undo the in-place restore that already happened).
  `_reopen_after_recovery_restore()` replaced by `_finish_recovery_restore()`
  + `_open_recovered_folder()`: if the exact file can be reopened
  automatically (via the now-crash-safe marker), the confirmation dialog
  names it *and* offers a one-click "Open Recovery Folder" button pointing
  at the export (not repo root); if it can't be reopened, Explorer opens
  directly on the export folder (selecting the specific file within it
  when the relative path can be resolved) instead of falling back to
  `repo_root` — the direct fix for complaint (2) above. `tools/
  architecture_baseline.json`: `ui/repo_validator.py` bumped 720 → 800,
  `git/client.py` bumped 2300 → 2400.
- **What this doesn't change:** the in-place `restore_from_recovery()` /
  `restore_recovery_checkpoint()` path is untouched and still runs first —
  export is additive, not a replacement, since the in-place mechanism is
  the one with direct real-git test coverage proving it works.

---

**Checkpoint save was silently a no-op — the actual root cause, as fixed**
(`dev` working tree, 2026-07-19, same day, third immediate follow-up: the
user navigated to the newly-added recovery export folder from the pass
above — proving that part of the pipeline now works — and confirmed the
file *inside it* still had the pre-edit content. Also not live-verified,
same caveat as the passes above, though this one is the most confident of
the three: it's a straightforward reading of what
`App::Document.isTouched()` actually means in FreeCAD's own object model,
not a guess about timing or persistence):

- **Root cause:** `ui/panel.py`'s `_save_active_document_if_dirty()` — the
  function `run_checkpoint()` calls to perform the real `doc.save()` before
  every checkpoint commit — had this gate: `if hasattr(doc, "isTouched")
  and not doc.isTouched(): return True`. `App::Document.isTouched()`
  reflects whether the document's **recompute dependency graph** still has
  anything pending — not "modified since the file on disk was last
  written." FreeCAD settles recompute essentially immediately after an
  edit, almost always well inside the checkpoint scheduler's 45-second
  idle-debounce window (`DEFAULT_IDLE_SECONDS`) before a tick is even
  allowed to fire. So by the time a checkpoint tick actually ran,
  `isTouched()` had very often already gone back to `False`, causing this
  function to skip the real save on the vast majority of genuine edits —
  silently, via a clean early return, not an exception, so it was
  indistinguishable from "nothing needed saving" by every signal this
  session added to detect problems, including `CheckpointResult.save_ok`
  from two passes ago (which this same function is responsible for
  reporting — from its own point of view, it correctly had nothing to
  save). The `gitpdm/recovery` commit that followed still succeeded as
  pure git plumbing either way, re-snapshotting whatever was already on
  disk (the pre-edit version) — which is exactly what both the in-place
  restore and the non-destructive export from the pass above then
  faithfully reproduced. **This was very likely not an intermittent bug**:
  given the idle-debounce window is specifically tuned to be well past
  FreeCAD's near-instant recompute settling, this gate was probably wrong
  on close to every real checkpoint since G6 shipped, not just this user's
  session — see the correction added to G6's original "as built" entry
  above, which had claimed (inaccurately, and without this specific
  behavior ever actually having been exercised) that `isTouched()` "works
  as expected."
- **`ui/panel.py`:** the `isTouched()` gate removed outright — 
  `_save_active_document_if_dirty()` now calls `doc.save()` unconditionally
  whenever there's an active document with a `FileName` already set (the
  other early-return, for a never-saved document, is untouched and still
  correct). Not a regression risk for "saving too often": the outer
  scheduler (`core/checkpoint.py`'s `should_checkpoint()`) already gates
  *whether* this function runs at all on real recent activity
  (`CheckpointState.dirty`, set by `slotChangedObject` on any property
  change — this part *was* genuinely live-verified) — the `isTouched()`
  check inside this function was always redundant on top of that, and,
  it turns out, actively wrong besides.
- **What this doesn't change:** nothing else in the checkpoint pipeline —
  `should_checkpoint()`'s scheduling, `commit_recovery_checkpoint()`'s git
  plumbing, `save_ok`/`export_recovery_snapshot()`/the crash-safe marker
  from the last two passes — needed any change; they were all working
  correctly against whatever `_save_active_document_if_dirty()` actually
  did, which was the one thing that was wrong.

---

**Recovery success path simplified — Explorer dropped from the working
case, as built** (`dev` working tree, 2026-07-19, same day, immediate
follow-up once the `isTouched()` fix above was confirmed working: the user
reported the reopened document now correctly shows the recovered content
("functionally I can get the file back open now"), and asked, reasonably,
why a File Explorer window pointed at "just a general documents folder"
was still part of the flow once the native reopen already works):

- **Context:** the export-to-folder + Explorer-surfacing machinery (two
  passes back) existed specifically because, at the time, an in-place
  restore or an automatic reopen couldn't be fully trusted — the
  `isTouched()` bug (previous entry) meant a checkpoint could silently
  contain stale content with zero indication anything was wrong, so
  showing the user a concrete, inspectable folder was the only way to give
  them real proof. Now that the underlying save bug is fixed, that
  proof-of-work burden is gone, and popping Explorer in the success case
  is just an extra window between the user and their (correctly) reopened
  document.
- **`ui/repo_validator.py`:** `_finish_recovery_restore()`'s success branch
  (the exact file reopens via `FreeCADGui.openDocument()`) no longer builds
  a multi-button `QMessageBox` offering "Open Recovery Folder" — it's a
  single, simple confirmation naming the file, full stop. `export_
  recovery_snapshot()` is still called every time (see
  `offer_recovery_restore`, unchanged) and its `.git/gitpdm-recovery/`
  folder is untouched as a concept — it's purely the *automatic surfacing*
  of it in the success case that's gone. The **fallback** path (reopen
  doesn't resolve, e.g. the marker file is missing/stale) is unchanged and
  still opens Explorer scoped to the export folder (or repo root as a last
  resort) — Explorer remains the only way to hand the user their file when
  the direct reopen genuinely can't.
- **What this doesn't change:** `export_recovery_snapshot()`,
  `note_last_checkpoint_file()`/`load_last_checkpoint_file()`, and the
  in-place `restore_recovery_checkpoint()` call are all untouched — this
  pass only removes UI surfacing in the one case (a successful reopen)
  where that surfacing had stopped earning its keep.

---

**Checkpoint history browsing, as built** (`dev` working tree, 2026-07-19,
same day, immediate follow-up: the user ran a fresh end-to-end test and
reported the CAD-folder file and the exported recovery-folder file were
identical, calling the restore prompt "virtually meaningless" as a result,
and described a mental model where the CAD folder should only change on an
explicit save while `gitpdm-recovery` builds a continuous backup history
independently. That mental model doesn't match this feature's actual,
originally-documented design — `GITPDM_REQUIREMENTS.md` R2.5 explicitly
specifies "save the document, commit to a dedicated `gitpdm/recovery`
branch" as the mechanism for the "walk away anytime, lose at most ~a
minute" guarantee, so the real file being auto-saved every checkpoint is
intentional, not a bug, and the CAD-folder/recovery-folder match the user
observed is exactly what a *working* checkpoint should produce. But the
user's underlying complaint was still valid: the branch's full checkpoint
history already exists (git never overwrites a commit; every checkpoint
this session made is still there), and nothing surfaced it — "restore" only
ever meant "restore the latest tip," which is a likely no-op once
checkpoints correctly auto-save. Asked the user to choose between (a)
keeping auto-save and adding history browsing, or (b) making checkpoints
stop touching the real file entirely (a much bigger behavior change,
removing the walk-away guarantee); the user chose (a)):

- **`git/client.py`:** new `RecoveryCheckpointEntry` dataclass (`sha`,
  `at` — ISO 8601 commit timestamp) and `list_recovery_checkpoints(
  repo_root, branch_ref=RECOVERY_REF, limit=50)`, using `git log
  <branch_ref> --not HEAD --format=%H%x1f%cI`. The `--not HEAD` is load-
  bearing, not decorative: without it, the log walk includes whatever
  commit the recovery branch originally forked from (see
  `commit_recovery_checkpoint()`'s `parent_sha` — either the prior
  checkpoint's tip or `HEAD` at the time), so a repo with 2 checkpoints
  would report 3 entries (the extra one being the shared "Initial commit"
  ancestor) — caught immediately by
  `TestListRecoveryCheckpoints.test_older_checkpoints_are_individually_
  extractable` asserting `len(entries) == 2`, which failed before the fix.
  Four new real-git tests, including one proving an *older* checkpoint
  (not just the latest) is independently restorable/exportable via its own
  SHA — the actual capability being added.
- **`core/checkpoint.py`:** `list_recovery_checkpoints(git_client,
  repo_root, limit=50)` thin wrapper, same pattern as
  `restore_recovery_checkpoint()`/`export_recovery_snapshot()`.
- **`ui/dialogs.py`:** new `RecoveryHistoryDialog` — a `QListWidget` of
  "`YYYY-MM-DD HH:MM:SS   (sha8)`" entries (newest first, newest
  pre-selected), "Restore Selected"/"Cancel" buttons, double-click as a
  shortcut for "Restore Selected". Exposes `.selected_sha` after `accept()`,
  same result-attribute convention `NewBranchDialog` already uses.
- **`ui/repo_validator.py`:** `offer_recovery_restore()` now branches on
  `interactive_when_unavailable` at the point where it used to always show
  a plain Yes/No: the on-demand "Restore Recovery Checkpoint" command
  (`interactive_when_unavailable=True`) calls new
  `_pick_recovery_checkpoint()`, which lists history and shows
  `RecoveryHistoryDialog`, falling back to the latest SHA if listing comes
  back empty (shouldn't normally happen, given `recovery_branch_status()`
  already confirmed availability) or the dialog has nothing to show. The
  automatic restore-on-start offer (`interactive_when_unavailable=False`)
  is completely unchanged — still the original fast Yes/No on
  `status.recovery_sha` (the latest tip), deliberately: browsing history
  isn't the right friction to add to the "I just crashed, get my work
  back" moment, which is the automatic offer's whole job. Whichever SHA
  gets chosen (`selected_sha`) now flows through `restore_recovery_
  checkpoint()`, `export_recovery_snapshot()`, and `_finish_recovery_
  restore()` uniformly — none of those three needed to change, they just
  stopped being hardcoded to always receive the latest tip.
  `tools/architecture_baseline.json`: `ui/repo_validator.py` bumped
  800 → 850.
- **What this doesn't change:** the underlying "walk away anytime" design
  (checkpoints still auto-save the real file, every ~45s-3min while dirty)
  is untouched, per the user's explicit choice — this pass adds a way to
  reach *past* checkpoints, it doesn't change what a checkpoint itself
  does or how often one happens.

---

**Automatic self-populating recovery-export folder, as built** (`dev`
working tree, 2026-07-19, same day, immediate follow-up: the checkpoint
history browser above worked, but the user pointed out it only ever
materialized one export when explicitly triggered through GitPDM's UI —
what they actually wanted was `.git/gitpdm-recovery/` building up
automatically as checkpoints happen, browsable directly in Explorer with
no GitPDM interaction at all, and specifically flagged that export folders
were named after when they were *exported* rather than when the checkpoint
was actually *made*, breaking chronological tracking):

- **`git/client.py`:** new `commit_timestamp(repo_root, sha)` — `git log -1
  --format=%cI <sha>` for a single commit's real committer date. Read-only,
  same pattern as `rev_parse()`.
- **`core/checkpoint.py`:** `export_recovery_snapshot()`'s folder naming
  flipped from `<sha8>-<timestamp>` to `<timestamp>-<sha8>` (plain
  alphabetical/Explorer-default sort is now chronological order for free),
  and the timestamp itself now comes from `commit_timestamp()` — the
  checkpoint's own commit time — instead of `datetime.now()` at export
  time. New `test_folder_name_uses_the_commits_own_time_not_export_time`
  proves the distinction for real (sleeps past a full second between
  committing and exporting, then asserts the folder name matches the
  commit's timestamp, not a later "now"). New `MAX_RETAINED_RECOVERY_
  EXPORTS = 30` and `_prune_old_recovery_exports()`: every successful
  export now prunes down to the N most recent by name (safe given the
  naming above) — added because automatic per-checkpoint export means
  unbounded folder growth over a long session is now a real risk (each
  export is a full checked-out copy of the tracked files, not a diff, so a
  large FCStd file times many checkpoints adds up fast). `prune_recovery_
  branch()` (already called after every real commit and from "Clear
  Recovery Checkpoint") now also `shutil.rmtree()`s the whole export
  folder tree, not just the git branch — same rationale as always applied
  to the branch: a real commit supersedes every earlier checkpoint. Four
  new tests (`TestCheckpointExportWrapperAndPruning`) covering the naming
  order, the commit-time-not-export-time behavior, the retention cap (via
  `monkeypatch.setattr(checkpoint, "MAX_RETAINED_RECOVERY_EXPORTS", 2)`),
  and branch-prune clearing the folder.
- **`ui/panel.py`:** `_on_checkpoint_timer_tick()` now calls
  `checkpoint.export_recovery_snapshot()` immediately after every
  successful checkpoint commit (silent/best-effort, `log.debug` on
  failure only — a convenience layered on an already-successful
  checkpoint shouldn't surface its own error UI on every tick). This is
  the actual behavior change the user asked for: the folder now populates
  itself continuously as you work, not only when a restore is explicitly
  requested.
- **What this doesn't change:** the explicit export call inside
  `ui/repo_validator.py`'s `offer_recovery_restore()` (added two passes
  ago) stays — not redundant, since it's what makes an *older*, possibly
  already-pruned checkpoint from the history browser exportable on demand
  even if its automatic export from earlier in the session didn't survive
  the retention cap.
- **Known trade-off, not addressed this pass:** `R2.5`'s original
  requirement text says checkpoint commit+push should run "asynchronously
  (subprocess); only the save itself touches the main thread" — in the
  actual implementation, `_on_checkpoint_timer_tick()` has always run the
  whole `run_checkpoint()` call (save, git commit, git push) synchronously
  on the Qt main thread; this was true before this pass and isn't
  something this session introduced. Adding the export step extends that
  same pre-existing blocking window a bit further (another `git checkout`
  subprocess) rather than fixing it — flagged here rather than silently
  compounding an unaddressed gap. A real fix would thread the whole
  checkpoint tick through `core/jobs.py`'s job runner, same as other
  git operations already do; out of scope for this pass.

---

## How to use this document (instructions to the implementing agent)

1. **Explore before editing.** Module names below (`freecad_gitpdm/`, `github/`, `git/`, `ui/`, `core/`, `export/`) come from the README's architecture section and may not match reality exactly. Map the actual layout first; adapt paths, preserve intent.
2. **The desktop user is sacred.** Every phase must be a no-op or an improvement for someone running GitPDM in desktop FreeCAD with a keyring. If a change alters desktop behaviour, stop and flag it.
3. **Tests must run without FreeCAD.** FreeCAD's Python API isn't pip-installable. Structure new code so business logic imports cleanly under plain pytest, with `FreeCAD`/`FreeCADGui`/`PySide` mocked or injected at the edges. UI and document-event code gets thin adapters; logic lives below them.
4. **No new hard dependencies** beyond stdlib + what GitPDM already vendors. Git operations shell out (existing pattern); HTTP uses whatever the codebase already uses.
5. **One phase = one PR.** Don't reach forward into later phases.

---

## Phase G1 — Credential engine *(BLOCKER for everything external)* ✅ IMPLEMENTED

**Implements:** R2.1, R2.1a. **Depends on:** nothing.

**As built** (`dev` @ `ceaa4f5`, 2026-07-17 — kept for reference; the brief below is the original spec):

- `auth/credential_chain.py` — `resolve_credential()` / `resolve_env_credential()` / `headless_backends_active()`; interactive rungs (device flow, PAT prompt) stay in the UI layer as planned.
- `auth/token_store_file.py` — `FileTokenStore`, constructible only under `GITPDM_ALLOW_FILE_TOKENS=1`; factory falls back to it only when the flag is set AND the OS store is unavailable.
- `TokenResponse.provider` (default `"github"`) rather than a separate `Credential` wrapper — stores serialize field-by-field with `.get()` defaults, so pre-existing stored tokens load unchanged.
- `auth/check.py` — `python -m freecad_gitpdm.auth.check`, runs without FreeCAD.
- `git/client.py:_headless_credential_args()` — bridges env tokens into `clone`/`fetch`/`pull`/`push` via an inline credential helper referencing env var names only (no token on any command line); returns `[]` on desktop so existing helpers are untouched. This item wasn't in the original brief but is required by R2.1's "authenticates and **pushes** in a container".
- `core/services.py:github_api_client()` — env credentials take precedence; desktop path unchanged.
- Refresh was already implemented but dead (see Status ledger); the wiring bug is fixed. Per-provider token URL parameterization deferred to G4 as planned.
- ~~Outstanding: the docker acceptance run~~ ✅ Verified 2026-07-17: `python:3.12-slim` container, `GITPDM_TOKEN` only (no keyring, no SSH, no `.env`), `python -m freecad_gitpdm.auth.check` → `OK — source=env provider=github host=github.com login=nerd-sniped`, exit 0. R2.1's acceptance criterion is met.
- **Fixed 2026-07-18** (while reviewing the manual test checklist for non-GitHub host coverage): `_headless_credential_args()` hardcoded `username=x-access-token` unconditionally — GitHub's convention, sent regardless of host. This silently broke container/`GITPDM_TOKEN` auth against GitLab (which requires `username=oauth2`) even though the generic-provider desktop path (interactive git credential prompt / PAT-in-URL / SSH) was always genuinely host-agnostic. Fixed by adding `credential_username` to `BaseProvider` (default `"x-access-token"`, overridden to `"oauth2"` on `GitLabProvider`) and a new `_headless_credential_username()` in `git/client.py` that resolves it via `GITPDM_PROVIDER` (the same env var `auth/credential_chain.py` already reads) through `providers.get_provider_class()`. This is a narrow, deliberate exception to "no provider conditionals in `git/client.py`" (CLAUDE.md) — it reads a provider *property*, the same capability-delegation pattern used everywhere else, not an `isinstance`/id branch. 7 new tests in `tests/test_git_client.py::TestHeadlessCredentialUsername`.
- **2026-07-21, `GITPDM_AUDIT_FIXES.md` follow-up** (a live-container audit found two real gaps, not just doc drift): (1) `TokenResponse` gained `expires_at: Optional[float]` (absolute epoch, computed once at issuance/refresh via `time.time() + expires_in` in `oauth_device_flow.poll_for_token()` and `token_refresh.refresh_token()`) plus shared `to_dict()`/`from_dict()` methods; all four token stores (`token_store_file.py`, `_macos.py`, `_linux.py`, `_wincred.py`) now call these instead of hand-rolling the same field list four times. `token_refresh.is_token_expired()`/`get_token_ttl_seconds()` check `expires_at` first, falling back to the original `obtained_at_utc + expires_in` computation for tokens persisted before this field existed — this was confirmed to be a **shape fix, not a live correctness bug**: `obtained_at_utc` was already anchoring `expires_in` correctly on every read. This does *not* reverse the original G1 brief's "do **not** add a separate `expires_at`" call above — that guidance was about not needing a *second, independently-drifting* expiry source; this `expires_at` is a cached, single computation of exactly the same value, done once at issuance instead of recomputed on every read, and both code paths remain in sync via the fallback. (2) `credential_chain.resolve_credential()` gained an optional `interactive_resolver` callable parameter, invoked only when file/env/keyring all miss. This is additive, not a reversal of the "interactive rungs stay in the UI layer" decision two paragraphs up: `resolve_credential()` still never imports PySide/FreeCAD or drives a device-flow/PAT-prompt UI itself (that would break `auth/check.py`'s "runs with no FreeCAD installed" contract) — it's an injection point, the same pattern `core/checkpoint.py` uses for `is_busy`/`save_if_dirty`, that a real UI caller *could* wire a synchronous device-flow-or-PAT-prompt entry point through. No UI code calls it with a real resolver yet (`github_auth.py`'s device flow is async/dialog-driven and can't return a token synchronously the way this parameter's contract expects) — wiring that up for real is a separate, larger follow-up, not done here. Callers that omit it (the CLI check, all existing tests) see the prior three-rung-only behavior, byte-for-byte unchanged. (3) `ui/connections_dialog.py`'s "Other Git Hosts" list now filters on `capabilities.requires_manual_token` instead of a hardcoded `pid not in ("github", "generic")` exclusion, so a future PAT-paste provider is picked up automatically. GitHub's own "GitHub Account" section stays hardcoded rather than capability-gated — `ui/panel.py`'s startup calls (`refresh_connection_status()`, `maybe_auto_verify_identity()`) assume its widgets always exist, and GitHub is currently the *only* `supports_device_flow=True` provider, so conditionally skipping construction had real risk of breaking the one working device-flow path for no present benefit. `tests/test_connections_dialog.py::TestGitHubDeviceFlowAssumption` asserts this single-provider invariant so it fails loudly (rather than silently misrouting) if a second device-flow provider is ever added.

**Context (corrected in v2):** GitPDM currently assumes an OS keyring — that assumption does fail in containers. But it does **not** model tokens as immortal strings: `auth/oauth_device_flow.py` defines `TokenResponse` with `refresh_token`, `expires_in`, `refresh_token_expires_in`, and `obtained_at_utc`; `auth/token_refresh.py` implements expiry detection (5-minute buffer), transparent refresh, and graceful degradation to re-auth (`ensure_fresh_token`). Persistence goes through a `TokenStore` ABC (`auth/token_store.py`) with per-OS backends chosen by `auth/token_store_factory.py`. **Extend these pieces; do not rewrite them.** What's missing: headless resolution rungs, a `provider` field, chain orchestration, and the CLI check.

**Build:**
1. Add `provider: str = "github"` to `TokenResponse` (or a thin `Credential` wrapper if extending the dataclass breaks deserialization of already-stored tokens — check how the per-OS stores serialize before choosing). Do **not** add a separate `expires_at`; that semantics already exists as `obtained_at_utc + expires_in`.
2. A resolution chain module (e.g. `auth/credential_chain.py`), tried in order, each rung either *yielding*, *missing* (silent fall-through), or *erroring* (logged warning + fall-through, never a crash):
   `GITPDM_TOKEN_FILE` → `GITPDM_TOKEN` → keyring (existing `create_token_store()`) → device flow (if provider supports) → PAT prompt.
   The chain resolves the non-interactive rungs; the interactive rungs (device flow, PAT prompt) stay in the UI layer, which acts on the chain's outcome.
3. File persistence backend: a new `TokenStore` implementation (`auth/token_store_file.py`) writing `~/.config/GitPDM/credentials.json`, `chmod 0600`, engaged **only** when `GITPDM_ALLOW_FILE_TOKENS=1`. Wire it through the factory following the existing per-OS pattern. Without the flag it must be unreachable — assert this in a test; it is the desktop-security invariant.
4. Transparent refresh: **already implemented** (`token_refresh.ensure_fresh_token`). G1's job here is only to (a) verify it is actually invoked before every network git/API operation and close any gaps, and (b) parameterize the hardcoded GitHub token URL per provider. Env-sourced tokens are PATs with no refresh token; `is_token_expired` already treats missing expiry info as long-lived — no work needed there.
5. A CLI-invokable check (`python -m freecad_gitpdm.auth.check`) that resolves the chain and prints the authenticated login. Must import and run with no FreeCAD installed (the `core/log.py` FreeCAD dependency must not leak in). This is the container smoke test.

**Acceptance:**
- Unit tests: every rung yields/misses/errors correctly; precedence order enforced; file backend unreachable without the env flag; refresh path exercised with a fake expiring token.
- `docker run -e GITPDM_TOKEN=<pat> …auth.check` prints the login on a machine with no keyring daemon.
- Existing keyring flow on desktop is behaviourally unchanged.

**Do not:** log token values anywhere (add a test that greps captured logs); store tokens in FreeCAD parameters; add a keyring polyfill for containers.

---

## Phase G2 — Release + CI *(unblocks the sister repo's image build)* ✅ IMPLEMENTED

**Implements:** R3.1, R3.2. **Depends on:** G1 merged. ✅ (G1 is on `dev`; merge or branch from it.)

**As built** (`dev`, 2026-07-17):

- `.github/workflows/release.yml` — new workflow, triggered on `v*` tags only; existing `ci.yml` untouched. Four jobs: `verify` (ruff + pytest + architecture guard, gates the rest), `build` (asserts the tag matches all four synced version fields, assembles `Init.py`/`InitGui.py`/`freecad_gitpdm/` into a `GitPDM/` layout, zips it, uploads as a build artifact), `container-smoke` (downloads the artifact, unzips into a clean `Mod/`-shaped directory, imports `freecad_gitpdm` with `FreeCAD`/`FreeCADGui` mocked the same way `tests/conftest.py` does — this is belt-and-suspenders since the package currently imports clean with no FreeCAD present at all, per its try/except-guarded `core/log.py`), and `publish` (creates the GitHub Release via `softprops/action-gh-release`, attaching the archive, `contents: write` permission scoped to that job only).
- README support matrix (R3.2) was already updated in `acfa289` ("current stable + one prior" policy) — no further change needed here.
- Version bumped to **0.5.0** across `pyproject.toml`, `Init.py`, `freecad_gitpdm/__init__.py`, `docs/README.md` in this same change. The `v0.5.0` tag push (which fires the release workflow above) is a separate, explicit step — not done automatically as part of the code change.

**Context (corrected in v2):** CI already exists — `.github/workflows/ci.yml` runs ruff lint + format check, pytest across Python 3.10/3.11/3.12 on Linux/Windows/macOS (FreeCAD mocked via `tests/conftest.py`), and `tools/architecture_guard.py`, on push/PR to `main` and `dev`. **Do not rebuild it.** This phase only adds release automation.

**Build:**
1. Tag-triggered release job (extend `ci.yml` or add `release.yml`): on tag `v*` — build a release archive with the layout the tutorial describes (`Init.py`, `InitGui.py`, `freecad_gitpdm/`) and attach it to a GitHub Release. Existing lint/test/guard jobs stay untouched.
2. A container smoke job: install the archive into a clean `Mod/`-shaped directory, `python -c "import freecad_gitpdm"` succeeds with FreeCAD mocked.
3. Update the README support matrix: tested-against FreeCAD versions incl. 1.1.x, and the policy "current stable + one prior", verified manually before each release. No FreeCAD-in-CI (see R3.2 as revised — CI mocks FreeCAD by design).
4. Bump the version to **0.5.0** across all four synced fields (`docs/README.md`, `pyproject.toml`, `freecad_gitpdm/__init__.py`, `Init.py` — per CLAUDE.md) and tag `v0.5.0`. (`v0.4.0` was already tagged from pre-G1 `main` on 2026-07-16; v0.5.0 is the release that carries the credential engine.)

**Acceptance:** the release page has a downloadable archive; Tutorial 1's "download the latest release" instruction is now true; CI green including the pre-existing architecture guard.

---

## Phase G3 — Storage modes *(independent; ship any time before public docs)* ⛔ RETIRED 2026-07-20

**⛔ Retired 2026-07-20** — see `Dev_Docs/PRESENCE_AND_LFS_REMOVAL_PLAN.md` for
the full record; kept below for historical reference, not as current
behavior. Real Git LFS file locking (this phase's entire justification for
the "lfs" mode) was never actually implemented on any provider
(`supports_lfs_locking` stayed `False` everywhere, permanently deferred as
D1) — on reflection, locking's real value is preventing *wasted editing
effort*, not preventing data loss (checkpoints/recovery already make every
state recoverable), and that value doesn't need Git LFS's storage model at
all. Replaced by an advisory, provider-agnostic "who else has this file
open" presence indicator (`core/presence.py`); the entire storage-mode
split (`core/storage_mode.py`, `ui/storage_mode_dialog.py`, the wizard's
mode picker, `supports_lfs_locking`, `git lfs install`) was then deleted.
Every repo now behaves like the old "delta" mode, unconditionally.

**Implements:** R1.1, R1.2, R1.3, R1.4. **Depends on:** nothing (parallel-safe with G1/G2).

**As built** (`g3-storage-modes` branch off `dev`, 2026-07-17 — kept for reference; the brief below is the original spec):

- `core/storage_mode.py` — new single source of truth for the `storageMode` field in `.freecad-pdm/config.json` (default `"delta"`) and the `*.FCStd` line in `.gitattributes`. `apply_storage_mode()` rewrites exactly that one line (preserving all other `.gitattributes` content), writes the config, and (for `lfs`) best-effort runs `git lfs install` if a git client is passed. `get_storage_mode()` defaults to `delta` on missing/malformed config, never crashes.
- `core/settings.py` — `ensure_git_friendly_fcstd_compression()` (the regression: silently flipped the global compression preference, never recorded the prior value) is **replaced**, not patched, by `enter_git_friendly_compression_scope()` / `exit_git_friendly_compression_scope()` / `recover_stuck_compression_scope()`. Investigated FreeCAD's API per the brief: there is no per-document `CompressionLevel` override, but `CompressionLevel` is only *read* at save-serialization time, so the scope is tied to the save call itself (`slotStartSaveDocument` → `slotFinishSaveDocument`) rather than "while a repo is open" — tighter than the brief asked for, and it sidesteps the open/close-tracking complexity entirely. `recover_stuck_compression_scope()` handles the crash-mid-save case (flag left active from a previous session) by restoring on next startup; wired into `ui/panel.py`'s deferred init.
- `ui/panel.py` — `_DocumentObserver` gained `slotStartSaveDocument` (enters the scope, only for saves inside the active repo root when its mode is `delta`) and `slotFinishSaveDocument` now wraps its body in `try/finally` so `exit_git_friendly_compression_scope()` always runs (a no-op if never entered, so this is safe unconditionally). Added a Storage Mode row (label + "Change…" button) to the status section.
- `ui/repo_validator.py` — the blind `settings.ensure_git_friendly_fcstd_compression()` call on every repo open (the shipped R1.2 harm) is gone; repo validation now only *reads* `storage_mode.get_storage_mode()` for display/caching, with zero global side effects from opening a repo. Added `change_storage_mode_clicked()`.
- `ui/storage_mode_dialog.py` — new `StorageModeDialog`: delta/lfs radio choice; selecting a different mode than the repo currently has always shows a blocking `QMessageBox.question` explaining the consequence before it's applied (satisfies R1.1's "never a silent flip" in both directions, not just delta→lfs).
- `core/scaffold.py` / `ui/new_repo_wizard.py` — the old ad hoc `enable_lfs` checkbox + hand-rolled `.gitattributes` writer (which wrote an LFS filter line unconditionally when checked, independent of any config) is replaced by a delta/lfs radio choice routed through `storage_mode.apply_storage_mode()`, so the new-repo path and the existing-repo path never disagree about what's forbidden.
- `tools/storage_mode_benchmark.py` — runs standalone (no FreeCAD required), builds a synthetic XML-like `.FCStd` proxy, saves it 10x per mode, and prints per-save loose-object growth plus a final `git gc` pack-size summary. **Empirical finding, documented in the script's own module docstring:** this small-scale synthetic proxy does not reliably reproduce R1.1's "deflate cascade" in the expected direction — generic zlib over this content still lets git's delta compression find cross-version similarity more often than not. The script is honest about this rather than curve-fit to always show delta mode winning; it points at running the same technique through FreeCAD's own CLI against a real project (real BREP data, real topological-naming churn) for a trustworthy verdict, consistent with R1.4's "gains are real but uneven."
- `tests/test_storage_mode.py` (new, 14 tests) + `tests/test_settings.py` (rewritten compression-scope tests) cover: default-mode fallback, exact `.gitattributes` stanza per mode with no forbidden tokens (`-delta`, coexisting `binary`+`filter=lfs`), mode-switch cleanup of the old stanza, unknown-mode rejection, and the enter/exit/recover scope state machine.
- `tools/architecture_baseline.json` — `ui/panel.py` limit bumped 2500 → 2550 (grew ~68 lines net for the document-observer split + storage mode UI row).

**Context (sharpened in v2):** compression=0 and Git LFS are mutually defeating (see R1.1 rationale). This is not hypothetical: v0.4.0 ships `core/settings.py:ensure_git_friendly_fcstd_compression()`, called from `ui/repo_validator.py` on repo validation, which **silently sets the global FreeCAD `CompressionLevel` to 0 and does not record the prior value** — the exact harm R1.2 describes — while `docs/README.md` simultaneously recommends LFS. G3 replaces that function's behavior; it is partly a regression fix.

**Build:**
1. A single repo-scoped setting `storage_mode: "delta" | "lfs"` in `.freecad-pdm/config.json`. A `.freecad-pdm/` config-file mechanism already exists for export presets (`export/preset.py` reading `preset.json`) — mirror that pattern; it's also needed by G4. Default for new repos: `delta`.
2. Mode application, atomically coupled:
   - `delta` → FreeCAD compression 0, no LFS filter, write `*.FCStd binary` to `.gitattributes`.
   - `lfs` → FreeCAD compression back to user's prior/default, LFS tracking for `*.FCStd`.
3. Compression scoping (R1.2): apply the global `CompressionLevel` parameter only while a GitPDM repo is the active document context; restore the prior value on switch-away/close. If FreeCAD's API makes true scoping infeasible, fall back to: explicit consent dialog on first use + a visible log line on every change. Investigate `App.ParamGet("User parameter:BaseApp/Preferences/Document")` and document-activation signals; report which path was taken.
4. UI: mode selector in settings; switching to `lfs` shows the warning that compression will be restored and why; the two forbidden states (compression 0 + LFS; `-delta` or LFS filter on `*.FCStd` in delta mode) are unreachable by construction.
5. Benchmark script in `tools/` (repo convention — `scripts/` doesn't exist): save the same document 10× with a small change per save, in each mode, print `git count-objects -vH` growth. (Run headless via FreeCAD's CLI if available; otherwise document manual invocation.)

**Acceptance:**
- Unit test asserts forbidden-state unreachability. ✅ `tests/test_storage_mode.py::TestForbiddenStatesUnreachable`.
- Scoping test: open GitPDM repo → open unrelated doc → global compression equals the user's prior value. ✅ satisfied more strongly than written: since scoping is tied to the save call (not document-open), an unrelated doc's save is *never* touched regardless of what's open elsewhere — see `tests/test_settings.py::TestCompressionScope` for the enter/exit/restore state machine this relies on.
- `.gitattributes` written on repo creation contains exactly the delta-mode stanza; never contains `-delta`. ✅.
- Benchmark script runs and reports. ✅ with an honest caveat about what its synthetic numbers do and don't prove (see "As built" above).

**Do not:** silently flip the global preference; promise text-like delta ratios in any doc string (R1.4 — BREP deltas are real but uneven).

---

## Phase G4 — Provider abstraction *(architecturally urgent: stops GitHub leakage)* ✅ IMPLEMENTED

**Implements:** R5.1, R5.2, R5.3, R4.3. **Depends on:** G1 (uses `Credential.provider`).

**Context (expanded in v2):** the transport layer (`git/` subprocess wrapper) is already host-agnostic. The `github/` package is not — today it holds `api_client.py`, `cache.py`, `create_repo.py`, `errors.py`, `identity.py`, `rate_limiter.py`, `repos.py` — and every feature built before this refactor deepens the coupling. Note that `auth/` is *also* GitHub-coupled (device-flow endpoints and client ID in `auth/config.py`, hardcoded token URL in `token_refresh.py`): provider classes should own their auth endpoints so the G1 chain and refresh path can consult them. The generic provider is the **base case**, not a fallback.

**Build:**
1. Restructure `github/` → `providers/`:
   - `base.py` — `GenericProvider`: plain git + PAT/SSH. **Zero host API calls.** Repo creation = instruct user to create in browser + paste URL. This class alone must make GitPDM fully functional.
   - `github.py` — extends base: device flow, repo-creation API, (existing PR features if present).
   - Capability flags on the class: `supports_device_flow`, `supports_repo_creation`, `supports_lfs_locking`, `supports_pull_requests`. UI reads flags and hides unavailable actions — it never offers an action that will fail.
2. Provider selection persisted per-repo in `.freecad-pdm/config.json` (from G3): `{provider: "github" | "generic", remote_host: …}`. Two repos with different providers open in one session must not fight over global state.
3. `gitlab.py` **stub only**: class exists, capability flags set (device flow true, per R5.2 GitLab ≥17.9), methods raise `NotImplementedError` with a tracking-issue reference. The stub's purpose is to prove the abstraction has a second consumer shape — full implementation is deferred.
4. Rename sweep (R4.3): README title to git-based, repo topics, any UI strings saying "GitHub" where the provider is variable.

**Acceptance:**
- **The forcing test:** a scripted flow using `GenericProvider` against a bare git remote (a local `git init --bare` is fine) completes: configure → clone → save → commit → push, with zero HTTP calls (assert via a network-mock or by pointing at a nonexistent API host).
- Existing GitHub flows behave identically to pre-refactor (regression suite or manual checklist).
- UI shows no repo-creation button when the active provider lacks the capability.

**Do not:** implement GitLab beyond the stub; build an SSH-key management UI (out of scope — generic provider assumes the user's git already authenticates, e.g. PAT in remote URL or ambient SSH agent); leak provider conditionals into `core/`/`export/` (all branching lives in `providers/`).

---

## Phase G5 — Container ergonomics ✅ IMPLEMENTED

**G5 as built** (merged into `dev` from `g5-container-ergonomics`,
2026-07-18 — kept for reference; the brief below is the original spec):

- **R2.2:** `ui/github_auth.py`'s device-flow dialog gained a read-only,
  selectable `QLineEdit` showing the verification URL as literal text (the
  user code was already selectable) plus a "Copy Link" button.
  `_open_verification_uri` now checks `QDesktopServices.openUrl`'s return
  value instead of discarding it; on failure (or an exception) a fallback
  label appears telling the user to copy the link manually instead of
  failing silently.
- **R2.3:** new `core/session_lock.py` — advisory `.git/gitpdm.lock` JSON
  lockfile (`pid`/`timestamp`/`hostname` exactly as specified). PID
  liveness is stdlib-only (no psutil/pywin32 added): `os.kill(pid, 0)` on
  POSIX, `ctypes.windll.kernel32.OpenProcess` on Windows — one function
  with a platform branch rather than a new per-OS-file factory, since it's
  small enough not to warrant one. Stale threshold is 15 minutes on a
  still-live PID. Wired into `ui/repo_validator.py`'s `_handle_valid_repo`/
  `_handle_invalid_repo` (the single choke point every repo activation and
  path switch already flows through) with a Yes/No override dialog; a
  5-minute heartbeat timer in `panel.py` refreshes our own lock so a long
  session doesn't look abandoned, and `closeEvent` releases it.
  `tests/test_session_lock.py` covers acquire/release, dead-PID and
  stale-timestamp auto-clear, live-foreign-PID blocking, and force-steal.
- **R2.4 (scoped down from the brief — see below):** `git/client.py` gained
  `clone_repo(..., depth=...)`, `is_shallow_repo()` (fails open on any
  error — it only gates a UI affordance), and `deepen_repo()`
  (`--deepen N` or `--unshallow`). `ui/repo_picker.py` exposes a
  "Shallow clone" checkbox (`DEFAULT_SHALLOW_CLONE_DEPTH = 20`),
  default-checked when `headless_backends_active()` is true (the existing
  G1 signal for "probably a container"). `panel.py` shows a persistent
  "History truncated — Deepen" banner when the active repo is shallow, with
  a working Deepen button. **Scope decision:** at implementation time there
  was no commit-log/history/diff/blame UI anywhere in GitPDM to "audit" per
  the brief's step 3 — that UI doesn't exist yet (still on the roadmap).
  G5 therefore shipped the shallow-clone infrastructure and the panel-level
  indicator only, not a new history-browsing feature; commit/push/pull were
  already history-agnostic and verified working unmodified against a real
  shallow clone.
- **R2.4 panel-driven first run:** mostly pre-existing (paste-URL clone in
  `ui/repo_picker.py`, create-via-provider-API in `ui/new_repo_wizard.py`
  gated on `capabilities.supports_repo_creation`, both confirmed already
  degrading correctly for non-API providers per G4). The actual gap closed:
  `panel.py` now shows a first-run hint above the repo-path field
  ("No repository yet — clone an existing one or start a new one below")
  when `settings.load_repo_path()` is empty, instead of just blank fields.
- Architecture guard: `panel.py`'s baseline bumped 2500 → 2600
  (`tools/architecture_baseline.json`) for the lock heartbeat, shallow-clone
  banner, and first-run hint additions.
- 211 tests pass (up from 202); ruff, format check, and the architecture
  guard are all clean.

**Implements:** R2.2 (dialog hardening), R2.3 (session guard), R2.4 (shallow clone + panel bootstrap). **Depends on:** G1, G4.

**Build:**
1. **Device-flow dialog hardening (R2.2):** URL and user code rendered as selectable text; "open browser" is a convenience button whose `xdg-open` failure is caught and non-fatal; dialog legible at 1080p streamed (no tiny fixed fonts).
2. **Session guard (R2.3):** advisory lockfile `.git/gitpdm.lock` `{pid, timestamp, hostname}` on repo activation; stale-lock detection (dead PID or age > threshold → auto-clear); second live instance gets a warning dialog with override option, not a hard block.
3. **Shallow-clone tolerance (R2.4):** audit every history-touching feature (log views, diffs, blame-ish features, export) against a `--depth 20` clone; each degrades to a "history truncated — deepen?" affordance (running `git fetch --deepen`) rather than erroring.
4. **Panel-driven first run (R2.4):** from a fresh FreeCAD with GitPDM installed and a resolved credential, the panel offers *Clone existing* (URL field) or *Create new* (provider API if capability present; else instructions + paste URL). No terminal required end-to-end.

**Acceptance:**
- Scripted: `git clone --depth 20` a real repo → open in GitPDM → log view shows truncation affordance → deepen works → commit/push work.
- Two-instance test: second process opening the same repo sees the warning; killing the first and retrying auto-clears.
- Manual: complete first-run flow via panel only, in a container over a video stream.

---

## Phase G6 — Continuous checkpointing *(default-on; ships with the deployment MVP)* ✅ IMPLEMENTED

**Implements:** R2.5 (read it in full — it specifies triggers, guards, and the push-policy split). **Depends on:** G5.

**As built** (`dev`, 2026-07-18 — kept for reference; the brief below is the original spec):

- `git/client.py` gained the plumbing primitives, kept host-agnostic and
  reusable rather than baked into the scheduler: `rev_parse()` (read-only ref
  resolution), `commit_recovery_checkpoint()` (the `GIT_INDEX_FILE` + `add -A`
  + `write-tree` + `commit-tree` + `update-ref` sequence — parented on the
  recovery branch's own prior tip, falling back to HEAD only for the first
  checkpoint, so mainline commits never gain recovery-branch ancestors),
  `push_ref()` (pushes an arbitrary local ref without touching HEAD or the
  checked-out branch), `restore_from_recovery()` (`git checkout <sha> -- .`,
  which writes files without moving HEAD or switching branches), and
  `delete_recovery_branch()` (local `update-ref -d` + best-effort remote
  delete-ref, for the prune offer). Two real bugs were caught and fixed by
  the real-git integration tests before landing: `tempfile.mkstemp()`
  reserves the temp-index path by creating a 0-byte file, which git rejects
  as "smaller than expected" — the file has to be removed again, leaving
  only the path, before pointing `GIT_INDEX_FILE` at it; and
  `delete_recovery_branch()`'s branch-name extraction used
  `rsplit("/", 1)`, which — since the branch name itself is `gitpdm/recovery`
  (a slash-containing name) — chopped it down to bare `recovery` and deleted
  the wrong ref. Fixed by using the full `refs/heads/...` ref directly
  instead of reconstructing it from a split.
- `core/checkpoint.py` (new): FreeCAD-agnostic orchestration, per CLAUDE.md's
  "tests must run without FreeCAD" — the two FreeCAD-only questions ("is the
  user mid-edit" and "perform the actual save") are taken as injected
  `is_busy`/`save_if_dirty` callables rather than imported, so the scheduling
  and policy logic (`should_checkpoint()`, `should_auto_push_recovery()`,
  `run_checkpoint()`) is covered by pure-Python unit tests with a fake clock.
  `should_checkpoint()` fires on idle-since-last-edit (default 45s) OR a
  max-interval backstop since the *last checkpoint* (default 180s, not since
  the most recent edit — continuous active editing still gets checkpointed
  periodically instead of never going idle; a fake-clock test specifically
  pins this baseline choice). `max_interval_seconds_for_repo()` reads G3's
  `storage_mode` and lengthens the backstop to 600s in `lfs` mode (the
  settings-coupling requirement below). `run_shutdown_checkpoint()` +
  `register_sigterm_handler()` expose the external-signal hook the brief
  asked for, but deliberately don't self-install: GitPDM runs embedded in
  FreeCAD's GUI process, not as a standalone daemon, so installing a raw
  `signal.signal(SIGTERM, ...)` handler that calls into Qt/git from signal
  context would be its own hazard. The pattern mirrors `auth/check.py`
  (G1): an importable, headless-invokable entry point that a deployment's
  own process supervisor wires up, not something GitPDM calls on itself.
- Push policy: `core/settings.py` gained a tri-state
  `save_checkpoint_auto_push_override()`/`load_checkpoint_auto_push_override()`
  pair (string-backed `""`/`"true"`/`"false"`, so "never touched" is
  distinguishable from an explicit "off") — `should_auto_push_recovery()`
  checks the override first, else falls back to a default. Exposed as a
  3-option combo box in `ui/connections_dialog.py`'s new "Checkpointing"
  section — the natural home per that dialog's own stated purpose (settings
  you don't touch often).
  **Revised 2026-07-19, per explicit user decision (see R2.5's amendment
  note in `GITPDM_REQUIREMENTS.md`):** the no-override default changed from
  "follow `headless_backends_active()`" (push only when G1's env-var
  backends are active) to unconditionally `True` — auto-push is now the
  default on desktop too, not just headless, so a checkpoint is a real
  off-machine record as soon as it's made rather than sitting local-only
  until the next real commit. The combo box's first option was relabeled
  "Automatic (recommended — pushes by default)" from "Automatic (follow
  environment)" to match; `headless_backends_active()` is no longer
  referenced by this function at all. Tests updated
  (`tests/test_checkpoint.py::TestShouldAutoPushRecovery`) to assert the
  new default explicitly, including on a plain desktop session with no env
  vars set.
- `ui/panel.py`: `_checkpoint_state` (a `CheckpointState`) + a 10s
  `QTimer` polling `should_checkpoint()`/`run_checkpoint()` — the 10s tick is
  just scheduling granularity, not the checkpoint cadence itself, which
  `should_checkpoint()` decides. `_DocumentObserver` gained `slotChangedObject`
  (FreeCAD's per-property-change signal) to mark activity, the same
  observer class G3 already extended with `slotStartSaveDocument`/
  `slotFinishSaveDocument`. `_is_freecad_busy()` (checks
  `Document.HasPendingTransaction` and `FreeCADGui.Control.activeDialog()`)
  fails **closed** (treats an unreadable state as busy) rather than open,
  since a wrongly-skipped checkpoint just runs late, while a mid-edit save
  risks real corruption. `_save_active_document_if_dirty()` originally used
  `Document.isTouched()` to skip the blocking whole-file save when there's
  nothing new to capture.
  **Live-verified 2026-07-19** (user session, real FreeCAD): `slotChangedObject`
  fires correctly (`CheckpointState.dirty` confirmed `True` right after an
  edit). **`Document.isTouched()` was claimed "works as expected" in this
  same note originally, but that was never actually exercised by the
  session described below** (which only walked through `_checkpoint_state.
  dirty` and `_is_freecad_busy()`/`activeDialog()`, not `isTouched()`
  itself) **and turned out to be false — see the 2026-07-19 correction
  under the seamless-recovery follow-ups near the end of this document**:
  `isTouched()` tracks the recompute dependency graph, not "unsaved
  relative to disk," and was removed from this function entirely once a
  later real-world test proved it was silently skipping the save on
  essentially every checkpoint. **Found and fixed a
  real bug** in the same 2026-07-19 session: `FreeCADGui.Control.activeDialog()`
  returns a **bool** (`True` when a task dialog/panel is active), not the
  dialog object or `None` — the original code checked
  `... is not None`, and `False is not None` is `True` in Python, so
  `_is_freecad_busy()` reported "busy" unconditionally, permanently
  blocking every checkpoint regardless of actual state. Diagnosed by
  walking the user through `dock._checkpoint_state.dirty` (confirmed
  `True`) then `dock._is_freecad_busy()` (confirmed stuck `True`) then
  `repr(FreeCADGui.Control.activeDialog())` (revealed `False, <class
  'bool'>`) in the Python console — three quick checks isolated it exactly.
  Fixed to check truthiness directly (`if FreeCADGui.Control.activeDialog():`)
  instead of `is not None`. `Document.HasPendingTransaction` remains
  unexercised (the user wasn't mid-transaction during this session) — still
  flagged as not independently confirmed, though the same fail-closed
  design means a wrong value there would under-fire (delay a checkpoint),
  not corrupt anything, unlike the `activeDialog()` bug which over-fired
  "busy" and blocked checkpointing entirely.
- Restore-on-start: `ui/repo_validator.py`'s `_handle_valid_repo()` now
  calls `_maybe_offer_recovery_restore()`, which checks
  `checkpoint.recovery_branch_status()` and — only when no `.FCStd` document
  is currently open, reusing `branch_ops.py`'s existing
  `_get_all_open_fcstd_documents()` guard rather than duplicating it (the
  same corruption-risk class the "close ALL documents" branch-switching
  guard exists for) — offers a `QMessageBox` restore prompt.
- Prune: `ui/commit_push.py`'s `_auto_prune_recovery_checkpoint()` fires
  after both the plain "Commit" and the combined "Commit & Push" success
  paths, clearing the recovery branch once a real commit supersedes it.
  **Revised 2026-07-19 per explicit user decision:** originally asked via
  a `QMessageBox.question` ("Clear Recovery Checkpoint?"); changed to
  silent auto-prune — a commit always captures the current working tree,
  which is at least as up to date as any earlier checkpoint of that same
  tree, so there was nothing genuine to confirm and declining just meant
  re-asking after every single commit. Still reachable on demand from the
  "Git PDM" menu (`GitPDM_ClearRecoveryCheckpoint`, alongside the other
  rarely-touched entries like Change Storage Mode / Deepen History) for
  anyone who wants to inspect a checkpoint before it's cleared (e.g. if
  edits were undone since it fired, it could hold state the final commit
  doesn't).
- `tests/test_checkpoint.py` (new, 28 tests): real-git integration tests
  (same style as `test_generic_provider_flow.py`) for the plumbing —
  specifically proving the corruption-safety invariant (`HEAD`, the real
  index, and the working tree are byte-identical before/after a checkpoint),
  that mainline history never gains recovery commits, that a second
  checkpoint chains onto the first rather than HEAD, and that restore writes
  files without moving HEAD — plus pure unit tests (fake clock, fake
  `git_client`) for `should_checkpoint()`'s idle/backstop decision, the
  push-policy override tri-state, and `run_checkpoint()`'s busy-guard/push
  wiring.
- `tools/architecture_baseline.json`: `git/client.py` bumped 2050 → 2300 (new
  plumbing methods, ~2234) and `ui/repo_validator.py` bumped 600 → 650 (the
  restore-on-start prompt, ~626).
- 405 tests pass (up from 377); ruff, format check, and the architecture
  guard are all clean.
- **Deferred, not done:** an in-panel commit-log/history browser doesn't
  exist yet (same gap G5 already noted), so there's no UI surface to show
  *which* checkpoints exist beyond the single latest recovery-branch tip;
  the restore/prune flows work against "the current tip" only. SIGTERM
  wiring into an actual deployment process supervisor is explicitly the
  sister repo's responsibility, not exercised here beyond unit-testing that
  `register_sigterm_handler()` installs successfully.

**Context:** this delivers the Onshape-style "walk away anytime, lose ≤ ~1 minute" guarantee via debounced checkpoints, not per-action persistence (prohibitive on FreeCAD's blocking whole-file save — see R2.5 rationale).

**Build:**
1. Checkpoint engine: idle-debounced (~30–60 s idle + dirty), max-interval backstop (2–5 min), external-signal hook (exposed so the container's SIGTERM handler can invoke save+checkpoint+push synchronously before exit).
2. Transaction guard: query FreeCAD's active command/transaction state; skip and reschedule if busy. Never save mid-edit.
3. Commit to `gitpdm/recovery` **without ever moving HEAD or touching the working tree** — documents are open during checkpoints, and the branch-switching corruption constraint applies (see CLAUDE.md / README). Use plumbing, not porcelain: build a tree via a temporary index (`GIT_INDEX_FILE` + `git add -A` + `git write-tree`), `git commit-tree` with the recovery branch tip as parent, then `git update-ref refs/heads/gitpdm/recovery <new-sha>`. Git operations async via subprocess — the Qt main thread is only ever touched by the save itself.
4. Push policy: recovery-branch auto-push ON when headless credential backends (G1 env vars) are active, OFF on desktop by default; both overridable in settings.
5. Restore-on-start prompt when recovery branch is ahead; prune/reset offer on next real commit.
6. Settings coupling: in `lfs` mode, lengthen default checkpoint interval and say why (each checkpoint is a full stored LFS object; delta mode makes frequent checkpoints cheap).

**Acceptance:**
- Integration: dirty document → idle → checkpoint fires → `kill -9` the process → restart → restore offered → file round-trips intact.
- SIGTERM path: external hook invoked → work present on recovery branch after process exit (this is the deployment's Phase 1.4 test from the sister repo's side).
- Transaction guard: checkpoint scheduled during an active sketch edit does not fire until the edit closes.
- Desktop default: no network push occurs without headless backends active (assert no push in test harness).
- Mainline history never contains recovery commits.
- A checkpoint leaves HEAD, the real index, and the working tree byte-identical to before (assert in test — this is the corruption-safety invariant).

**Do not:** attempt per-action persistence or unsaved in-memory sync (explicit non-goal); auto-restore without prompting; block the UI on any git operation; check out, switch branches, or run any porcelain command that rewrites the working tree while documents are open.

---

## Phase G7 — Docs sweep *(gates public launch, not code)* ✅ IMPLEMENTED

**Implements:** R4.1, R4.2, R3.3. **Depends on:** G3 (modes must exist as described).

**As built** (`dev`, 2026-07-19 — kept for reference; the brief below is the original spec):

- `docs/README.md`'s "Git LFS (Why It's Recommended for CAD)" section is
  replaced by "Storage Modes (Delta vs. LFS)" using R4.1's draft verbatim
  (Explanations layer) plus a new "Storage Modes" Technical Reference
  section (the delta/LFS mechanics table, `.gitattributes`/
  `.freecad-pdm/config.json` fields, and the real benchmark run below) —
  R4.2's "state the opposition plainly" landed in both places.
- Found and fixed a real doc/code contradiction while doing this: "Why
  GitPDM Sets FreeCAD's Compression Level to 0" still described the
  pre-G3 behavior (global flip on every repo *open*, left in place) that
  G3 explicitly replaced with a save-scoped flip/restore. Rewritten to
  describe what's actually shipped — this was the acceptance criterion
  ("no doc contradicts shipped behaviour") catching a real regression in
  the docs themselves, not just missing content.
- New Technical Reference sections: "Credential Chain & Environment
  Variables" (all four `GITPDM_*` vars, verified against
  `auth/credential_chain.py`/`token_store_file.py`/`git/client.py` source
  rather than written from memory — table content, file paths, and
  precedence order are grep-confirmed), "Shallow Clone" (G5), and
  "Continuous Checkpointing" (G6, with the actual 45s/3min/10min-in-lfs
  numbers from `core/checkpoint.py`, not rounded-off prose).
- New How-To: "How to Connect a Non-GitHub Host" — the multi-provider hosts
  work (GitLab/Bitbucket/Gitea-Forgejo/SourceHut) had **zero** end-user
  documentation before this; the panel's "Other Git Hosts" section and PAT
  flow were fully shipped but undiscoverable from the README.
  `Tutorial 2` gained a pointer to it, and both tutorials were corrected
  against the actual shipped UI (see below).
- **Tutorials 1 and 2 corrected against the real UI**, verified by reading
  `ui/panel.py`/`ui/connections_dialog.py` source (exact button labels,
  visibility conditions) rather than assuming the tutorial's original prose
  still matched the bottom-dock UI simplification's redesigned panel:
  "Browse for Folder" → "Browse…"; "Connect GitHub" is no longer inline in
  the panel, it's `Git PDM → Connections…`; there is no standalone
  "Commit" or "Push" button anymore, only a combined workflow-mode button
  (default "Commit and Push", switchable via a **▼** dropdown to
  "Save Only (don't share yet)" / "Share Only (already saved)") — Tutorial
  1 now explicitly switches to "Save Only" since it has no remote yet, and
  Tutorial 2 gained a "connect this existing local repo to a GitHub remote"
  step (paste a URL into **Connect Remote**) that was previously skipped
  over silently.
- `tools/storage_mode_benchmark.py` run for real, numbers included with
  the script's own caveat: on this run, LFS mode's packed size (5.45 KiB)
  came in *smaller* than delta mode's (59.78 KiB) — the opposite of the
  naive expectation, and exactly the outcome the script's module docstring
  already warned was possible at small synthetic scale. Reported honestly
  rather than cherry-picked or omitted, with the existing explanation for
  why real `.FCStd`/BREP data is expected to behave differently.
- `Developer-Facing Architecture Overview` and `Roadmap` sections updated
  for accuracy: `github/` → `providers/` (with its subpackages),
  `core/checkpoint.py`/`storage_mode.py`/`session_lock.py` added, "Support
  for additional hosting providers" moved from Long-term ideas to a new
  "Recently shipped" list alongside storage modes and checkpointing.
- **R3.3 (Addon Manager submission) — prep done, actual submission not
  done here:** researched the *current* submission process live (the
  wiki's `Package_metadata` page is bot-walled; used
  `github.com/FreeCAD/Addon-Template`'s real `package.xml` and a real
  published workbench's (`FreeCAD_FastenersWB`) `package.xml` as verified
  schema references instead of writing from memory). Added `package.xml`
  at the repo root (legacy layout: `classname=GitPDMWorkbench`,
  `subdirectory=./`). Two things block a real submission and are flagged
  in the file: a maintainer contact email (placeholder only — invented one
  would be actively wrong) and an icon (GitPDM has never had one,
  `InitGui.py`'s `Icon = ""` since Sprint 0). Also discovered **GitPDM had
  no LICENSE file at all**, which would have blocked submission outright
  (Addon Manager requires a clear OSI license) — asked the user, who chose
  MIT; added `LICENSE` and `pyproject.toml`'s `license` field. The actual
  submission (a GitHub issue against `FreeCAD/Addons` using the
  "Addon - Addition" template, per `Addon-Academy`'s current docs — not a
  PR, as the phase brief assumed) is an external, identity-bound action
  for a maintainer to take, not something done autonomously from here.
- 405 tests still pass (docs-only + one metadata file change, no source
  touched); ruff, format check, and the architecture guard all clean.

1. Replace the "Git LFS (Why It's Recommended for CAD)" section with the storage-modes explainer drafted in R4.1.
2. Reference section: state the delta/LFS opposition plainly (R4.2); document the credential chain and every `GITPDM_*` env var (from G1); shallow-clone behaviour (from G5).
3. Include benchmark numbers from G3's script (real numbers, not projections).
4. Submit to the FreeCAD addon index (R3.3).

**Acceptance:** a new user following only the README makes the correct storage-mode choice for their situation; no doc contradicts shipped behaviour.

---

## Phase G8 — HistoryWorkbench integration *(spike may run any time; adapter after G4)*

**Implements:** R5.5a–c (read §5b of the requirements in full — it contains the license boundary and the coexistence risk analysis). **Depends on:** spike: nothing; adapter: G4 (capability-flag pattern).

**Context:** HistoryWorkbench (`eblanshey/HistoryWorkbench`, LGPL-2.1) provides visual 3D diff and review UX. GitPDM consumes it via runtime interop — **never fork it, never vendor its code** (LGPL boundary).

**Build:**
1. **Spike first (R5.5a):** install both addons on one project. Determine whether HW can operate against a GitPDM-managed repo, and where its internal git state lives. Write the finding to `docs/history-wb-interop.md` before any adapter code. If the answer is "needs upstream changes," stop and report — that's a collaboration conversation (R5.5d), not code.
2. Adapter `integrations/history_wb.py` — the only module that may import or reference HW. Import probe + minimum-version check at runtime, never at module load. Expose `supports_visual_diff` through the G4 capability system.
3. Diff invocation: materialize two revisions of an `.FCStd` to temp files via `git show <rev>:<path>`, call HW's compare entry point, clean up temp files after.
4. UI: "Visual diff" action on any two versions in the history view — rendered only when the capability is true.
5. CI pair test (R5.5c): commit a part twice with a dimension change, invoke the adapter, assert the comparison opens without error. Wire to run on any bump of either pinned version.

**Acceptance:**
- GitPDM with HW uninstalled: zero behavior change, no import errors, no visual-diff UI shown.
- GitPDM with incompatible HW version: action hidden, one log line, no crash.
- With compatible HW: two-commit dimension change produces an opened comparison.
- `grep -r "history_wb" --include="*.py"` outside `integrations/` returns nothing (the choke-point invariant, as a test).

**Do not:** copy any HW code into GitPDM (LGPL); import HW at module load; make any GitPDM feature *require* HW; write to HW's internal storage.

---

## Deferred (tracked, not scheduled)

- **R2.6** touch-viable panel — after the deployment project's touch pass produces findings.
- ~~**D1** LFS locking~~ — retired 2026-07-20 rather than shipped; see `Dev_Docs/PRESENCE_AND_LFS_REMOVAL_PLAN.md`. Replaced by the advisory presence indicator (Plan A), which needed no per-provider locking API.
- **D2** assembly link integrity — research spike first; likely GitPDM's long-term differentiator.
- **GitLab full implementation** — exercises R2.1a's refresh path for real; schedule when a GitLab user exists.

## Sequencing summary

```
G1 ──► G2 ──────────────► (sister repo can build)
 │
 ├──► G4 ──► G5 ──► G6
 │      └──► G8 (adapter; spike runs any time)
G3 (parallel, any time) ──► G7 (docs, pre-launch)
```

Critical path for the deployment project: **G1 → G2**. Everything else improves the product; those two unblock it.
