# Testing Instructions for GitHub Username Fix

## Before Testing

Run the cleanup script to remove any old credentials:
```powershell
.\clear_github_auth.ps1
```

## Test Scenario 1: Single User Authentication

1. **Open FreeCAD** with GitPDM installed
2. **Open GitPDM panel**
3. **Click "Connect GitHub"**
4. **Authenticate** with your GitHub account in the browser
5. **Verify success**:
   - Should see: "Signed in as YOUR_USERNAME"
   - Check Windows Credential Manager:
     ```powershell
     cmdkey /list | Select-String "GitPDM"
     ```
   - Should show: `GitPDM:github.com:YOUR_USERNAME:oauth`

## Test Scenario 2: File Locking with Correct Username

1. **Open a GitPDM repository**
2. **Check current username detection**:
   - Run in FreeCAD Python console:
     ```python
     from freecad.gitpdm.core import settings
     print(f"GitHub Login: {settings.load_github_login()}")
     ```
   - Should print YOUR username, not "nerd-sniped"

3. **Create or lock a test file**
4. **Verify lock shows your username**:
   ```powershell
   cd path\to\repo
   git lfs locks
   ```
   - Should show YOUR username as the owner

## Test Scenario 3: Multiple Users (Different Computers)

### Computer 1 (User A):
1. Authenticate as User A
2. Lock a file
3. Commit and push

### Computer 2 (User B):
1. Authenticate as User B  
2. Pull the repository
3. Check file locks:
   - Should see "Locked by UserA" (not "nerd-sniped")
4. Try to edit locked file
   - Should warn: "File locked by UserA"
5. Lock a different file
   - Should show "Locked by UserB" (your username)

## Test Scenario 4: Re-authentication

1. **Disconnect from GitHub** in GitPDM
2. **Re-connect** with the same account
3. **Verify**:
   - Should authenticate as the same user
   - Should show correct username in locks
   - Old credential should remain but unused

## Checking Credentials in Windows

To see all GitPDM credentials:
```powershell
cmdkey /list | Select-String "GitPDM"
```

To remove a specific credential (if needed):
```powershell
cmdkey /delete:"GitPDM:github.com:username:oauth"
```

## Expected Results

✅ **Each user authenticates with their own GitHub account**
✅ **Tokens are stored separately per user** (different credential keys)
✅ **File locks show the actual lock owner's username**
✅ **No "nerd-sniped" appearing as lock owner** (unless nerd-sniped actually locks the file)
✅ **Lock handler uses authenticated user's username**

## Debugging

If you see "nerd-sniped" as the lock owner:

1. Check FreeCAD settings:
   ```python
   from freecad.gitpdm.core import settings
   print(f"GitHub Login: {settings.load_github_login()}")
   print(f"GitHub Connected: {settings.load_github_connected()}")
   ```

2. Check credential store:
   ```powershell
   cmdkey /list | Select-String "GitPDM"
   ```

3. Check git config:
   ```powershell
   git config user.name
   git config user.email
   ```

4. Run the lock debug script:
   - In FreeCAD Python console, paste contents of [test_lock_check.py](test_lock_check.py)
   - Run: `test_lock_logic()`

## Known Issues

- Old generic credentials (`GitPDM:github.com:oauth`) may still exist but won't be used
- Users must disconnect and reconnect to get the fix

## Support

If you still see incorrect usernames after following these steps, check:
- [FIX_GITHUB_USERNAME_BUG.md](FIX_GITHUB_USERNAME_BUG.md) for technical details
- FreeCAD logs for authentication errors
- Windows Credential Manager for credential conflicts
