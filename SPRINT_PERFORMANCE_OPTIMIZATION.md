# Performance Optimization Sprint Plan

**Goal**: Eliminate UI blocking operations and improve responsiveness by moving synchronous git operations to background workers.

**Current State**: Many git operations run synchronously on the UI thread, causing freezes during repository validation, status refresh, and branch operations.

**Target State**: All heavy operations run asynchronously via job_runner, with UI updates only when results are ready.

---

## Sprint PERF-1: Core Status Refresh (HIGH PRIORITY)

**Objective**: Move the most frequently-called blocking operations to background workers.

**Why First**: `_refresh_status_views()` is called after every document save and git operation, making it the #1 UI responsiveness issue.

### Tasks

#### 1.1 Make `_refresh_status_views()` Async
**File**: `freecad_gitpdm/ui/panel.py` (line ~1831)
**Current**: Synchronously calls `status_summary()` and `status_porcelain()` on UI thread
**Change**: 
- Create background job that fetches status
- Update UI labels when job completes
- Add loading state indicator

**Acceptance Criteria**:
- ✓ Status refresh doesn't block UI
- ✓ UI shows "Refreshing..." state during load
- ✓ Auto-refresh after save still works
- ✓ No race conditions if multiple refreshes triggered

**Impact**: **CRITICAL** - Fixes most noticeable performance issue

---

#### 1.2 Make `_update_upstream_info()` Async
**File**: `freecad_gitpdm/ui/panel.py` (line ~1731)
**Current**: Synchronously calls `get_ahead_behind_with_upstream()` which runs `git rev-list`
**Change**:
- Move ahead/behind calculation to background job
- Update upstream labels when complete
- Cache results to avoid redundant calls

**Acceptance Criteria**:
- ✓ Ahead/Behind counters don't block UI
- ✓ Shows "calculating..." or cached value during load
- ✓ Works correctly with status refresh

**Impact**: **HIGH** - Heavy git operation on every status refresh

---

#### 1.3 Optimize `_update_button_states()` to Avoid Redundant Git Calls
**File**: `freecad_gitpdm/ui/panel.py` (line ~1900)
**Current**: Calls `has_remote()` synchronously on every button state update
**Change**:
- Use cached `_cached_has_remote` consistently
- Only refresh remote status during status refresh job
- Avoid calling git during typing/UI events

**Acceptance Criteria**:
- ✓ Button state updates are instant (<5ms)
- ✓ No git subprocess calls during typing
- ✓ Remote status stays accurate

**Impact**: **MEDIUM** - Improves responsiveness during text input

---

**Sprint PERF-1 Success Metrics**:
- Document save → status refresh perceived as instant (<100ms)
- No UI freezes during normal operations
- Status updates appear within 500ms of git operation completion

**Estimated Effort**: 2-3 days

---

## Sprint PERF-2: Repository Validation & Selection (MEDIUM PRIORITY)

**Objective**: Make repository path validation and selection non-blocking.

**Why Second**: Users experience 1-2 second freezes when browsing/selecting repos, affecting first-time setup UX.

### Tasks

#### 2.1 Make Repository Validation Async
**File**: `freecad_gitpdm/ui/repo_validator.py` (entire validation flow)
**Current**: Sequential synchronous calls to:
- `get_repo_root()`
- `current_branch()`
- `has_remote()`
- Full status refresh

**Change**:
- Create single background validation job
- Chain all git queries in worker thread
- Update UI progressively as results arrive
- Show validation progress indicator

**Acceptance Criteria**:
- ✓ Repo path field doesn't freeze on blur
- ✓ Browse button returns immediately
- ✓ Validation results appear within 1 second
- ✓ Clear error messages if validation fails

**Impact**: **HIGH** - Improves new user experience significantly

---

#### 2.2 Defer Panel Initialization Heavy Operations
**File**: `freecad_gitpdm/ui/panel.py` (`_deferred_initialization`, line ~300)
**Current**: Runs git availability check synchronously
**Change**:
- Move git check to background
- Defer repo validation to background
- Show "Loading..." state during init
- Panel becomes interactive immediately

**Acceptance Criteria**:
- ✓ Panel opens instantly (<50ms)
- ✓ Git check happens in background
- ✓ Repo validation doesn't block panel display

**Impact**: **MEDIUM** - Panel opens faster, better perceived performance

---

#### 2.3 Background Load of Saved Repo Path
**File**: `freecad_gitpdm/ui/panel.py` (`_load_saved_repo_path`)
**Current**: Synchronously validates saved path on startup
**Change**:
- Load and display path immediately
- Validate in background
- Update status when validation completes

**Acceptance Criteria**:
- ✓ Saved path appears instantly
- ✓ Validation happens after panel visible
- ✓ Handles invalid saved paths gracefully

**Impact**: **LOW** - Minor startup time improvement

---

**Sprint PERF-2 Success Metrics**:
- Panel initialization <100ms
- Repository selection/validation non-blocking
- Browse folder dialog opens instantly

**Estimated Effort**: 2-3 days

---

## Sprint PERF-3: Branch Operations (MEDIUM PRIORITY) ✅ COMPLETE

**Objective**: Make branch listing and operations non-blocking.

**Why Third**: Less frequent than status refresh, but still affects user experience when working with branches.

### Tasks

#### 3.1 Async Branch List Population ✅ COMPLETE
**File**: `freecad_gitpdm/ui/branch_ops.py` (`refresh_branch_list`)
**Current**: Synchronously calls:
- `list_local_branches()`
- `list_remote_branches()`

**Change**:
- Load branches in background job
- Show "Loading branches..." in combo
- Update combo box when load completes
- Cache branch list, refresh only on explicit refresh/fetch

**Implementation**:
- Added `_is_loading_branches` flag to prevent race conditions
- Created `_load_branches()` background callable
- Shows "Loading branches…" state during loading
- Added `_on_branch_list_loaded()` and `_on_branch_list_load_error()` callbacks
- Updates busy state to include branch loading

**Acceptance Criteria**:
- ✓ Branch combo doesn't freeze on click
- ✓ Branches load in background
- ✓ Current branch always displays correctly
- ✓ Refresh after fetch/pull/checkout

**Impact**: **MEDIUM** - Improves branch switching UX

---

#### 3.2 Async Branch Operation Result Handling ✅ COMPLETE
**File**: `freecad_gitpdm/ui/branch_ops.py` (various operations)
**Current**: Some operations already async, but results processed synchronously
**Change**:
- Ensure create/switch/delete all use job_runner
- Refresh UI only after operation completes
- Show progress during operations

**Implementation**:
- Made `new_branch_clicked()` async with `_create_branch()` callable
- Added `_on_branch_created()` and `_on_branch_create_error()` callbacks
- Made `delete_branch_clicked()` async with `_delete_branch()` callable
- Added `_on_branch_deleted()` and `_on_branch_delete_error()` callbacks
- Added `_force_delete_branch()` helper for unmerged branch handling
- All branch operations now non-blocking via job_runner

**Acceptance Criteria**:
- ✓ All branch operations non-blocking
- ✓ Clear feedback during operations
- ✓ UI updates correctly after completion

**Impact**: **LOW** - Most already async, just consistency improvements

---

**Sprint PERF-3 Success Metrics**:
- Branch dropdown opens instantly
- Branch operations provide immediate feedback
- No freezes during branch management

**Estimated Effort**: 1-2 days
**Actual Effort**: <1 hour

---

## Sprint PERF-4: GitHub Integration & Polish (LOW PRIORITY)

**Objective**: Optimize GitHub API operations and final polish.

**Why Last**: Already mostly async, just needs consistency and optimization.

### Tasks

#### 4.1 Defer GitHub Connection Status Check
**File**: `freecad_gitpdm/ui/github_auth.py` (`refresh_connection_status`, line ~44)
**Current**: Synchronously reads credential store during panel init
**Change**:
- Move to background job
- Show "Checking..." state initially
- Update when credential check completes

**Acceptance Criteria**:
- ✓ Credential check doesn't block panel init
- ✓ GitHub status updates within 200ms
- ✓ Doesn't slow down panel opening

**Impact**: **LOW** - Credential store is usually fast, but good practice

---

#### 4.2 Optimize Auto-Verify Identity Cooldown
**File**: `freecad_gitpdm/ui/github_auth.py` (`maybe_auto_verify_identity`, line ~185)
**Current**: Already async, but datetime parsing happens on UI thread
**Change**:
- Move cooldown check to background
- Simplify logic
- Consider caching verify result longer

**Acceptance Criteria**:
- ✓ No UI impact from auto-verify
- ✓ Cooldown works correctly
- ✓ Doesn't spam GitHub API

**Impact**: **VERY LOW** - Already mostly optimized

---

#### 4.3 Add Global Loading State Indicator
**File**: `freecad_gitpdm/ui/panel.py`
**Current**: Some operations show busy bar, inconsistent
**Change**:
- Unified loading indicator for all async operations
- Show what's currently running
- Cancel button for long operations (optional)

**Acceptance Criteria**:
- ✓ User always knows when operations are running
- ✓ Consistent loading UX across all operations
- ✓ No confusion about application state

**Impact**: **MEDIUM** - UX polish, helps users understand what's happening

---

#### 4.4 Implement Operation Debouncing
**File**: `freecad_gitpdm/ui/panel.py` (various locations)
**Current**: Some debouncing exists but inconsistent
**Change**:
- Debounce status refresh after rapid saves
- Debounce button state updates during typing
- Avoid duplicate concurrent operations

**Acceptance Criteria**:
- ✓ Rapid saves don't trigger multiple status refreshes
- ✓ Typing doesn't cause lag
- ✓ Operations queue intelligently

**Impact**: **MEDIUM** - Reduces unnecessary work

---

**Sprint PERF-4 Success Metrics**:
- All operations provide clear feedback
- No redundant API calls or git operations
- Professional, responsive feel throughout

**Estimated Effort**: 2-3 days

---

## Architecture Guidelines for All Sprints

### Pattern to Follow (from repo_picker.py, line 193):
```python
# GOOD - Async pattern using job_runner
self._job_runner.run_callable(
    "github_list_repos",
    lambda: list_repos(client, per_page=100, max_pages=10),
    on_success=self._on_repos_loaded,
    on_error=self._on_repos_error,
)
```

### Pattern to Avoid:
```python
# BAD - Synchronous blocking call on UI thread
status = self._git_client.status_summary(repo_root)  # BLOCKS!
self._display_working_tree_status(status)
```

### Principles:
1. **Never call git client methods directly from UI event handlers**
2. **Always use job_runner for subprocess operations**
3. **Show loading state before starting async operation**
4. **Update UI in success/error callbacks**
5. **Handle race conditions (operations completing out of order)**
6. **Cache results when appropriate to avoid redundant calls**
7. **Debounce rapid operations (saves, typing)**

---

## Testing Strategy

### For Each Sprint:
1. **Manual Testing**:
   - Open panel → should be instant
   - Select repo → should not freeze
   - Save document → should not freeze
   - Click buttons → immediate feedback

2. **Performance Benchmarks**:
   - Measure time from user action to UI update
   - Target: <100ms for any UI interaction
   - Background operations can take longer, but shouldn't block

3. **Stress Testing**:
   - Large repos (10k+ files)
   - Slow networks (GitHub operations)
   - Rapid repeated actions (spam save)

4. **Edge Cases**:
   - Concurrent operations
   - Operation failures
   - Network timeouts
   - Invalid repo states

---

## Rollout Plan

1. **Sprint PERF-1**: Most impactful, test thoroughly before proceeding
2. **Sprint PERF-2**: Builds on PERF-1 patterns
3. **Sprint PERF-3**: Independent, can overlap with PERF-2
4. **Sprint PERF-4**: Polish and optimization, can be ongoing

**Total Estimated Effort**: 7-11 days across 4 sprints

**Risk Level**: MEDIUM
- Main risk is race conditions with async operations
- Mitigation: Careful testing, operation queuing, state management

**User Impact**: HIGH - Significantly improved responsiveness and UX
