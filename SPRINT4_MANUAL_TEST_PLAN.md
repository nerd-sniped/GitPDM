# Sprint 4 Manual Test Plan
GitPDM FreeCAD Workbench - Commit & Push Workflow Testing

## Test Environment Setup

### Prerequisites
- FreeCAD 1.0 installed
- Git installed and on PATH
- GitHub Desktop configured (for auth)
- Test repository with remote configured
- GitPDM workbench installed

### Test Repository Setup
Create a test repo with these conditions:
```bash
# Create test repo
git init test-gitpdm
cd test-gitpdm
git remote add origin <your-test-repo-url>

# Create initial commit
echo "Initial" > README.md
git add .
git commit -m "Initial commit"
git push -u origin main

# Create some test files
echo "Test content" > file1.txt
echo "Test content" > file2.txt
mkdir subdir
echo "Nested file" > subdir/nested.txt
```

---

## Test Suite

### TEST 1: Changes List Display
**Purpose:** Verify status parsing and changes list population

**Setup:**
1. Open FreeCAD
2. Open GitPDM dock panel
3. Select your test repository
4. Validate repo (should show OK)

**Steps:**
1. In your repo, modify `file1.txt` (add a line)
2. Create new file `untracked.txt`
3. Delete `file2.txt` using `git rm file2.txt`
4. Click "Refresh Status" in GitPDM

**Expected Results:**
- [ ] Working tree shows "Dirty" with counts
- [ ] Changes list populates with 3+ entries
- [ ] Modified file shows: `M  file1.txt` or similar
- [ ] Untracked file shows: `?? untracked.txt`
- [ ] Deleted file shows: `D  file2.txt`
- [ ] "Stage all changes" checkbox is enabled and checked
- [ ] Changes list is enabled (not grayed out)

**Notes:** _____________________

---

### TEST 2: Commit Button Enable States
**Purpose:** Verify button enable logic

**Steps:**
1. With changes present (from TEST 1):
2. Verify Commit button is DISABLED (no message yet)
3. Click in commit message box, type "Test"
4. Observe Commit button state
5. Clear the message (delete all text)
6. Observe Commit button state

**Expected Results:**
- [ ] Commit button disabled when message empty
- [ ] Commit button enabled when message has content AND changes present
- [ ] Commit button disabled when message cleared again

**Notes:** _____________________

---

### TEST 3: Basic Commit Workflow
**Purpose:** Verify successful commit creates commit and refreshes UI

**Setup:** 
- Ensure you have uncommitted changes
- No identity issues (git config user.name/email set)

**Steps:**
1. Type commit message: "Test commit for Sprint 4"
2. Verify "Stage all changes" is checked
3. Click "Commit" button
4. Observe button text change
5. Wait for completion

**Expected Results:**
- [ ] Commit button text changes to "Committing…" briefly
- [ ] Commit button becomes disabled during operation
- [ ] Operation completes without error
- [ ] Success message appears: "Commit created" (green/blue)
- [ ] Commit message box is CLEARED
- [ ] Changes list is CLEARED (empty)
- [ ] Working tree status shows "Clean"
- [ ] Ahead count increases by 1 (in Ahead/Behind display)
- [ ] Success message disappears after ~2 seconds
- [ ] Commit button re-enables if you type a new message

**Notes:** _____________________

---

### TEST 4: Commit with Empty Message
**Purpose:** Verify empty message validation

**Steps:**
1. Make a change: `echo "Change" >> file1.txt`
2. Click Refresh Status
3. Leave commit message box empty
4. Verify Commit button is disabled
5. Click in message box and press Space a few times (whitespace only)
6. Check Commit button state

**Expected Results:**
- [ ] Commit button remains disabled with whitespace-only message
- [ ] No commit is created

**Notes:** _____________________

---

### TEST 5: Nothing to Commit Error
**Purpose:** Verify handling when no changes present

**Setup:**
- Ensure working tree is clean (commit any changes first)

**Steps:**
1. Verify Changes list is empty
2. Verify Working tree shows "Clean"
3. Type commit message: "This should fail"
4. Commit button should be disabled (no changes)
5. Force-enable by making a change, clicking commit, but quickly
   reset the repo before staging completes (OPTIONAL - hard to time)

**Alternative (easier):**
1. Make a change, commit it normally
2. Without refreshing, try to commit again with same message
   (The UI won't let you - this is correct behavior)

**Expected Results:**
- [ ] Commit button disabled when no changes present
- [ ] No error dialogs appear (button prevents invalid state)

**Notes:** _____________________

---

### TEST 6: Missing Git Identity Error
**Purpose:** Verify friendly error when user.name/email not set

**Setup:**
1. Temporarily clear git identity:
   ```bash
   cd <test-repo>
   git config --local user.name ""
   git config --local user.email ""
   ```

**Steps:**
1. Make a change: `echo "Test" >> file1.txt`
2. Refresh status in GitPDM
3. Type commit message: "Test identity error"
4. Click Commit

**Expected Results:**
- [ ] Commit fails (as expected)
- [ ] A dialog appears with title "Git Identity Not Configured"
- [ ] Dialog message: "Git needs your name and email before committing"
- [ ] Dialog shows instructions with git config commands
- [ ] No commit is created

**Cleanup:**
```bash
git config --local user.name "Test User"
git config --local user.email "test@example.com"
```

**Notes:** _____________________

---

### TEST 7: Commit When Behind Upstream
**Purpose:** Verify non-blocking hint when behind

**Setup:**
1. Create a commit on remote (via GitHub web or another clone):
   - On GitHub, edit README.md and commit
   - Or in another clone: make change, commit, push
2. In GitPDM, click Fetch
3. Wait for fetch to complete
4. Verify "Behind" count is > 0

**Steps:**
1. Make a local change: `echo "Local" >> file1.txt`
2. Refresh status
3. Type commit message: "Local commit while behind"
4. Click Commit
5. Observe any warnings/messages

**Expected Results:**
- [ ] Commit proceeds successfully (NOT blocked)
- [ ] A non-error message appears (blue, not red):
      "You're N commits behind upstream. Consider Pull before pushing."
- [ ] Commit is created
- [ ] Message clears after commit
- [ ] Ahead count increases (now ahead AND behind)

**Notes:** _____________________

---

### TEST 8: Push Button Enable States
**Purpose:** Verify push button logic

**Scenarios to test:**

**A. When synced (ahead=0, behind=0):**
- [ ] Push button is DISABLED

**B. When ahead (ahead>0, behind=0):**
- [ ] Push button is ENABLED

**C. When behind (ahead=0, behind>0):**
- [ ] Push button is DISABLED (nothing to push)

**D. When diverged (ahead>0, behind>0):**
- [ ] Push button is ENABLED (will warn before pushing)

**E. When no upstream set (new branch):**
- [ ] Push button is ENABLED

**Notes:** _____________________

---

### TEST 9: Successful Push
**Purpose:** Verify push workflow and UI updates

**Setup:**
- Have at least 1 commit ahead (create one if needed)
- Behind count = 0 (pull first if needed)

**Steps:**
1. Verify Ahead count > 0
2. Verify Behind count = 0
3. Click Push button
4. Observe button text and state

**Expected Results:**
- [ ] Push button text changes to "Pushing…"
- [ ] Push button becomes disabled
- [ ] Other buttons (Fetch, Pull, Commit) disabled during push
- [ ] Push completes successfully
- [ ] Success message appears: "Push completed" (green/blue)
- [ ] Ahead count returns to 0
- [ ] Behind count remains 0
- [ ] Success message disappears after ~2 seconds
- [ ] Push button becomes disabled (nothing to push)

**ISSUE CHECK:**
- [ ] Commit message box is still empty (should be from previous commit)
- [ ] If commit message reappeared, THAT'S THE BUG

**Notes:** _____________________

---

### TEST 10: Push When Behind Upstream
**Purpose:** Verify warning dialog when trying to push while behind

**Setup:**
1. Have local commits (ahead > 0)
2. Have remote commits (behind > 0) - fetch after remote change
3. Verify you're in "diverged" state (ahead>0 AND behind>0)

**Steps:**
1. Verify Ahead/Behind shows both > 0
2. Click Push button
3. Read the warning dialog

**Expected Results:**
- [ ] Warning dialog appears immediately
- [ ] Title: "Behind Upstream"
- [ ] Message mentions: "You're N commits behind upstream. 
      Push may be rejected."
- [ ] Informative text: "Consider Pull first to sync with upstream."
- [ ] Two buttons: "Cancel" (default) and "OK"
- [ ] Clicking Cancel: dialog closes, no push attempted
- [ ] Clicking OK: push proceeds (may fail server-side if rejected)

**Notes:** _____________________

---

### TEST 11: Push Without Upstream (New Branch)
**Purpose:** Verify auto-upstream detection and `-u` flag

**Setup:**
1. Create a new local branch:
   ```bash
   cd <test-repo>
   git checkout -b test-new-branch
   echo "New branch" >> newfile.txt
   git add .
   git commit -m "New branch commit"
   ```
2. Refresh GitPDM (repo might need reselection)

**Steps:**
1. Verify Upstream shows "(not set)" or similar
2. Verify Ahead/Behind shows "(unknown)" or error
3. Make a commit in GitPDM
4. Click Push

**Expected Results:**
- [ ] Push button is enabled (even without upstream)
- [ ] Push executes: `git push -u origin HEAD`
- [ ] Push succeeds and sets upstream
- [ ] After push, upstream shows `origin/test-new-branch`
- [ ] Ahead/Behind now computes correctly

**Notes:** _____________________

---

### TEST 12: Push Authentication Failure
**Purpose:** Verify auth error handling (simulated)

**Setup (OPTIONAL - may be hard to simulate):**
- Sign out of GitHub Desktop
- Or use HTTPS repo without credential helper

**Steps:**
1. Make and commit a change
2. Click Push
3. If auth fails, observe error handling

**Expected Results:**
- [ ] Push error dialog appears
- [ ] Title: "Push Failed"
- [ ] Message indicates auth/permission issue
- [ ] Suggests: "Sign in via GitHub Desktop, then try again"
- [ ] Details section shows raw git error
- [ ] "Copy Details" button works

**Notes:** _____________________

---

### TEST 13: Push Rejection (Non-Fast-Forward)
**Purpose:** Verify handling of rejected push

**Setup:**
1. Have local commits (ahead > 0)
2. Have different remote commits (behind > 0) that conflict
3. Attempt to push anyway (click OK on warning)

**Steps:**
1. Click Push (with behind > 0)
2. Click OK on warning dialog
3. Wait for push to fail

**Expected Results:**
- [ ] Push fails with rejection error
- [ ] Error dialog appears
- [ ] Error code: "REJECTED"
- [ ] Message suggests: "Consider Pull before Push"
- [ ] Raw error in details section

**Notes:** _____________________

---

### TEST 14: Multi-File Commit
**Purpose:** Verify staging and committing multiple files

**Steps:**
1. Modify 3-5 files:
   ```bash
   echo "A" >> file1.txt
   echo "B" >> file2.txt
   echo "C" > file3.txt
   echo "D" > subdir/file4.txt
   mkdir newdir
   echo "E" > newdir/file5.txt
   ```
2. Refresh status in GitPDM
3. Verify changes list shows all files
4. Type message: "Multi-file commit"
5. Ensure "Stage all changes" is checked
6. Click Commit

**Expected Results:**
- [ ] All 5 files appear in changes list
- [ ] Commit succeeds
- [ ] All changes included in commit
- [ ] Verify with: `git show --stat` (should list all files)

**Notes:** _____________________

---

### TEST 15: Rename Detection
**Purpose:** Verify porcelain -z handles renames

**Setup:**
```bash
cd <test-repo>
git mv file1.txt file1-renamed.txt
```

**Steps:**
1. Refresh status in GitPDM
2. Check changes list

**Expected Results:**
- [ ] Changes list shows rename, format like:
      `R  file1.txt -> file1-renamed.txt`
- [ ] Commit and verify rename tracked correctly

**Notes:** _____________________

---

### TEST 16: Unicode and Special Characters
**Purpose:** Verify porcelain -z handles non-ASCII paths

**Setup:**
```bash
cd <test-repo>
echo "Test" > "file with spaces.txt"
echo "Test" > "filé-unicode.txt"
echo "Test" > "file'quote.txt"
```

**Steps:**
1. Refresh status
2. Check changes list displays correctly
3. Commit with message: "Test special chars"
4. Verify commit succeeds

**Expected Results:**
- [ ] All files appear correctly in changes list
- [ ] No parsing errors
- [ ] Commit succeeds with all files

**Notes:** _____________________

---

### TEST 17: Concurrent Operations Prevention
**Purpose:** Verify buttons disabled during operations

**Steps:**
1. Make changes and refresh
2. Click Fetch button
3. While fetching, try to click:
   - Pull button
   - Commit button
   - Push button
4. Repeat with each operation type

**Expected Results:**
- [ ] During Fetch: Pull, Commit, Push all disabled
- [ ] During Pull: Fetch, Commit, Push all disabled
- [ ] During Commit: Fetch, Pull, Push all disabled
- [ ] During Push: Fetch, Pull, Commit all disabled
- [ ] Buttons re-enable after operation completes

**Notes:** _____________________

---

### TEST 18: Status Message Clearing
**Purpose:** Verify status messages appear and auto-clear

**Operations to test:**
1. Successful Fetch
2. Successful Pull  
3. Successful Commit
4. Successful Push

**Expected Results:**
- [ ] Each operation shows success message (blue/green text)
- [ ] Message appears in Status section below Ahead/Behind
- [ ] Message auto-clears after ~2-3 seconds
- [ ] Error messages (red) remain until next operation

**Notes:** _____________________

---

### TEST 19: Rapid Sequential Operations
**Purpose:** Verify job runner handles queuing correctly

**Steps:**
1. Make changes
2. Type commit message
3. Click Commit
4. IMMEDIATELY click Fetch (before commit finishes)
5. Observe behavior

**Expected Results:**
- [ ] Commit operation completes first
- [ ] Fetch operation queued and runs after commit
- [ ] No crashes or UI freezes
- [ ] Both operations complete successfully

**Notes:** _____________________

---

### TEST 20: Stage All Checkbox (Future Enhancement)
**Purpose:** Document expected behavior for selective staging

**Current State:**
- Checkbox exists and is checked by default
- Always stages all files (selective staging not implemented)

**Future Test (when implemented):**
1. Uncheck "Stage all changes"
2. Select specific files in changes list
3. Commit should stage only selected files

**Expected Results (CURRENT SPRINT):**
- [ ] Checkbox is visible
- [ ] Checkbox is checked by default
- [ ] Checkbox becomes enabled when changes present
- [ ] Unchecking does NOT change behavior (still stages all)

**Notes:** _____________________

---

## Regression Tests (Sprint 1-3 Features)

### TEST R1: Fetch Still Works
- [ ] Fetch button enables when repo valid + has remote
- [ ] Clicking Fetch runs successfully
- [ ] Last fetch timestamp updates
- [ ] Ahead/Behind recomputes after fetch

### TEST R2: Pull Still Works  
- [ ] Pull button enables when behind > 0
- [ ] Pull succeeds with ff-only
- [ ] Warning dialog appears if local changes present
- [ ] Pull error dialog shows on ff failure

### TEST R3: Repo Selection
- [ ] Browse button opens folder dialog
- [ ] Typing path validates on Enter
- [ ] Invalid repos show "Invalid" status
- [ ] Saved repo path persists across FreeCAD restarts

### TEST R4: Git Availability Check
- [ ] Git version displays in System section
- [ ] Missing git shows "Not found" in red

---

## Bug Report Template

If you find issues during testing, document them:

**Bug ID:** _______________
**Test Case:** TEST __
**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**

**Actual Behavior:**

**Screenshots/Logs:**

**FreeCAD Version:**
**Git Version:**
**OS:**

---

## Known Issues to Check

1. **Commit message not clearing after push:**
   - The commit message should remain EMPTY after commit
   - If it reappears after push, this is a bug
   - Check if `self.commit_message.clear()` is being called

2. **Status messages not auto-clearing:**
   - Verify QTimer.singleShot is working
   - Check console for timer-related errors

3. **Button states after errors:**
   - Verify buttons re-enable after errors
   - Check if `_update_button_states()` called in all paths

---

## Performance Notes

- Commit/Push operations should complete in < 5 seconds for typical repos
- Changes list should populate instantly for < 100 files
- UI should never freeze during git operations
- Job runner should prevent parallel git commands

---

## Test Summary

Total Tests: 20 core + 4 regression = 24 tests

Completion Checklist:
- [ ] All core tests (TEST 1-20) completed
- [ ] All regression tests (TEST R1-R4) completed
- [ ] No crashes observed
- [ ] No UI freezes observed
- [ ] All buttons behave as expected
- [ ] All error paths tested
- [ ] Performance acceptable

**Testing Date:** _______________
**Tester:** _______________
**Overall Result:** PASS / FAIL / PARTIAL

**Critical Issues Found:** _______________

**Minor Issues Found:** _______________

**Recommendations:** _______________
