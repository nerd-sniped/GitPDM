# File Change Detection - Auto-Refresh Feature

## Problem Solved

GitPDM was only detecting changes to FreeCAD documents (`.FCStd` files) when they were saved. **New files or changes to non-FreeCAD files** (Python files, text files, images, etc.) were not automatically detected and required manually clicking the Refresh button.

## Solution

Added an **auto-refresh timer** that checks for file system changes every 5 seconds.

### How It Works

```
┌──────────────────────────────────────────┐
│  File Change Detection (2 Methods)      │
└──────────────────────────────────────────┘

Method 1: DocumentObserver (Immediate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Triggers: When .FCStd file is saved in FreeCAD
• Latency: Immediate (500ms debounce)
• Scope: Only FreeCAD documents
• Performance: No overhead (event-driven)

Method 2: Auto-Refresh Timer (Periodic) ✨ NEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Triggers: Every 5 seconds
• Latency: Up to 5 seconds
• Scope: ALL file changes (new files, edits, deletes)
• Performance: Minimal (quick git status check)
```

### What Gets Detected

The auto-refresh will now detect:

- ✅ **New files** created in the repository
- ✅ **Modified files** (any file type)
- ✅ **Deleted files**
- ✅ **Renamed files**
- ✅ **Files created outside FreeCAD** (text editors, etc.)
- ✅ **Files modified by other programs**

### When Refresh Happens

Auto-refresh runs every 5 seconds **IF:**
- ✅ A repository is loaded
- ✅ No other operations are in progress (commit, push, etc.)
- ✅ Previous refresh has completed
- ✅ Auto-refresh is enabled (default: ON)

Auto-refresh is **skipped** if:
- ❌ No repository selected
- ❌ Git operation in progress
- ❌ Previous refresh still running

## Technical Implementation

### Changes Made

1. **panel.py** - Added auto-refresh timer:
   ```python
   # Timer setup (5 second interval)
   self._auto_refresh_timer = QtCore.QTimer(self)
   self._auto_refresh_timer.setInterval(5000)
   self._auto_refresh_timer.timeout.connect(self._on_auto_refresh_tick)
   self._auto_refresh_enabled = True  # Enabled by default
   ```

2. **panel.py** - Auto-refresh method:
   ```python
   def _on_auto_refresh_tick(self):
       """Periodic check for file system changes."""
       if not self._current_repo_root or self._is_refreshing_status:
           return
       
       if self._active_operations:
           return  # Skip if busy
       
       self._refresh_status_views(self._current_repo_root)
   ```

3. **panel.py** - Start/stop timer with repository:
   - Starts when repository is loaded
   - Stops when panel is closed
   - Restarts when repository changes

4. **document_observer.py** - Clarified documentation:
   - Added note that it only detects .FCStd saves
   - Explained users need auto-refresh for other files

## Performance Impact

### Resource Usage

| Aspect | Impact |
|--------|--------|
| **CPU** | Minimal - `git status` is fast (~50ms) |
| **Memory** | Negligible - no data cached |
| **Disk I/O** | Low - git reads index, not full scan |
| **Network** | None - local operations only |

### Optimization Features

- **Concurrent protection**: Won't run if already refreshing
- **Operation detection**: Skips if commit/push in progress
- **Smart scheduling**: 5 seconds is long enough to avoid hammering

### Typical Timing

```
User creates file → [0-5 seconds] → Auto-refresh detects it
FreeCAD save     → [~500ms]      → DocumentObserver detects it
Manual refresh   → [immediate]   → User-triggered refresh
```

## User Experience

### Before (Without Auto-Refresh)

```
1. Create new file in repository
2. File is not shown in Changes list ❌
3. User must click Refresh button manually
4. File appears in Changes list ✓
```

### After (With Auto-Refresh)

```
1. Create new file in repository
2. Within 5 seconds, file appears in Changes list ✓
3. No manual action required ✨
```

## Configuration

### Disabling Auto-Refresh (If Needed)

Currently auto-refresh is always enabled. To disable it in the future:

```python
# In panel.py __init__:
self._auto_refresh_enabled = False  # Disable auto-refresh

# Or stop the timer:
self._auto_refresh_timer.stop()
```

### Adjusting Interval

```python
# Change from 5 seconds to something else:
self._auto_refresh_timer.setInterval(10000)  # 10 seconds
self._auto_refresh_timer.setInterval(2000)   # 2 seconds (more responsive)
```

## Future Enhancements

Possible improvements:

1. **User preference**: Add setting to enable/disable auto-refresh
2. **Adjustable interval**: Let users choose refresh frequency
3. **File system watcher**: Use QFileSystemWatcher for instant detection
4. **Smart throttling**: Increase interval when idle, decrease when active

## Troubleshooting

### Changes Still Not Detected?

**Check repository status:**
```bash
cd /path/to/repo
git status
```

If git sees the files but GitPDM doesn't:
- Wait up to 5 seconds for auto-refresh
- Click Refresh button manually
- Check FreeCAD console for errors

**Check if timer is running:**
Look for these log messages:
```
INFO: Auto-refresh timer started (5 second interval)
DEBUG: Auto-refresh: checking for file changes
```

### Performance Issues?

If auto-refresh is causing problems:
1. Check repository size (very large repos may be slow)
2. Increase interval to 10-15 seconds
3. Disable auto-refresh and use manual refresh

## Summary

✅ **Problem Solved**: New files and non-FreeCAD changes now detected automatically

✅ **Low Impact**: Minimal performance overhead

✅ **User Friendly**: No manual refresh needed for most workflows

✅ **Robust**: Skips refresh when busy, prevents concurrent operations

✅ **Fast**: 5 second detection for all file changes

---

**Result**: Users can now create files in their IDE, text editor, or file manager, and see them appear in GitPDM automatically within 5 seconds!
