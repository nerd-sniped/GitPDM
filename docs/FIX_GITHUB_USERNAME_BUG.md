# GitHub Authentication Username Fix

## Bug Description

**Problem**: When multiple users authenticated with GitHub through GitPDM, all file locks showed the OAuth app owner's username ("nerd-sniped") instead of the individual authenticated user's username.

**Root Cause**: The authentication flow was storing the OAuth token BEFORE fetching the authenticated user's identity. This meant:

1. User authenticates and receives a token
2. Token is stored using `settings.load_github_login()` (which returns `None` or old value)
3. Credential is saved as `GitPDM:github.com:oauth` (generic key without username)
4. Identity verification happens later (async)
5. Username is saved to settings

Result: All tokens were stored under the same generic credential key, causing username confusion.

## Fix Applied

Modified `_on_token_received()` in [freecad/gitpdm/ui/github_auth.py](freecad/gitpdm/ui/github_auth.py):

### Changes:

1. **Fetch identity FIRST**: Immediately after receiving the token, use it to call GitHub's `/user` API endpoint to get the authenticated user's username

2. **Save username BEFORE token**: Store the username in settings before storing the token

3. **Use correct credential key**: Store the token with the authenticated username as part of the credential key: `GitPDM:github.com:USERNAME:oauth`

4. **Immediate lock handler refresh**: Refresh the lock handler immediately (no delay needed since we have the username)

5. **Remove duplicate identity verification**: Eliminated the delayed identity verification that was happening in the `finally` block

### Code Flow (After Fix):

```
1. User authenticates → receives token
2. Use token to fetch user identity from GitHub API
3. Save username to settings: settings.save_github_login(authenticated_username)
4. Store token with username: store.save(host, authenticated_username, token_response)
   → Creates: GitPDM:github.com:ACTUAL_USERNAME:oauth
5. Update UI with correct username
6. Refresh lock handler immediately
```

## Testing

To test the fix:

1. **Clear existing auth** (if needed):
   ```powershell
   .\clear_github_auth.ps1
   ```

2. **User 1 authenticates**:
   - Open FreeCAD/GitPDM
   - Click "Connect GitHub"
   - Authenticate with User1's GitHub account
   - Verify credential stored as: `GitPDM:github.com:user1:oauth`

3. **User 2 authenticates on different machine**:
   - Open FreeCAD/GitPDM on different computer
   - Click "Connect GitHub"
   - Authenticate with User2's GitHub account
   - Verify credential stored as: `GitPDM:github.com:user2:oauth`

4. **Verify lock ownership**:
   - User1 locks a file → shows "Locked by user1"
   - User2 sees the file → shows "Locked by user1" (not "nerd-sniped")
   - User2 locks different file → shows "Locked by user2"

## Impact

**Benefits**:
- ✅ Each user's locks show their own username
- ✅ Multiple users can authenticate independently
- ✅ No credential conflicts between users
- ✅ Correct ownership tracking for file locking

**Breaking Changes**: None (backward compatible)

**Migration**: Existing users will need to:
1. Disconnect from GitHub in GitPDM
2. Reconnect with their account

The old generic credential (`GitPDM:github.com:oauth`) will remain but won't be used.

## Related Files

- [freecad/gitpdm/ui/github_auth.py](freecad/gitpdm/ui/github_auth.py) - Main fix
- [freecad/gitpdm/auth/keys.py](freecad/gitpdm/auth/keys.py) - Credential key naming
- [freecad/gitpdm/github/identity.py](freecad/gitpdm/github/identity.py) - Identity fetching
- [freecad/gitpdm/ui/lock_handler.py](freecad/gitpdm/ui/lock_handler.py) - Lock username usage

## Date

Fixed: January 4, 2026
