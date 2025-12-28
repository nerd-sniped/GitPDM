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

### `repo`
- **Purpose**: Access private and public repositories
- **Used for**:
  - Fetching repository metadata
  - Creating releases (future feature)
  - Managing pull requests (future feature)
- **Access**: Read/write access to repository contents

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
