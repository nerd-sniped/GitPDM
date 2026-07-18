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
| G3 storage modes | ✅ Implemented & merged | `dev`, 2026-07-18 |
| G4 provider abstraction | ✅ Implemented & merged | `dev` @ `e5039de` (PR #7), 2026-07-18 |
| G5 container ergonomics | ✅ Implemented & merged | `dev`, 2026-07-18 |
| G6–G8 | Not started | — |

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
now unblocked.

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

## Phase G3 — Storage modes *(independent; ship any time before public docs)* ✅ IMPLEMENTED

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

## Phase G6 — Continuous checkpointing *(default-on; ships with the deployment MVP)*

**Implements:** R2.5 (read it in full — it specifies triggers, guards, and the push-policy split). **Depends on:** G5.

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

## Phase G7 — Docs sweep *(gates public launch, not code)*

**Implements:** R4.1, R4.2, R3.3. **Depends on:** G3 (modes must exist as described).

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
- **D1** LFS locking — ships with a real `lfs`-mode team user, not before.
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
