# Cross-Platform Support

GitPDM supports Windows, Linux, and macOS, with credential storage that
uses each platform's own OS-native secure storage.

## Platform Support Matrix

| Platform | Token Storage | Extra Setup Needed | Status |
|----------|----------------|---------------------|--------|
| Windows | Windows Credential Manager (via `ctypes`, no extra dependency) | None | Fully supported |
| Linux | Secret Service API (GNOME Keyring, KWallet, etc., via the `secretstorage` package) | Usually yes — see below | Fully supported |
| macOS | Keychain (via the `keyring` package) | Usually yes — see below | Fully supported |

## Why Linux and macOS Need an Extra Step

Windows' credential storage (`freecad_gitpdm/auth/token_store_wincred.py`)
talks to the Windows Credential Manager API directly via `ctypes` — no
third-party package required, so it works immediately after installing
GitPDM.

Linux and macOS instead depend on two well-established Python packages,
`secretstorage` and `keyring`. Neither is currently on FreeCAD's own
list of Addon-Manager-installable Python packages, so the Addon Manager
doesn't auto-install them the way it does GitPDM itself — a one-time
manual install is usually needed first. See **[How to Set Up Linux Token
Storage](README.md#how-to-set-up-linux-token-storage-gnome-keyring--kwallet)**
and **[How to Fix macOS Keychain Access Issues](README.md#how-to-fix-macos-keychain-access-issues)**
in the full documentation for exact, copy-pasteable steps.

Until that one-time step is done, GitPDM still installs and runs
normally — only token storage (connecting a GitHub/GitLab/etc. account)
is affected, and it fails with a clear error rather than a crash.

## Git Detection

`freecad_gitpdm/git/client.py` looks for the `git` executable on `PATH`
first, then falls back to platform-specific common install locations if
that fails:

- **Windows**: common `Program Files` install paths, GitHub Desktop's
  bundled git
- **Linux**: `/usr/bin/git`, `/usr/local/bin/git`
- **macOS**: `/usr/local/bin/git`, `/opt/local/bin/git` (MacPorts),
  `/opt/homebrew/bin/git` (Homebrew on Apple Silicon)

## CI

`.github/workflows/ci.yml` runs the test suite on `ubuntu-latest`,
`windows-latest`, and `macos-latest`, across Python 3.11 and 3.12 (3.10
support was dropped 2026-07-20 — see `PYTHON_COMPATIBILITY.md`).
