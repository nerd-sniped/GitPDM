# Security Policy

## Supported Versions

We support the latest stable release of GitPDM:

| Version | Supported          |
| ------- | ------------------ |
| 0.8.x   | :white_check_mark: |
| 0.2.x   | :x:                |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in GitPDM, please report it responsibly:

### Private Disclosure

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, email us at: **security@nerd-sniped.com**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### Response Timeline

- **Within 24 hours**: Acknowledgment of your report
- **Within 7 days**: Initial assessment and severity classification
- **Within 30 days**: Fix deployed (if confirmed vulnerability)

### Security Updates

Security patches will be released as:
- Patch version updates (e.g., 0.8.0 → 0.8.1)
- Announced in the CHANGELOG with `[SECURITY]` tag
- Published to GitHub Security Advisories

## Security Best Practices

### OAuth Token Storage

GitPDM stores GitHub OAuth tokens using OS-native credential managers:
- **Windows**: Windows Credential Manager (via wincred)
- **macOS**: Keychain
- **Linux**: Secret Service API (libsecret)

Tokens are **never** stored in plain text files.

### Git Credentials

GitPDM uses Git's native credential helper system. It does not:
- Store git passwords
- Intercept credential prompts
- Access SSH keys directly

### Subprocess Security

All subprocess calls:
- Use list arguments (no shell=True) to prevent command injection
- Sanitize file paths via os.path methods
- Suppress terminal windows on Windows (prevents credential exposure)
- Log output is redacted for sensitive data (tokens, passwords)

### File Operations

- All file paths are validated before operations
- Repository paths must be absolute
- Symbolic link traversal is handled by Python's pathlib
- No arbitrary code execution (no eval/exec)

### Network Security

- All GitHub API calls use HTTPS
- Certificate validation is enforced
- Rate limiting respects GitHub's limits
- Tokens are sent in Authorization headers (not URL params)

## Security Features

### Token Redaction in Logs

All log output automatically redacts:
- GitHub OAuth access tokens (`ghp_*`)
- GitHub Personal Access Tokens (`github_pat_*`)
- Refresh tokens
- Any JSON fields containing "access_token" or "refresh_token"

### Minimal Permissions

OAuth scope requested: `repo`, `read:user`
- `repo`: Required for git push operations and repository creation
- `read:user`: Get username for display

Note: OAuth Apps grant access to all user repositories. For per-repository permissions, consider using GitHub Apps (future enhancement).

### Secure Defaults

- File locking prevents concurrent editing conflicts
- Git operations are local-first
- No automatic credential sharing between repositories
- User confirmation required for destructive operations

## Known Limitations

### OAuth App Architecture

GitPDM currently uses GitHub OAuth Apps which grant access to **all repositories**. There is no way to limit access to specific repositories with OAuth Apps.

**Future Enhancement**: Migrate to GitHub Apps for per-repository installation permissions. See `docs/GITHUB_APPS_MIGRATION.md` for planned implementation.

### Credential Scope

When you authenticate with GitPDM, you grant it access to:
- All your GitHub repositories (public and private)
- Create new repositories
- Read your user profile

If this is a concern:
1. Use a dedicated GitHub account for CAD projects
2. Revoke access after use (GitHub Settings → Applications)
3. Watch for future GitHub Apps support (per-repo permissions)

## Dependency Security

GitPDM has minimal dependencies:
- Python 3.10+ (included with FreeCAD 1.2.0)
- secretstorage (Linux only)
- keyring (macOS only)

Dependencies are:
- Locked to minimum versions in pyproject.toml
- Reviewed for known vulnerabilities
- Updated regularly

## Security Checklist for Contributors

When contributing code:

- [ ] No hardcoded credentials or API keys
- [ ] No shell=True in subprocess calls
- [ ] File paths validated with pathlib
- [ ] User input sanitized
- [ ] Sensitive data redacted from logs
- [ ] Destructive operations require confirmation
- [ ] Network calls use HTTPS with cert validation
- [ ] Tokens stored in OS credential manager
- [ ] No eval() or exec() calls
- [ ] Error messages don't leak sensitive information

## Acknowledgments

We appreciate responsible security researchers who help keep GitPDM safe. 

Contributors who report valid security issues will be:
- Credited in the CHANGELOG (unless they prefer anonymity)
- Listed in the GitHub Security Advisories
- Thanked in the next release notes
