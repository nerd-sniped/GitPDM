# GitPDM Manual Test Checklist — G3, G4, G5, G6, Multi-provider hosts

Covers the phases that haven't had a real FreeCAD/Qt pass yet. G1 and G2
are already fully verified end-to-end (see `GITPDM_DEV_PLAN.md`'s "Closed
since the table above was first written" section) and aren't repeated here.
G7 (docs sweep) has no runtime surface to test and is also skipped.

**Branch:** everything below (G3–G6, multi-provider hosts, the bottom-dock
UI simplification) is merged into `dev` and pushed to `origin/dev` as of
2026-07-19 — a single `dev` checkout covers the whole file, no merging
required.

**Report View setup (do this first):** most of G6's log lines
(`log.info`/`log.debug`) go to FreeCAD's `PrintLog` channel, which Report
View **hides by default**. Right-click Report View → enable **Show Log
messages**, or several G6 steps below will show nothing even when working
correctly. (Push-failure warnings use `log.warning`/`PrintWarning` and are
visible either way.)

Each test has a **Steps**, **Expected**, and a blank **Result** line —
fill in Pass/Fail + notes as you go. If something fails, capture the exact
error text/log line before moving on.

## Prerequisites

- A real FreeCAD install (not the mocked test environment) with GitPDM
  installed as an editable addon pointed at this repo checkout, on `dev`.
- A GitHub account you're OK using for test repos (device-flow connect,
  repo creation via API).
- Ability to run **two FreeCAD processes at once** against the same repo
  path — two machines, or two user profiles/home directories on one
  machine, for the session-lock tests (G5).
- A way to open a Python console inside FreeCAD (View → Panels → Python
  console) — used for a couple of state-inspection/simulation steps below.
- Ability to force-kill the FreeCAD process (Task Manager end-task, or
  `kill -9`) — needed for G6's crash-recovery round trip (T6.2). A clean
  quit doesn't exercise the same path.

---

## G3 — Storage modes

### T3.1 — Fresh repo defaults to delta mode

**Steps:** Create a brand-new repo via GitPDM ("Start New Project…").
Open `.freecad-pdm/config.json` in the repo.
**Expected:** `storageMode` is `"delta"` (or the key is absent, which also
means delta — `get_storage_mode()` defaults to delta on a missing key).
**Result:** ___

### T3.2 — `.gitattributes` correctness in delta mode

**Steps:** In the same repo, open `.gitattributes`.
**Expected:** Contains exactly one `*.FCStd` line: `*.FCStd binary`. No
`-delta`, no `filter=lfs` line for `*.FCStd`.
**Result:** ___

### T3.3 — Compression scoping is save-scoped, not repo-scoped

This is the regression T3.3 exists to catch: G3 replaced code that used to
silently pin FreeCAD's **global** compression preference to 0 whenever a
GitPDM repo was merely open. The fix scopes the override tightly around
each save call (`slotStartSaveDocument`/`slotFinishSaveDocument`), not the
whole time a repo is active.

**Steps:**
1. Note your current global compression preference: Edit → Preferences →
   General → Document → Compression level (or via Python console:
   `FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Document").GetInt("CompressionLevel", 3)`).
2. Open a delta-mode GitPDM repo's `.FCStd` document and save it (Ctrl+S).
3. Immediately after the save completes, re-check the compression
   preference via the same Python console command.
4. Open/save an unrelated document that is **not** part of any GitPDM repo
   at some point before/after step 2, and check its saved compression
   didn't get forced to 0 either.

**Expected:** After step 3, the compression preference is back to the
value from step 1 (not left at 0). The unrelated document's save in step 4
is never affected.
**Result:** ___

### T3.4 — Switch delta → lfs

**Steps:** With the repo open, click the "Change…" button next to
"Storage Mode:" in the panel. Select "LFS" in the Storage Mode dialog.
**Expected:** A blocking warning dialog appears before anything changes,
titled around restoring compression / LFS storage/bandwidth /
"Existing files won't shrink or migrate until you save them again."
Confirming it: `.gitattributes`'s `*.FCStd` line becomes
`*.FCStd filter=lfs diff=lfs merge=lfs -text`; `storageMode` in
`.freecad-pdm/config.json` becomes `"lfs"`; FreeCAD's compression
preference reverts to your normal (non-zero) default on the next save.
**Result:** ___

### T3.5 — Switch lfs → delta

**Steps:** Reverse T3.4 — switch back to Delta mode via the same dialog.
**Expected:** A warning dialog with the delta-mode consequences appears.
After confirming: `.gitattributes`'s `*.FCStd` line is back to
`*.FCStd binary` (no leftover LFS filter line), `storageMode` is `"delta"`,
and the next save forces compression back to 0.
**Result:** ___

### T3.6 — Stuck compression scope recovers on next startup

Simulates a crash mid-save that leaves the compression override "stuck".

**Steps:** Via the FreeCAD Python console, manually set the stuck-scope
flag and a fake prior value, then restart FreeCAD:
```python
import FreeCAD
pg = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/GitPDM")
pg.SetBool("CompressionScopeActive", True)
pg.SetString("PriorCompressionLevelBeforeGitPDM", "3")
```
Restart FreeCAD with GitPDM installed.
**Expected:** On startup, a log line like "Found a GitPDM compression
scope left active from a previous session... restoring prior compression
level" appears (Report View, `[GitPDM]` prefix), and the global
compression preference ends up at `3` (or whatever value you set), not
stuck at 0.
**Result:** ___

### T3.7 — Benchmark script runs and reports real numbers

**Steps:** `python tools/storage_mode_benchmark.py` (check `--help` for
any required args — it saves the same document 10× with a small change
per save, in each mode, and reports `git count-objects -vH` growth).
**Expected:** Runs to completion, prints a growth comparison between delta
and lfs modes that looks sane (delta mode's repo growth should be
noticeably sublinear vs. lfs's roughly-linear-per-save growth).
**Result:** ___

---

## G4 — Provider abstraction

Already merged to `dev` since 2026-07-18 (PR #7) — mostly a regression
pass — confirm nothing broke in the GitHub-coupling refactor, plus
exercise the new generic-provider path for real. Also worth a quick eye
here since G3 and G5 both merged in *after* G4: nothing in T4.1–T4.7
should behave differently now than it did before those merges.

**Scope note for non-GitHub users:** device-flow connect, the repo picker's
listing table, and create-via-API are GitHub-only today (`GitLabProvider`
is a capability-flagged stub — see `providers/gitlab.py`). Pasting a URL
(T4.3/T4.3a/T4.5) is the real, permanent way GitPDM supports GitLab,
Bitbucket, self-hosted Gitea, etc. — not a fallback to route around. On
desktop that's genuinely as easy as it is for GitHub (paste a URL, let
git's own credential prompt/PAT-in-URL/SSH handle auth); the one place it
previously wasn't equally easy — headless/container auth via
`GITPDM_TOKEN` silently assuming GitHub's username convention — was a real
bug, fixed 2026-07-18 (see T4.3a).

### T4.1 — Device-flow connect (GitHub)

**Steps:** Click "Connect GitHub" in the panel. Follow the dialog (code +
browser authorization).
**Expected:** Connects successfully, panel shows connected GitHub login.
**Result:** ___

### T4.2 — Repo picker: list + clone via table

**Steps:** "Join Team Project…" → pick a repo from the table → clone.
**Expected:** Repo list loads, clone succeeds, GitPDM opens the cloned repo.
**Result:** ___

### T4.3 — Clone from URL (generic remote path, non-GitHub host)

This is the real test of "does GitPDM work for GitLab/Bitbucket/self-hosted
users" — cloning a GitHub URL through this path only proves the code
doesn't call GitHub's API, not that another host actually works. Use a
**real non-GitHub repo** you have access to: GitLab.com, a self-hosted
Gitea/Forgejo instance, Bitbucket, whatever you have.

**Steps:** In the repo picker, use "Or Clone from a Git URL" with a
non-GitHub URL, authenticating however that host normally expects (PAT
embedded in the URL, or your existing SSH agent/credential manager
prompting interactively).
**Expected:** Clones successfully. GitPDM never assumes GitHub — no
GitHub-specific error messages, no forced GitHub reconnect prompt.
**Result:** ___

### T4.3a — Headless/container credential auth against a non-GitHub host

Covers a real bug found and fixed 2026-07-18 while preparing this
checklist: the `GITPDM_TOKEN` container-auth bridge hardcoded GitHub's
"x-access-token" username for every host, which silently broke GitLab
auth (GitLab requires "oauth2"). Now fixed via a `credential_username`
property on each provider — this test is the real-world confirmation.

**Steps:** In a shell (doesn't need to be inside FreeCAD — this is a
`GitClient`-level operation): set `GITPDM_TOKEN=<a real GitLab PAT>` and
`GITPDM_PROVIDER=gitlab`, then run a push/pull against a real GitLab repo
you have write access to, e.g.:
```
GITPDM_TOKEN=<pat> GITPDM_PROVIDER=gitlab python -c "
from freecad_gitpdm.git.client import GitClient
c = GitClient()
print(c.clone_repo('https://gitlab.com/<you>/<repo>.git', '<dest>').ok)
"
```
**Expected:** Clone/push succeeds using only the env token — no separate
credential prompt, no GitHub-shaped auth error. Compare against the same
call with `GITPDM_PROVIDER` unset/`github` and a GitHub token, which
should still work exactly as before (regression check).
**Result:** ___

### T4.4 — New repo wizard: GitHub path

**Steps:** "Start New Project…" → choose "GitHub — create the repository
automatically" → fill in name/visibility → finish.
**Expected:** Repo actually created on github.com, local folder
initialized, remote added, pushed.
**Result:** ___

### T4.5 — New repo wizard: generic path

**Steps:** "Start New Project…" → choose "Another git remote — I'll paste
a URL I already have" → paste the URL of an empty repo you created some
other way — ideally on the **same non-GitHub host** used in T4.3/T4.3a, so
this test and those together cover the full non-GitHub-user journey
(create on the host's own site → paste URL → push).
**Expected:** Local folder initialized, remote added to the pasted URL,
pushed — no GitHub API call made.
**Result:** ___

### T4.6 — GitHub option disabled when disconnected

**Steps:** Disconnect GitHub (panel's Disconnect button). Open "Start New
Project…" again.
**Expected:** The GitHub radio button is disabled (not hidden), with hint
text like "Connect GitHub from the panel first...". Generic path still
fully usable.
**Result:** ___

### T4.7 — Existing flows unaffected (regression sanity)

**Steps:** On an already-connected GitHub repo: commit, push, pull,
create/switch a branch.
**Expected:** All behave identically to pre-G4 — no regressions from the
`github/` → `providers/github/` restructure.
**Result:** ___

---

## G5 — Container ergonomics

Nothing here has touched a real Qt/FreeCAD runtime yet — everything below
was only verified via mocked-Qt unit tests and (for the git-client pieces)
direct calls against a real shell git repo, not through the actual panel.
Since G5 merged in after G3, also keep an eye on T5.7's banner and T3.4's
storage-mode "Change…" button both living in the same Repository section
of the panel — confirm they don't visually collide or fight for space.

### T5.1 — Device-flow dialog: URL field + copy

**Steps:** Trigger "Connect GitHub". Inspect the dialog.
**Expected:** Below the (already-selectable) code, a read-only text field
shows the verification URL as plain selectable/copyable text — not just a
button. Clicking "Copy Link" puts that URL on the clipboard (paste
somewhere to confirm). Dialog is legible, nothing clipped, at your normal
resolution.
**Result:** ___

### T5.2 — Device-flow dialog: browser-open failure fallback

**Steps:** Force `QDesktopServices.openUrl` to fail or return False —
easiest is temporarily removing/breaking the OS's default-browser
association, or testing on a machine/VM with no browser installed at all.
Trigger "Connect GitHub".
**Expected:** Instead of nothing happening silently, a message appears
under the status label: "Couldn't open a browser automatically — copy the
link above and open it manually." The dialog remains fully usable via the
URL field + Copy Link.
**Result:** ___

### T5.3 — Session lock: second instance gets a warning

**Steps:** Open the same repo in two separate FreeCAD processes (instance
A first, then instance B — see Prerequisites for how to run two at once).
**Expected:** Instance B shows a warning dialog: "Repository Already Open
... (PID <A's PID> on <hostname>, opened <time>) ... Continue anyway?"
Clicking **No** leaves B showing "Locked by another session" and B's repo
is not activated. Reopening the same path and clicking **Yes** activates
it in B (steals the lock) — if you then check `.git/gitpdm.lock` in the
repo, its `pid` now matches B's process.
**Result:** ___

### T5.4 — Session lock: crash auto-clears

**Steps:** With B holding the lock from T5.3, force-kill B's process
(Task Manager / `kill -9`, not a clean close). Open the repo in a third
instance C (or reopen in A).
**Expected:** No warning dialog — the dead PID is detected and the lock is
silently reclaimed. `.git/gitpdm.lock` now holds the new process's PID.
**Result:** ___

### T5.5 — Session lock: stale-timestamp auto-clears (optional/advanced)

Covers the case where a process is still alive but abandoned the repo
(suspended, hung) — distinct from the dead-PID path in T5.4.

**Steps:** With no GitPDM instance holding the repo, manually write a lock
file with a *currently-running* process's real PID (any long-lived
process on your machine, e.g. your terminal or another app — just needs
`os.kill(pid, 0)`/`OpenProcess` to succeed) but an old timestamp:
```python
import json, os
lock = {"pid": <a real live pid>, "timestamp": "2020-01-01T00:00:00+00:00", "hostname": "other-host"}
with open(r"<repo>\.git\gitpdm.lock", "w") as f:
    json.dump(lock, f)
```
Then open that repo in GitPDM.
**Expected:** No warning dialog — a lock older than 15 minutes on a still-
live PID is treated as stale and silently reclaimed, same as T5.4.
**Result:** ___

### T5.6 — Shallow-clone checkbox default state

**Steps:** Open the repo picker on a normal desktop session (no
`GITPDM_TOKEN`/`GITPDM_TOKEN_FILE` env vars set). Check the "Shallow
clone" checkbox's default state. Then set `GITPDM_TOKEN=<anything>` in the
environment before launching FreeCAD and check again.
**Expected:** Unchecked by default on plain desktop; checked by default
when a headless credential env var is active.
**Result:** ___

### T5.7 — Shallow clone → banner → Deepen

**Steps:** Clone a repo with the "Shallow clone" checkbox checked (depth
20). Open it in the panel.
**Expected:** A banner reading "History truncated (shallow clone)" with a
"Deepen" button appears near the top of the Repository section. Click
Deepen; button shows "Deepening…" then re-enables; banner disappears once
the fetch completes.
**Result:** ___

### T5.8 — Shallow clone doesn't block normal operations

**Steps:** Before clicking Deepen in T5.7, make a small change, commit,
and push (assuming the repo has a remote you can push to). Also try Pull.
**Expected:** Commit/push/pull all work normally on the shallow clone —
no errors related to missing history.
**Result:** ___

### T5.9 — First-run hint

**Steps:** Clear the saved repo path (or use a fresh FreeCAD profile with
GitPDM freshly installed) and open the panel.
**Expected:** A blue-ish hint above the repo path field reads "No
repository yet — clone an existing one or start a new one below to get
started." Clone or create a repo; the hint disappears once a valid repo is
active.
**Result:** ___

---

## G6 — Continuous checkpointing

Nothing here has touched a real Qt/FreeCAD runtime yet. The git plumbing
itself (`GitClient.commit_recovery_checkpoint`/`push_ref`/
`restore_from_recovery`) is proven by real-git integration tests —
byte-identical HEAD/index/working-tree before and after, mainline history
never polluted — so this section is specifically about the FreeCAD-side
wiring that pytest can't reach: the busy-guard (`Document.HasPendingTransaction`,
`FreeCADGui.Control.activeDialog()`), the dirty-check (`Document.isTouched()`),
and the actual save trigger. If any of those FreeCAD API calls turn out to
be wrong, the failure mode isn't "checkpoint doesn't fire" — it's "the
busy-guard never trips and a checkpoint saves mid-edit," which is exactly
the corruption class the rest of this codebase's safety guards exist to
prevent. Treat this as the highest-priority section in the file.

**Timing reference:** idle-debounce 45s since your last edit; max-interval
backstop 3 minutes since the last checkpoint (10 minutes in `lfs` mode),
so continuous active editing still gets checkpointed periodically. A
`QTimer` polls every 10s to check whether either condition is met — that's
scheduling granularity, not the checkpoint cadence itself.

### T6.1 — Idle checkpoint fires and lands on `gitpdm/recovery`, not mainline

**Steps:** Open a repo with at least one commit. Edit and save a document
once normally. Make a second edit but don't save. Wait ~50 seconds idle.
**Expected:** Within ~10s of the 45s mark, Report View shows
`[GitPDM] ... Checkpoint committed <sha>` (requires "Show Log messages" —
see setup note above). The document gets saved to disk as part of this.
`git log --oneline HEAD` does **not** show the checkpoint. `git branch
--list` shows `gitpdm/recovery`.
**Result:** ___

### T6.2 — Crash-recovery round trip (the core G6 guarantee, never run before)

**Steps:** After T6.1's checkpoint exists, force-kill FreeCAD (Task
Manager / `kill -9` — not a clean quit) without making a real commit.
Relaunch FreeCAD, open the same repo.
**Expected:** A **"Recovery Checkpoint Available"** dialog appears showing
the checkpoint's short SHA. Clicking **Yes** restores file content matching
what you had right before the kill (not the last real commit), followed by
a **"Recovery Restored"** confirmation.
**Result:** ___

### T6.3 — Busy-guard: no checkpoint fires mid-edit

Covers a real bug found and fixed 2026-07-19 in a live debugging session:
`FreeCADGui.Control.activeDialog()` returns a bool, not the dialog object
or `None` — checking it with `is not None` made `_is_freecad_busy()`
permanently report "busy" (`False is not None` is `True`), silently
blocking every checkpoint forever, not just during real edits. If this
regresses, T6.1/T6.2/T6.4 will also silently fail (nothing ever fires) —
if any of those look dead, check `dock._is_freecad_busy()` in the Python
console first, exactly like this bug was found.

**Steps:** Enter Sketch edit mode (Part Design → Create Sketch) and stay in
it past 45 seconds idle.
**Expected:** No save/checkpoint occurs while the task panel is open — no
Report View line, no unexpected save prompt, no interruption to the edit.
Exit the sketch editor, wait 45s again — the checkpoint fires normally this
time (confirmed working as of the 2026-07-19 fix above).
**Result:** ___

### T6.4 — Max-interval backstop fires during continuous active editing

**Steps:** Keep actively editing (never idle more than ~30s at a stretch)
for a full 3+ minutes on a delta-mode repo.
**Expected:** A checkpoint still fires around the 3-minute mark even though
you never went properly idle (`git log gitpdm/recovery --oneline` shows a
new commit at roughly that interval).
**Result:** ___

### T6.5 — Push policy: default is auto-push everywhere (changed 2026-07-19)

The default flipped after the rest of G6 was built: checkpoints now push
automatically on a plain desktop session too, not only when
`GITPDM_TOKEN`/`GITPDM_TOKEN_FILE` are set. This is the test to prioritize.

**Steps:** On a normal desktop session (no env vars set), with a repo that
has a real, authenticated remote, leave **Git PDM → Connections… →
Checkpointing** on its default "Automatic" setting. Let a checkpoint fire
(T6.1). Check whether `gitpdm/recovery` reached the remote (`git fetch`
then `git log origin/gitpdm/recovery --oneline`, or check the host's web
UI directly).
**Expected:** The recovery branch **is** present on the remote — it pushed
automatically, with no setting changed from its default.
**Result:** ___

### T6.6 — Push policy: "Never" keeps checkpoints local

**Steps:** Switch Checkpointing to **Never**. Let another checkpoint fire.
**Expected:** A new commit appears on the local `gitpdm/recovery` branch,
but `git fetch` + comparing against `origin/gitpdm/recovery` shows the
remote never received it.
**Result:** ___

### T6.7 — Push with no remote configured doesn't error

**Steps:** On a repo with no remote at all, let a checkpoint fire.
**Expected:** The local checkpoint commit still succeeds — no crash, no
scary dialog. At most a quiet Report View **warning** (visible without any
setting change, since push failures log at warning level) noting the push
failed.
**Result:** ___

### T6.8 — Cleanup: auto-prune after a real commit

Revised 2026-07-19 per explicit user decision: this used to ask via a
"Clear Recovery Checkpoint?" dialog; it now prunes silently since a real
commit always supersedes any earlier checkpoint of the same tree, so
there's nothing to confirm.

**Steps:** With a recovery checkpoint present, make a real commit (**Commit**
or **Commit and Push**).
**Expected:** No dialog appears. `git branch --list` shows `gitpdm/recovery`
is gone immediately after the commit completes (locally, and remotely too
if it had been pushed). Report View shows `[GitPDM] ... Auto-pruned
recovery checkpoint <sha>` (requires "Show Log messages").
**Result:** ___

### T6.9 — Manual clear via the Git PDM menu

**Steps:** **Git PDM → Clear Recovery Checkpoint**, once with a checkpoint
present and once with none.
**Expected:** With one present: same confirm-then-clear flow as T6.8. With
none present: an informational "No Recovery Checkpoint" message, not an
error.
**Result:** ___

---

## Multi-provider hosts (GitLab, Bitbucket, Gitea/Forgejo, SourceHut)

Branch `multi-provider-hosts` (see the branch note at the top). Nothing
here has touched a real Qt/FreeCAD runtime — only live-verified at the
`GitClient`/API-client level (real unauthenticated requests against
gitlab.com, api.bitbucket.org, Codeberg, and git.sr.ht — confirmed
reachable and correctly classified as needing auth) and via mocked unit
tests. **SourceHut specifically is higher-risk than the other three**:
its GraphQL schema (mutation/query field names) could not be verified
against the live API at all (the endpoint requires a token even for
schema introspection) — built from public docs only. Test SourceHut last
and don't be surprised if repo creation/listing there needs a follow-up
fix once you can see real responses.

**Prerequisites for this section:** free-tier accounts (a few minutes
each to create) on GitLab.com, Bitbucket.org, a Gitea or Forgejo instance
(Codeberg.org works, or your own if self-hosting), and SourceHut
(sr.ht) — each with a Personal Access Token that has repo-creation scope.

### T-MP.1 — Connect via the panel's "Other Git Hosts" section

**Steps:** Open the panel. In the new "Other Git Hosts" section (below
"GitHub Account"), pick GitLab from the dropdown, paste a real GitLab PAT,
click Connect.
**Expected:** Status shows "Verifying…" then "GitLab: Connected as
&lt;username&gt;". Connect button disables, Disconnect enables.
**Result:** ___

### T-MP.2 — Wrong/invalid token is rejected cleanly

**Steps:** Switch the dropdown to Bitbucket, paste an obviously-wrong PAT
("not-a-real-token"), click Connect.
**Expected:** A clear "Connect Failed" dialog with a real error message
(not a crash, not a silent no-op). Status reverts to "Not connected".
**Result:** ___

### T-MP.3 — Gitea/Forgejo requires a server URL

**Steps:** Switch the dropdown to "Gitea / Forgejo". Confirm a "Server
URL:" field appears (it shouldn't for GitLab/Bitbucket/SourceHut). Try
Connect with the URL field empty.
**Expected:** Blocked with "Enter the Gitea / Forgejo server URL first."
before any network call. Fill in your instance's URL (e.g.
`https://codeberg.org`) + a real token, Connect succeeds.
**Result:** ___

### T-MP.4 — Two providers connected simultaneously don't clobber each other

This is the direct test of the credential-resolution bug found and fixed
in this branch (`core/services.py`'s `api_client_for()` used to always
read GitHub's settings regardless of which provider was asked for).

**Steps:** With GitLab connected (T-MP.1), also connect GitHub (existing
device-flow section) if not already, then connect Bitbucket too. Switch
the "Other Git Hosts" dropdown between GitLab and Bitbucket.
**Expected:** Each shows its own correct "Connected as X" status
independently — switching the dropdown never shows one provider's login
under another's name, and disconnecting one (T-MP.6) doesn't affect the
others' connection state.
**Result:** ___

### T-MP.5 — Browse Repos (the repo picker) for a connected host

**Steps:** With GitLab connected, click "Browse Repos…" in the Other Git
Hosts section.
**Expected:** The same repo-picker dialog GitHub uses opens, titled/
labeled for GitLab ("Sign in to GitLab…" text if disconnected, but here
it should go straight to listing), shows your real GitLab projects in the
table. Select one, clone it — confirm it clones successfully and opens in
the panel.
**Result:** ___

### T-MP.6 — Bitbucket's Browse Repos needs a workspace

**Steps:** Connect Bitbucket (T-MP.1 equivalent). Click "Browse Repos…".
**Expected:** A "Workspace:" field appears in the picker (not present for
GitLab/Gitea/SourceHut). Enter a real Bitbucket workspace slug you belong
to; the repo list loads for that workspace once entered.
**Result:** ___

### T-MP.7 — Disconnect clears state cleanly

**Steps:** With GitLab connected, click Disconnect, confirm the dialog.
**Expected:** Status reverts to "Not connected"; "Browse Repos…" now
shows "Connect to this host first" if clicked; the other connected
providers (T-MP.4) are unaffected.
**Result:** ___

### T-MP.8 — New Repo wizard: create on each of the 4 new hosts

Repeat for GitLab, Bitbucket, Gitea/Forgejo, and SourceHut (last).
**Steps:** "Start New Project…" → pick the host's radio button (no prior
panel connection needed — the wizard is self-sufficient) → fill in
folder/name/visibility/description → paste a PAT (+ server URL for Gitea,
if that page doesn't carry over from a prior connect) → Next → confirm the
"Verifying &lt;host&gt; token…" step succeeds → finish.
**Expected:** Repo actually created on the real host (check via browser),
local folder initialized, scaffolding written, pushed successfully. For
Bitbucket specifically, confirm the workspace field appears and the repo
lands under that workspace.
**Result (GitLab):** ___
**Result (Bitbucket):** ___
**Result (Gitea/Forgejo):** ___
**Result (SourceHut):** ___

### T-MP.9 — Wizard: invalid token fails fast with a clear message

**Steps:** Start the wizard, pick GitLab, paste an invalid PAT, proceed to
the progress page.
**Expected:** The "Verifying GitLab token…" step fails immediately with a
clear message — no folder created, no partial state left behind.
**Result:** ___

### T-MP.10 — GitHub regression check

**Steps:** With the multi-provider branch active, run through T4.1–T4.7
from the G4 section above again (device-flow connect, repo picker,
wizard create/generic path).
**Expected:** Everything behaves identically to the G4-only pass — this
branch didn't touch `providers/github/*` at all, but it did touch shared
UI files (`new_repo_wizard.py`, `repo_picker.py`, `panel.py`) that GitHub
flows also run through, so this is worth re-confirming.
**Result:** ___

---

## Sign-off

| Section | All tests pass? | Tester | Date |
|---|---|---|---|
| G3 storage modes | ☐ | | |
| G4 provider abstraction | ☐ | | |
| G5 container ergonomics | ☐ | | |
| G6 continuous checkpointing | ☐ | | |
| Multi-provider hosts | ☐ | | |
