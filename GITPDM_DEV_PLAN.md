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

---

## How to use this document (instructions to the implementing agent)

1. **Explore before editing.** Module names below (`freecad_gitpdm/`, `github/`, `git/`, `ui/`, `core/`, `export/`) come from the README's architecture section and may not match reality exactly. Map the actual layout first; adapt paths, preserve intent.
2. **The desktop user is sacred.** Every phase must be a no-op or an improvement for someone running GitPDM in desktop FreeCAD with a keyring. If a change alters desktop behaviour, stop and flag it.
3. **Tests must run without FreeCAD.** FreeCAD's Python API isn't pip-installable. Structure new code so business logic imports cleanly under plain pytest, with `FreeCAD`/`FreeCADGui`/`PySide` mocked or injected at the edges. UI and document-event code gets thin adapters; logic lives below them.
4. **No new hard dependencies** beyond stdlib + what GitPDM already vendors. Git operations shell out (existing pattern); HTTP uses whatever the codebase already uses.
5. **One phase = one PR.** Don't reach forward into later phases.

---

## Phase G1 — Credential engine *(BLOCKER for everything external)*

**Implements:** R2.1, R2.1a. **Depends on:** nothing.

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

## Phase G2 — Release + CI *(unblocks the sister repo's image build)*

**Implements:** R3.1, R3.2. **Depends on:** G1 merged.

**Context (corrected in v2):** CI already exists — `.github/workflows/ci.yml` runs ruff lint + format check, pytest across Python 3.10/3.11/3.12 on Linux/Windows/macOS (FreeCAD mocked via `tests/conftest.py`), and `tools/architecture_guard.py`, on push/PR to `main` and `dev`. **Do not rebuild it.** This phase only adds release automation.

**Build:**
1. Tag-triggered release job (extend `ci.yml` or add `release.yml`): on tag `v*` — build a release archive with the layout the tutorial describes (`Init.py`, `InitGui.py`, `freecad_gitpdm/`) and attach it to a GitHub Release. Existing lint/test/guard jobs stay untouched.
2. A container smoke job: install the archive into a clean `Mod/`-shaped directory, `python -c "import freecad_gitpdm"` succeeds with FreeCAD mocked.
3. Update the README support matrix: tested-against FreeCAD versions incl. 1.1.x, and the policy "current stable + one prior", verified manually before each release. No FreeCAD-in-CI (see R3.2 as revised — CI mocks FreeCAD by design).
4. Bump the version to **0.5.0** across all four synced fields (`docs/README.md`, `pyproject.toml`, `freecad_gitpdm/__init__.py`, `Init.py` — per CLAUDE.md) and tag `v0.5.0`. (`v0.4.0` was already tagged from pre-G1 `main` on 2026-07-16; v0.5.0 is the release that carries the credential engine.)

**Acceptance:** the release page has a downloadable archive; Tutorial 1's "download the latest release" instruction is now true; CI green including the pre-existing architecture guard.

---

## Phase G3 — Storage modes *(independent; ship any time before public docs)*

**Implements:** R1.1, R1.2, R1.3, R1.4. **Depends on:** nothing (parallel-safe with G1/G2).

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
- Unit test asserts forbidden-state unreachability.
- Scoping test: open GitPDM repo → open unrelated doc → global compression equals the user's prior value.
- `.gitattributes` written on repo creation contains exactly the delta-mode stanza; never contains `-delta`.
- Benchmark script runs and reports.

**Do not:** silently flip the global preference; promise text-like delta ratios in any doc string (R1.4 — BREP deltas are real but uneven).

---

## Phase G4 — Provider abstraction *(architecturally urgent: stops GitHub leakage)*

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

## Phase G5 — Container ergonomics

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
