# GitPDM — Requirements for Headless / Remote Operation

**Status:** Draft v2 — triaged and corrected against the codebase at v0.4.0 (commit `f94343c`, 2026-07-16)
**Target:** GitPDM v0.5.0 (v0.4.0 was tagged from pre-existing `main` on 2026-07-16; the work below lands in v0.5.0)
**Context:** GitPDM is being adopted as the data layer for a browser-accessible, containerised FreeCAD deployment (single-user). This document captures what GitPDM must do to support that, plus storage-policy corrections that apply to *all* users, not just the remote case.

**Baseline reviewed:** README @ v0.3.0; v2 revisions verified against source at v0.4.0. Notable v2 corrections: R2.1a (expiry/refresh already implemented — see revised rationale), R1.2 (the global-preference harm is *shipped behavior*, not hypothetical), R3.1 (v0.4.0 tag exists), R3.2 (no FreeCAD-in-CI; docs policy + manual verification).

---

## 0. Guiding constraints

| # | Constraint | Rationale |
|---|---|---|
| C1 | Free at a user scale of 1 | No metered services in the default path |
| C2 | No `.env` authoring by the user | Setup is 1–2 clicks + a device code |
| C3 | Server is disposable | All durable state lives in GitHub |
| C4 | Addon stays usable on a normal desktop | Deployment concerns must not leak into the addon |

C4 is the one to defend hardest. Most GitPDM users will never run it in a container. Every requirement below must be a no-op or an improvement for a laptop user.

---

## 1. Storage & compression policy

### R1.1 — Decouple compression from LFS *(priority: high)*

Setting FreeCAD's compression level to 0 and enabling Git LFS are **mutually defeating**. This must be encoded in the product, not just the docs.

- LFS stores each version as a whole, opaque object. There is **no delta compression, ever**.
- Uncompressed `.FCStd` files are materially larger (~3–5x).
- Therefore compression=0 + LFS = *multiplied* LFS storage and bandwidth consumption against a 1 GiB free tier.

The benefit of compression=0 accrues **only to plain git**, where it enables xdelta to work at all:

> Deflate cascades. A single dimension change shifts the entire compressed stream, so every subsequent byte differs. Git sees two dissimilar blobs, gives up on delta, and stores a full copy per commit. Stored (uncompressed) zip entries expose the raw `Document.xml` and BREP data, letting xdelta match unchanged regions and letting git's own zlib pack compression do the work once instead of twice.

**Requirement:** GitPDM MUST treat storage mode as a single choice with coupled settings, and MUST NOT allow the incoherent combination.

| Mode | Compression | LFS | Locking | Cost |
|---|---|---|---|---|
| `delta` **(default)** | 0 | off | none | Free, unmetered |
| `lfs` (opt-in) | 3 (FreeCAD default) | on | available | Metered past 1 GiB |

**Acceptance:**
- Enabling LFS in the UI warns that compression will be restored to default, and explains why.
- Selecting `delta` mode with LFS already active surfaces a blocking explanation, not a silent flip.
- Neither mode is reachable by accident.

### R1.2 — Compression must be repo-scoped, not user-global *(priority: high)*

`CompressionLevel` lives in FreeCAD's global parameter store (`BaseApp/Preferences/Document/…`). Setting it from the addon changes the preference for **every document that user owns**, including non-GitPDM projects. A user with one GitPDM repo and ten unrelated FreeCAD projects would silently get bloated files across all of them.

**v2 note — this is shipped behavior, not a hypothetical:** v0.4.0's `core/settings.py:ensure_git_friendly_fcstd_compression()` (called from `ui/repo_validator.py` when a repo is opened or created) silently sets the global preference to 0 and does not record the prior value, so there is nothing to restore. This requirement is therefore partly a regression fix and its priority stands.

**Requirement:**
- Store the intended mode in `.freecad-pdm/config.json` (repo-scoped, committed, travels with the project).
- Apply the global preference only while a GitPDM repo is the active context; restore the prior value on deactivation.
- If scoped application proves infeasible in FreeCAD's API, then the global change MUST be explicit, consented-to on first use, and logged — never silent.

**Note:** existing files do not shrink until re-saved. The first save after a mode switch rewrites the whole file — expect one large commit, then normal behaviour. Document this.

### R1.3 — Manage `.gitattributes` *(priority: high)*

**Requirement:** on `Create Repo` in `delta` mode, write:

```gitattributes
*.FCStd binary
```

- `binary` expands to `-diff -merge -text`. This is correct and does **not** disable delta compression.
- **Never** emit `-delta` for `*.FCStd`.
- **Never** add `*.FCStd` to an LFS filter in `delta` mode.

Either of the last two silently discards the entire benefit of R1.1, with no visible symptom until the repo is large. A test should assert their absence.

### R1.4 — Honest limits *(priority: medium)*

Delta gains are real but uneven. OCCT BREP geometry is still binary, and topological naming means a small parametric edit can renumber IDs and rewrite large regions. Sketches and `Document.xml` delta well; BREP less so. Docs should not promise text-like ratios.

---

## 2. Headless / container operation

### R2.1 — Credential storage without a keyring *(priority: BLOCKER)*

This is the single hard blocker for the remote deployment.

Current README: Linux tokens use the Secret Service API (GNOME Keyring / KWallet); the stated fallback for headless systems is "use SSH for Git operations."

Neither works here:
- A container running Xvfb + a streaming server has **no Secret Service daemon**. Running `gnome-keyring-daemon` inside a container is fragile and itself needs an unlock secret — recreating the problem.
- SSH fallback violates C2: the user is now generating keypairs and pasting them into GitHub. That is not two clicks.

**Requirement:** add a headless credential backend, selected automatically when Secret Service is unavailable:

1. **`GITPDM_TOKEN_FILE`** — read a token from a path. Satisfies Docker secrets, mounted volumes, and CI.
2. **`GITPDM_TOKEN`** — read a token from an environment variable. **Required for platform-identity injection**: Fly, AWS, GCP and most PaaS platforms inject secrets as env vars, *not* files. Supporting only `_FILE` would exclude every platform-native secret store.
3. **File backend** — persist to `~/.config/GitPDM/credentials.json`, mode `0600`, on a mounted volume so it survives container recreation. Gate behind explicit opt-in (`GITPDM_ALLOW_FILE_TOKENS=1`) so it can never silently downgrade a desktop user's security.

**Resolution precedence:**

```
GITPDM_TOKEN_FILE  >  GITPDM_TOKEN  >  keyring  >  device flow (if provider supports)  >  PAT prompt
```

**Acceptance:** GitPDM authenticates and pushes in a container with no keyring daemon, no SSH key, and no `.env` file.

### R2.1a — Model token expiry and refresh *(priority: high)*

The credential layer must not assume "a token" is a single opaque, immortal string. Provider behaviour differs materially:

| Provider | Access token lifetime | Refresh required |
|---|---|---|
| GitHub (OAuth App) | Does not expire by default | No |
| GitHub (GitHub App, user-to-server) | ~8 hours | Yes, rotating |
| GitLab (OAuth) | **2 hours default** (instance-configurable) | Yes |
| PAT / SSH | Until revoked/expiry set by user | No |

**Requirement:** the credential record is `{ access_token, refresh_token?, expires_at?, provider }`, not a string. Refresh is attempted transparently before an operation when `expires_at` is near. A failed refresh degrades to re-auth, not a crash mid-push.

**Rationale (corrected in v2):** the first draft assumed GitPDM modeled tokens as immortal strings. It does not — `TokenResponse` already carries `refresh_token`/`expires_in`/`obtained_at_utc`, and `auth/token_refresh.py` implements expiry detection with a 5-minute buffer, transparent refresh, and graceful degradation. **The remaining gap is only the `provider` field and un-hardcoding the GitHub token URL** so the same machinery serves GitLab's 2-hour tokens. See §5 and Phase G1 of the dev plan.

**Note:** GitHub OAuth App tokens not expiring is a convenience *and* a liability — a leaked token is leaked indefinitely. This is one argument for treating re-auth on cold start as acceptable rather than something to engineer around.

### R2.2 — Device flow is the setup UX *(priority: high)*

The existing OAuth device flow is the right primitive and needs no redesign — it is the reason this deployment is viable at all. It requires no callback URL, no open port, and no local browser. The user sees a short code rendered in the FreeCAD panel over the video stream, authorises it on their phone, and lands connected.

**Requirement:** ensure the device-flow dialog is fully usable at streamed resolutions and does not depend on `xdg-open` succeeding (there is no browser in the container). The dialog must render the URL and code as **selectable text**, with the "open browser" button treated as an optional convenience that fails gracefully.

### R2.3 — Concurrent session guard *(priority: medium)*

A hosted deployment makes it trivial to open two browser tabs against one repo and one working tree. The README already notes that `.FCStd` files can corrupt if the working directory changes while documents are open.

**Requirement:** advisory lockfile in `.git/gitpdm.lock` with PID + timestamp. Second instance warns rather than proceeds. Cheap insurance now; expensive to retrofit once people have workflows.

### R2.4 — Fast bootstrap: shallow clone & panel-driven setup *(priority: high)*

The deployment clones on boot with no volume; clone time is cold-start time. Additionally, the rung-2 user may deploy *before* creating a repo, so first-run setup must be completable entirely from inside the FreeCAD panel over a video stream.

**Requirement:**
- Support operating in a shallow clone (`--depth N`). Commit/push/pull must work; history views degrade gracefully ("older history not fetched — deepen?") rather than erroring.
- First-run panel flow: *clone existing repo by URL* or *create new* (via provider API where available per §5, else instructions + paste-URL). No terminal required.

### R2.5 — Continuous checkpointing *(priority: high; default ON)*

**Push policy revised 2026-07-19, per explicit user decision (supersedes the
"Push policy split" bullet below):** auto-push of the recovery branch
defaults **ON everywhere** — desktop and headless alike — not just in
headless/container environments as originally specified. The user
prioritized "a checkpoint is a real off-machine record as soon as it's
made" over the original concern about surprise background pushes on
desktop; that concern is still addressable (an explicit "Never" override
exists in settings), it's just no longer the default. The original
requirement text below is kept for historical record; treat this note as
authoritative for current behavior.

**Goal:** the Onshape *guarantee* — walk away at any moment, from any device, and lose at most ~a minute of work — without the Onshape *mechanism*. Onshape persists every action because it has no files: each UI action is a transaction against a cloud feature-graph database. FreeCAD's save is a blocking, whole-file serialization of a monolithic `.FCStd` on the Qt main thread. Per-action persistence is therefore prohibitive here (UI freezes, mid-transaction corruption risk); a debounced checkpoint policy is not.

**Requirement — checkpoint policy, default ON:**
- **Triggers:** document dirty AND user idle ~30–60 s; a max-interval backstop (every 2–5 min while dirty regardless of activity); on external signal (the deployment's SIGTERM handler calls this hook on platform stop/sleep).
- **Guard:** never fire while a command/transaction is active — check FreeCAD's active-transaction state before saving.
- **Action:** save the document, commit to a dedicated `gitpdm/recovery` branch. The git commit + push run asynchronously (subprocess); only the save itself touches the main thread, and idle-triggering hides it.
- **Push policy split:** auto-push of the recovery branch defaults **ON in headless/container environments** (detected via the R2.1 env backends being active), **OFF on desktop** — desktop users should not get surprise background pushes to their remote; local recovery commits still protect them against crashes.
- **Restore:** on session start, if `gitpdm/recovery` is ahead of the working branch, offer restore (never auto-restore). The next real commit offers to prune/reset the recovery branch so mainline history stays clean.

**Synergy note:** delta mode (R1.1) is what makes this affordable — frequent saves of uncompressed `.FCStd` files produce sublinear pack growth. In `lfs` mode, checkpoint frequency should back off (every checkpoint is a full stored object); surface this coupling in settings.

**Non-goal:** continuous sync of unsaved in-memory state or per-action persistence. Save-triggered checkpointing is the honest maximum on a file-based document model; anything more fights FreeCAD and loses.

### R2.6 — Touch-viable panel UI *(priority: low, Phase 4 timing)*

On an iPad or phone, GitPDM's panel is operated by finger over a video stream. The core actions (stage, commit, push, pull, branch switch) need hit targets that survive that; Qt defaults don't.

**Requirement:** a "large controls" toggle (or respect FreeCAD's global UI scaling) for the GitPDM panel; commit flow completable without right-click or hover-dependent controls. Full audit deferred until the deployment's Phase 4 touch pass produces real findings.

---

## 3. Release & packaging hygiene

### R3.1 — Publish tagged releases *(priority: high)*

The repo previously showed **no releases published**, but Tutorial 1 instructs users to "Download the latest GitPDM release." That link went nowhere. This is both a new-user papercut and a build blocker: the container image needs to pin a GitPDM version to be reproducible, and pinning to `main` makes the image non-deterministic.

**Status (v2):** `v0.4.0` was tagged from pre-credential-engine `main` and pushed on 2026-07-16 (GitHub serves source archives for the tag; the layout `Init.py`, `InitGui.py`, `freecad_gitpdm/` is the repo root, so the archive matches the tutorial). Remaining work, in Phase G2: a Release page with a purpose-built archive, automated on tag, and the `v0.5.0` release carrying the credential engine — which is the version the container image should pin, since headless auth (R2.1) lands there.

### R3.2 — Refresh the support matrix *(priority: medium)*

README lists FreeCAD 0.20 / 0.21 / 1.0. FreeCAD 1.1 shipped March 2026 and 1.1.1 in April; the project has moved to CalVer with time-based releases, so this table will now drift faster than it used to.

**Requirement (reworded in v2):** state a tested-against version and a policy (e.g. "current stable + one prior") in the README, verified manually before each release. There is deliberately **no FreeCAD version in CI** — the test suite mocks FreeCAD by design (`tests/conftest.py`), so "add a CI matrix entry for 1.1.x" as originally written had nothing to attach to. If real-FreeCAD smoke testing in CI is ever wanted (headless AppImage/conda job), that is a separate, explicitly-scoped work item — not part of this requirement.

### R3.3 — Addon Manager index *(priority: low)*

Manual install into `Mod/` is a real adoption tax. Submit to the FreeCAD ≥1.0 addon index.

---

## 4. Documentation corrections

### R4.1 — Rewrite "Git LFS (Why It's Recommended for CAD)" *(priority: high)*

As written, this section actively causes the harm R1.1 describes: a user follows the README, enables LFS, and the compression change inflates their storage and bandwidth rather than reducing it. Replacement draft:

> **Storage modes**
>
> **Delta mode (default, free).** GitPDM saves `.FCStd` files uncompressed so that git can store only what actually changed between versions, rather than a fresh copy each commit. Repos stay small, and plain git on GitHub is free and unmetered. Individual files on disk are larger; this is intentional and is what makes the history small.
>
> **LFS mode (opt-in, for teams).** Git LFS adds file locking — the ability to reserve a file so a teammate cannot edit it simultaneously. Because `.FCStd` files cannot be merged, locking is the only real answer to concurrent edits. The cost: LFS stores every version in full, with no delta compression, and GitHub's free LFS allowance is ~1 GiB of storage and ~1 GiB/month of bandwidth. GitPDM restores normal compression in this mode to keep those numbers down.
>
> **Which do I want?** Working alone: delta mode. You do not have a concurrency problem, and delta mode is free. Sharing write access with others: LFS mode, and budget for a data pack.

### R4.2 — Document the delta/LFS coupling in the reference section

State plainly: compression=0 and LFS are opposites. Anyone reading the technical reference should not have to infer it.

### R4.3 — Rename away from "GitHub-based" *(priority: medium)*

README currently reads *"An Open Source **Github** Based PDM Addon For FreeCAD"*, and the repo topics list `github`. Per §5, GitHub is a convenience default, not a dependency — the transport layer is already host-agnostic today.

**Requirement:** retitle to git-based (the project name is already correct), and adjust topics. Worth doing before the ecosystem anchors on the GitHub association; the name is the cheapest thing to change now and the most expensive later.

---

## 5. Host agnosticism (provider abstraction)

**Goal:** the stack works with any git host — GitHub, GitLab, Gitea/Forgejo, Bitbucket, or a bare SSH remote. GitHub is the convenience default, not a dependency.

This promotes an existing roadmap item ("Support for additional hosting providers") from long-term idea to architectural constraint, because retrofitting it is dramatically more expensive than designing for it.

### The three layers

| Layer | Host-specific? | Work |
|---|---|---|
| **Git transport** (commit/push/pull/fetch/clone) | No — already generic via the `git/` subprocess wrapper | **None. Already works today.** |
| **Credentials** | Partially | PAT/SSH is universal; device flow is a per-provider bonus |
| **Host API** (repo creation, PRs) | Yes | Adapter per provider |

Note that **Git LFS locking is part of the LFS server specification**, not a GitHub API. GitHub, GitLab and Gitea all implement it. D1 (locking) therefore inherits host-agnosticism for free.

### R5.1 — Generic provider is the base case, not the fallback *(priority: high)* ✅ IMPLEMENTED

**Build the generic adapter first.** Make "plain git + PAT, no host API" the base class that GitHub *extends* — not a degraded path retrofitted after the fact. If GitHub is built first, its assumptions leak into `core/`, `ui/`, and `export/`, and excavating them later costs several times more than doing it in the right order now.

**Forcing test:** GitPDM MUST be fully functional against a host with **zero API support**.
- No repo creation API → user creates the repo in a browser and pastes the URL.
- No PR integration → feature absent, not broken.
- Previews are just committed files → already work anywhere.

If everything degrades cleanly to that, the layering is correct.

**Requirement:** restructure `github/` → `providers/` with `base.py` (generic: plain git + PAT/SSH), then `github.py`, `gitlab.py`, `gitea.py` as extensions. Capabilities are declared, not assumed:

```python
class Provider:
    supports_device_flow: bool
    supports_repo_creation: bool
    supports_lfs_locking: bool
    supports_pull_requests: bool
```

UI hides what the active provider can't do. It never offers an action that will fail.

**As built** (see `GITPDM_DEV_PLAN.md`'s "Multi-provider hosts as built"
for the full writeup): `providers/` restructure done in Phase G4
(`base.py` + `github/`); GitLab, Bitbucket, Gitea/Forgejo, and SourceHut
(additive beyond this requirement's original four) added as full
subpackages on `multi-provider-hosts` off `dev`, 2026-07-18, all real
create/list/clone workflows via PAT-paste auth, not stubs. GitLab,
Bitbucket, and Gitea were verified against real live API endpoints during
development; SourceHut's GraphQL schema could not be (its endpoint
requires auth even for introspection) and needs a real-token acceptance
pass before being fully trusted. `ProviderCapabilities` gained three more
flags beyond this requirement's original four
(`requires_manual_token`/`requires_host_url`/`requires_workspace`) to
express the PAT-paste hosts' auth/input needs.

### R5.2 — Device flow support matrix *(priority: medium)*

Verified as of July 2026:

| Host | Device flow | Notes |
|---|---|---|
| GitHub | ✅ | Widely supported |
| GitLab 17.9+ | ✅ GA | Feature flag `oauth2_device_grant_flow` removed at 17.9; tokens expire in 2h (see R2.1a) |
| Gitea / Forgejo | ❌ | Open proposal only (`go-gitea/gitea#27309`), not accepted |
| Bitbucket / bare SSH | ❌ | PAT / key |

**The structural limit:** even where device flow exists, a *self-hosted* instance requires its own OAuth app registration. There is no universal client ID for self-hosted forges. The property that makes GitHub two clicks — one pre-registered app serving infinite instances — is unavailable off-SaaS.

**This is acceptable and needs no solution**, because it maps onto the existing persona split:

- **Non-self-hoster (2-click):** GitHub or gitlab.com. SaaS, one pre-registered app, device flow, zero config.
- **Self-hoster (technical):** any forge, PAT or SSH key via `.env`. Registering an OAuth app on their own Gitea would be *more* work than pasting a PAT, not less.

**PAT/SSH is the universal floor.** Every git host supports one.

**As built:** this is no longer just the theoretical fallback — GitLab,
Bitbucket, Gitea/Forgejo, and SourceHut all ship real PAT-paste
create/list/clone workflows (`requires_manual_token=True`), not merely
"paste a URL for a repo you made elsewhere." Device flow itself remains
unbuilt for all four (no pre-registered OAuth app exists for any of
them yet, consistent with the structural limit above) — `GitLabProvider`
no longer claims `supports_device_flow=True` the way an earlier stub did;
it's `False` until a real implementation exists, so the capability flag
doesn't overstate what's actually working.

### R5.3 — Provider config is repo-scoped *(priority: medium)*

Store provider identity and remote host in `.freecad-pdm/config.json` alongside storage mode (R1.2). Config travels with the project; a user can have a GitHub repo and a Forgejo repo open in the same FreeCAD session without global state fighting them.

### R5.4 — Deployment warning: do not co-locate the forge *(priority: doc)*

Self-hosting Forgejo *next to* the workstation container is thematically attractive (fully vendor-free) but **destroys the property the deployment architecture rests on**.

"The server is disposable because all durable state lives in the git host" holds only while the host is *somewhere else*. Co-locating reintroduces a pet with precious state requiring backups, and the ephemeral cost model dies with it.

Forgejo on a *separate* box or a small VPS preserves everything. Document this explicitly — it is a trap that looks like good practice.

## 5b. Ecosystem integration — HistoryWorkbench *(R5.5)*

**Context:** HistoryWorkbench (`eblanshey/HistoryWorkbench`, LGPL-2.1, v0.1.0 June 2026, FreeCAD 1.1+) already ships visual 3D diff (added/removed/shared geometry in distinct colors), tree/property comparison down to constraints and expressions, multi-document assembly review, and a git-free review vocabulary — using git internally. Its roadmap gap ("push to GitHub or other git remote services") is GitPDM's core competency; GitPDM's gap (visual diff) is its core competency. Integrate, do not fork.

### R5.5a — Interop spike *(priority: high; do before any adapter code)*

HW manages git state with its own semantics (iterations, reviewed snapshots, its own initialize flow). Two addons writing git state to one working tree is the collision risk. **Spike:** install both on one project; determine whether HW can (a) operate read-only against a GitPDM-managed repo, (b) keep its internal store in a gitignored subdirectory, or (c) needs an upstream "external git management" mode. Outcome (c) becomes agenda item one of the upstream discussion. Record findings before writing the adapter.

### R5.5b — Adapter, not dependency *(priority: high)*

- Single choke point: `integrations/history_wb.py` is the **only** module allowed to know HW exists.
- Runtime feature detection (import probe + minimum-version check); **never imported at module load**; the "Visual diff" action renders only when HW is present and version-compatible — same capability-flag pattern as R5.1.
- GitPDM's half of the handshake is minimal: materialize any two commits of an `.FCStd` to temp files (`git show rev:path`) and invoke HW's compare entry point.
- **License boundary:** HW stays a separate installed addon. No vendored or forked HW code in GitPDM — LGPL-2.1 obligations stay outside the codebase.
- GitPDM remains fully functional with HW uninstalled.

### R5.5c — Tested-pair CI *(priority: medium)*

CI job: commit a part twice with a dimension change, invoke the adapter, assert the comparison opens. Runs on any bump of either addon's pinned version. The deployment image ships only version pairs this test has passed (`GITPDM_VERSION` + `HISTORY_WB_VERSION` build args) — breakage prevention by consuming upstream progress, not freezing it.

### R5.5d — Upstream collaboration *(priority: high, non-code)*

Open a discussion with the HW author proposing division of labor: HW owns comparison/review/history UX; GitPDM owns remotes, auth, PDM semantics, deployment. Note the D2 overlap — HW's roadmap already includes `.FCStd` rename detection; coordinate rather than duplicate.

---

## 6. Deferred / research

### D1 — File locking

Real check-out/check-in via `git-lfs` native locking (`lockable` in `.gitattributes`, `git lfs lock` / `unlock`). GitHub already implements the server API — it exists because game studios have the same un-mergeable-binary problem. Ships with LFS mode, not before. **Not needed at user scale 1.**

### D2 — Assembly link integrity

The genuine gap in every git-based approach, and probably GitPDM's most defensible long-term differentiator. Git tracks renames heuristically at *repo* level; FreeCAD needs link integrity at *document* level. Rename a part in git today and assembly links break silently. Solving this means hooking document save/rename and rewriting `App::Link` targets. Commercial PDM treats this as routine; no open-source git-based tool does it well. Research spike before committing — and coordinate with HistoryWorkbench first (R5.5d): its roadmap already includes `.FCStd` rename detection, so this may become a joint effort rather than a solo one.

---

## 7. Non-goals

- Multi-tenancy or a session broker — out of scope for the addon entirely.
- Deployment/container logic in the GitPDM repo. Dependency direction is **sister-repo → GitPDM, never the reverse** (see C4).
- Merge conflict resolution UI (already on the roadmap; unaffected by this document).
- **Solving OAuth app registration for self-hosted forges.** There is no universal client ID; PAT is the correct answer for that persona (R5.2).
- Hosting an auth-broker/redirect service. Device flow's callback-free design is what avoids putting the project in the availability and trust path of every user's instance. Do not give this up.
