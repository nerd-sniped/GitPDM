# GitHub OAuth Device Flow

## Overview

GitPDM uses GitHub's **OAuth Device Flow** to authenticate users
without requiring a web browser redirect or terminal input. This
flow is ideal for desktop applications like FreeCAD addons.

## Why OAuth Device Flow?

The Device Flow provides a user-friendly authentication experience:

1. **No browser redirect**: GitPDM displays a code that users enter
   on GitHub's website in their preferred browser.
2. **Cross-platform**: Works consistently across Windows, macOS,
   and Linux.
3. **No embedded browser**: Avoids complexity of embedded web views
   or platform-specific browser integration.
4. **Secure**: No client secrets exposed in the addon code.

## Authentication Process

When you click "Connect GitHub" in GitPDM:

1. GitPDM requests a device code from GitHub.
2. A dialog displays:
   - A user code (e.g., `ABCD-1234`)
   - A verification URL (`https://github.com/login/device`)
3. You open the URL in your browser and enter the user code.
4. After authorizing GitPDM, the addon receives an access token.
5. The token is securely stored in your OS credential manager.

## Token Storage

GitPDM stores OAuth tokens locally using your operating system's
credential manager:

- **Windows**: Windows Credential Manager
- **macOS**: Keychain
- **Linux**: Secret Service API (gnome-keyring, kwallet, etc.)

**Important**: Tokens are stored locally on your machine. GitPDM
never sends your tokens to any server except GitHub's API.

## Requested Scopes

GitPDM requests the following OAuth scopes:

### `read:user`
- **Purpose**: Read your GitHub profile (username, email)
- **Used for**: Displaying your connected account name
- **Access**: Read-only access to public profile information

### `repo` ⚠️
- **Purpose**: Access private and public repositories
- **Used for**:
  - **Creating repositories** via GitHub API
  - **Pushing commits** (Git uses OAuth token for authentication)
  - **Accessing private repositories**
  - Fetching repository metadata
  - Future: Creating releases, managing pull requests
- **Access**: Read/write access to ALL your repository contents

#### Why `repo` Scope is Required

GitPDM needs the `repo` scope because:

1. **Git Push Authentication**: When GitPDM pushes commits to GitHub via HTTPS,
   Git uses your OAuth token as a password. GitHub **requires the `repo` scope**
   for push operations, even to public repositories.

2. **Repository Creation**: Creating new repositories via the GitHub API requires
   the `repo` scope.

3. **Private Repository Support**: If you want to back up FreeCAD files to private
   repositories, the `repo` scope is mandatory. The alternative `public_repo` scope
   only works with public repositories.

#### Security Implications

The `repo` scope grants **broad access** to your repositories:

- ✅ **Read** all public and private repository contents
- ✅ **Write** to all repositories (create, modify, delete files)
- ✅ **Create** new repositories
- ✅ **Manage** repository settings (collaborators, webhooks, etc.)

**What GitPDM Actually Does**:
- Creates repositories (only when you explicitly use "New Repository")
- Pushes commits (only when you click "Commit & Push")
- Lists your repositories (read-only)
- Fetches metadata (read-only)

GitPDM **never** modifies repositories without your explicit action.

#### Limiting Access to Specific Repositories

**Current Limitation**: OAuth Apps (what GitPDM currently uses) grant access to
**ALL repositories** the user owns or collaborates on. There's no way to limit
an OAuth App to specific repositories.

**Solution: GitHub Apps** ✨

GitHub offers an alternative architecture called **GitHub Apps** that DOES support
repository-specific permissions:

##### How GitHub Apps Work:

1. User "installs" the app and **selects specific repositories** to grant access
2. App only receives tokens for those selected repositories
3. User can add/remove repositories at any time from GitHub Settings
4. Much more granular control: read-only vs write access per repository

##### Why GitPDM Doesn't Use GitHub Apps (Yet):

- **More complex setup**: Requires webhook URLs and app hosting infrastructure
- **Installation friction**: Users must "install" rather than just "authorize"
- **Device Flow limitations**: GitHub Apps have limited Device Flow support
- **Migration complexity**: Would break existing OAuth connections

##### We're Considering a Hybrid Approach:

- **Option 1: Default OAuth Mode** (current) - Quick setup, all repos
- **Option 2: GitHub App Mode** (future) - More setup, per-repo control

**Want per-repository access?** [Vote on this GitHub issue](https://github.com/nerd-sniped/GitPDM/issues/XX)
or contribute! The architecture change is substantial but achievable.

#### Current Mitigation Strategies

If you're uncomfortable with the `repo` scope today:

1. **Dedicated Account**: Create a separate GitHub account with only the repos
   you want GitPDM to access
2. **Connect Only When Needed**: Use "Disconnect" when not actively pushing/pulling
3. **Repository Segregation**: Keep sensitive repos in a separate GitHub account
4. **Monitor Activity**: Check GitHub's "Settings → Security → Recent activity"
   for unexpected API access
5. **Review Source Code**: GitPDM is open-source - verify what it actually does
   at [github.com/nerd-sniped/GitPDM](https://github.com/nerd-sniped/GitPDM)

## Revoking Access

You can revoke GitPDM's access at any time:

1. Visit GitHub Settings: **Settings → Applications → Authorized
   OAuth Apps**
2. Find "GitPDM" in the list.
3. Click "Revoke" to remove access.

After revoking access:
- GitPDM will show "Not connected" status.
- Locally stored tokens will no longer work.
- Use "Disconnect" in GitPDM to clear local credentials.

## Privacy & Security

- **No password storage**: GitPDM never asks for or stores your
  GitHub password.
- **Token expiration**: OAuth tokens do not expire by default, but
  you can revoke them anytime.
- **Limited scope**: GitPDM only requests necessary permissions.
- **Local storage**: Tokens are stored using OS-level encryption.

## Troubleshooting

### "GitHub OAuth not configured"

This message appears when GitPDM's OAuth client ID is not set.
This is expected in Sprint OAUTH-0 (preparation sprint). OAuth
authentication will be enabled in Sprint OAUTH-1.

### Connection issues

If "Connect GitHub" fails:
- Check your internet connection.
- Ensure you completed the device flow on GitHub's website.
- Try "Disconnect" and reconnect.

### "Token missing required scopes" error

If you see "Token missing required scopes: read:user, repo" even though
GitHub shows the authorization was successful:

**Root Cause**: GitHub reuses existing OAuth authorizations. If you
previously authorized GitPDM (on this or another computer) with incomplete
permissions, GitHub may return that old authorization instead of creating
a new one with correct scopes.

**Solution**:
1. Go to **GitHub Settings → Applications → Authorized OAuth Apps**
2. Find **"GitPDM"** in the list
3. Click **"Revoke"** to remove the old authorization
4. Return to GitPDM and click **"Sign In with GitHub"** again
5. Authorize with all requested permissions

**Note**: Each computer stores its own token locally, but GitHub maintains
a single authorization record per app. Revoking and re-authorizing ensures
all computers get tokens with the correct scopes.

### Using GitPDM on multiple computers

You can use GitPDM on multiple computers with the same GitHub account:

- Each computer stores its own token in the local OS credential manager
- All tokens share the same GitHub OAuth authorization
- If you revoke access on GitHub, all computers will need to re-authenticate
- Tokens don't interfere with each other—multiple computers can be
  connected simultaneously

### Token refresh

If GitPDM shows "Not connected" after a system restart:
- The OS credential manager may have issues.
- Use "Disconnect" then "Connect GitHub" again.

## Future Enhancements

Planned improvements for future sprints:

- Token refresh (OAuth refresh tokens)
- Support for GitHub Enterprise Server
- Multiple account support
- Fine-grained permissions (when GitHub supports it)

## References

- [GitHub OAuth Device Flow Documentation]
  (https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/
  authorizing-oauth-apps#device-flow)
- [GitHub OAuth Scopes]
  (https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/
  scopes-for-oauth-apps)
