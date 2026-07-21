# GitPDM — Audit Follow-up Fixes

**Context:** a live audit (real container runs, not just code review) checked G1/G2/G4 against their acceptance criteria and found two real gaps and two lower-priority items. This is a punch list to close them — not a re-architecture. Explore the actual code before editing; file/function names below are from the audit and may need light adjustment to match reality.

---

## P0 — fix before anything else builds on top of this

### 1. Credential record needs a real `expires_at`, not `expires_in`

**Problem:** `TokenResponse` (`auth/oauth_device_flow.py`) stores `expires_in` (seconds-remaining *at issuance*). If nothing anchors that to when it was issued, a stale check can read a long-expired token as valid. No shared serializer exists — `token_store_file.py` and other stores each hand-roll their own field list, which drifts.

**First, determine which case this is:**
- If an `issued_at`/timestamp is stored somewhere and `expires_at` is computed from it on read → this is a shape fix only.
- If `expires_in` is stored raw and checked directly (e.g. `if expires_in > 0`) with no anchor to issuance time → this is a live correctness bug. Fix with priority.

**Fix:**
- Add `expires_at: Optional[float]` (absolute epoch timestamp) to the credential record, computed once at issuance/refresh time (`expires_at = time.time() + expires_in`).
- Add one shared `to_dict()` / `from_dict()` (or equivalent) on the credential record. Every store (file, keyring, env) uses it — no store hand-rolls its own field list.
- Confirm the refresh-transparency logic (attempt refresh when `expires_at` is within ~5 minutes) actually reads this field.

**Acceptance:** a unit test constructs a credential with a **past** `expires_at` and asserts a refresh is attempted before use; a **future** `expires_at` well outside the window is asserted to skip refresh. Serializer round-trips through every store without field-list duplication (grep for hand-rolled field lists in store files — should find none after the fix).

### 2. Verify (or cut) a tag with CI actually green *on that tag*

**Problem:** `v0.4.0` was cut before the release-workflow/smoke-job commit existed. `gh run list --branch v0.4.0` returns zero runs. The workflow is real and has been green since `v0.5.0`, through `v0.6.2`.

**Fix:** no code change needed. Confirm the current latest tag (audit found `v0.6.2` green) still passes CI today, and treat *that* tag — not `v0.4.0` — as the one anything external pins against. If nothing has shipped since, just re-confirm `v0.6.2` is still green. If work has landed since, cut a fresh tag and confirm its CI run is green before calling it done.

**Acceptance:** `gh run list --branch <tag>` shows a passing run for the tag actually being pinned.

---

## P1 — worth fixing, not blocking

### 3. Chain the interactive rungs into the same resolution path

**Problem:** `resolve_credential()` covers file → env → keyring (confirmed working, tested, live-verified). Device flow and PAT prompt exist as separate, manually-triggered UI actions rather than automatic fallback rungs of the same chain.

**Fix:** when `resolve_credential()` exhausts file/env/keyring with nothing found, it should trigger device flow (if the active provider supports it) or the PAT prompt, rather than requiring a separate manual trigger elsewhere in the UI.

**Acceptance:** a test that clears file/env/keyring and asserts `resolve_credential()` itself invokes the device-flow (or PAT-prompt) path, rather than returning empty and leaving it to a separate caller.

### 4. Gate GitHub's device-flow UI on the capability flag

**Problem:** `supports_device_flow` exists on the provider but GitHub's device-flow widget is hardwired rather than conditioned on it — so a future device-flow-capable provider (e.g. GitLab) won't get the UI automatically.

**Fix:** condition the existing device-flow widget on `provider.supports_device_flow` instead of being GitHub-specific. No new provider work — just remove the hardcoding.

**Acceptance:** temporarily flip the flag false on a test provider and confirm the widget doesn't render.

---

## Manual verification (not code — do this yourself, don't hand a token to any agent in chat)

- **Live success-path test:** with a real, scoped, throwaway PAT, run the G1 container smoke test end to end and confirm it prints the authenticated login (the audit only got as far as a 401 on a garbage token).
- **Desktop keyring re-test:** open GitPDM on a real desktop (macOS/Linux at minimum) with a real keyring and confirm save/load/delete still works post-fix. Windows currently only has a mocked test — worth a real pass if you have a Windows box handy.

---

## Out of scope for this pass

Everything else in `GITPDM_DEV_PLAN.md` (G3, G5, G6, G7, G8) — untouched by the audit, no action needed here.
