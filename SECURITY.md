# Security Policy

## Overview

GitPDM is a FreeCAD workbench that connects to Git hosting providers (GitHub, GitLab, Bitbucket, Gitea/Forgejo, or SourceHut) for backing up CAD files. This document describes the security architecture, implemented safeguards, and how to report security issues.

## Security Architecture

### Authentication Flow

**GitHub** uses **OAuth Device Flow** (RFC 8628):

1. **No passwords stored**: Users authenticate directly with GitHub; GitPDM never sees passwords
2. **Minimal scopes**: Requests only `read:user` (profile) and `repo` (repository access)
3. **Scope validation**: Validates granted scopes match requested scopes to prevent privilege downgrade
4. **Secure token storage**: Tokens stored in OS credential storage (Windows Credential Manager, macOS Keychain, Linux Secret Service)
5. **Token expiry detection**: Automatically detects expired tokens and refreshes using refresh_token
6. **Hardened polling**: 15-minute absolute timeout, exponential backoff with jitter, correlation IDs for audit

**GitLab, Bitbucket, Gitea/Forgejo, and SourceHut** use a **pasted Personal Access Token** instead: none of these has a pre-registered OAuth app GitPDM can use, so the user creates a PAT on the host themselves (scoped as narrowly as that host allows) and pastes it into GitPDM. GitPDM verifies the token against the host's API before storing it, and never displays or logs the value. Storage is the same OS credential storage used for GitHub tokens, keyed per-provider so connecting to more than one host at once doesn't overwrite another's credentials.

**Headless/CI use** (no FreeCAD, no keyring prompt) resolves credentials from a fixed precedence: `GITPDM_TOKEN_FILE` > `GITPDM_TOKEN` > OS keyring. An additional file-backed token store exists for containers without a keyring at all, but it's gated behind `GITPDM_ALLOW_FILE_TOKENS=1` and unreachable otherwise -- this is enforced by its own test, not just convention.

### Rate Limiting & Abuse Prevention

To prevent abuse and respect each host's rate limits, GitHub's client uses:

- **Global rate limit**: 100 requests/minute across all users
- **Per-user rate limit**: 30 requests/minute per authenticated user
- **Circuit breaker**: Automatically trips after 5 consecutive failures; 30s cooldown
- **Request coalescing**: Deduplicates redundant API calls
- **Automatic backoff**: Exponential backoff with jitter on 5xx errors
- **Secondary rate limit detection**: Respects `Retry-After` headers from GitHub abuse detection

The GitLab/Bitbucket/Gitea-Forgejo/SourceHut clients share the same
retry/circuit-breaker/rate-limiter skeleton (`providers/shared/`), so the
mechanism is identical even though each host's own numeric quotas differ
from GitHub's.

### Input Validation

All user-controlled inputs are validated before use:

- **Repository names**: Alphanumeric + dots/hyphens/underscores only; max 100 chars
- **Owner names**: Alphanumeric + hyphens/underscores; max 39 chars (GitHub limit)
- **Branch names**: Valid Git ref names; no path traversal sequences
- **Commit messages**: Control characters stripped; max 50KB
- **File paths**: Path traversal protection (no `..`); validated against repo root
- **GitHub URLs**: HTTPS only; github.com domain validated
- **Other host URLs** (GitLab/Bitbucket/Gitea-Forgejo/SourceHut self-hosted
  instances): the user-supplied host is trusted as entered, since these are
  meant to point at arbitrary self-hosted instances rather than a single
  fixed domain -- **HTTPS is not currently enforced** for this path (a
  pasted `http://` host URL is accepted); see the Known Limitations note
  below

### Permissions & Least Privilege

- **Read-only by default**: Most operations use read-only API calls
- **Write operations gated**: Commit/push only when user explicitly initiates
- **No admin scopes**: Never requests repo admin or org-level permissions
- **Short-lived tokens**: Tokens automatically refreshed; prefer shortest TTL
- **Required `repo` scope**: GitPDM requests the `repo` OAuth scope, which grants
  broad access to all repositories. This is required because:
  - Git push operations via HTTPS require `repo` scope (GitHub's requirement)
  - Creating repositories via API requires `repo` scope
  - The alternative `public_repo` scope only works with public repositories
  
  **Mitigation**: GitPDM never modifies repositories without explicit user action
  (clicking "Commit & Push", "New Repository", etc.). All write operations are
  user-initiated and clearly labeled in the UI.

### Network Security

- **HTTPS only for GitHub**: All GitHub communication uses TLS 1.2+
- **Other providers**: the pasted PAT is only ever sent to whatever scheme
  the user-supplied host URL specifies -- see the Input Validation and
  Known Limitations notes above/below
- **Certificate validation**: Full certificate chain validation (no insecure flags)
- **No credential logging**: Authorization headers never logged
- **Timeout enforcement**: All network calls have strict timeouts (10-180s)

### Known Limitations

- **No HTTPS enforcement for self-hosted providers**: unlike the GitHub
  path (hardcoded to `github.com` over HTTPS), the GitLab/Bitbucket/
  Gitea-Forgejo/SourceHut connect flow accepts whatever scheme the user
  types into the host-URL field, including `http://`. A user who pastes
  (or is tricked into pasting) a plain-HTTP self-hosted URL sends their
  PAT over an unencrypted connection with no local warning. Tracked as a
  real gap, not yet fixed.

## Attack Vectors & Mitigations

### 1. Token Compromise

**Risk**: Attacker obtains user's OAuth token  
**Impact**: Unauthorized repo access until token expires/revoked

**Mitigations**:
- Tokens stored in OS credential storage (encrypted at rest)
- Tokens never logged or written to FreeCAD settings
- Token expiry detection with automatic refresh
- Users can revoke via GitHub → Settings → Applications

### 2. Command Injection (Git Operations)

**Risk**: Malicious commit messages/file names execute shell commands  
**Impact**: Arbitrary code execution with user privileges

**Mitigations**:
- All Git commands use `subprocess` with list arguments (no shell expansion)
- Commit messages sanitized (control chars removed)
- File paths validated against repo root
- No user input passed to shell directly

### 3. Path Traversal

**Risk**: Malicious file paths access files outside repo  
**Impact**: Leak/modify files outside intended scope

**Mitigations**:
- All file paths validated with `Path.resolve()` and `relative_to()` checks
- Parent directory references (`..`) rejected
- Absolute paths resolved and validated against repo root

### 4. API Abuse / Rate Limit Exhaustion

**Risk**: Attacker triggers thousands of API requests  
**Impact**: GitHub throttles/blocks the app; service denial for other users

**Mitigations**:
- Global + per-user rate limiting with token buckets
- Circuit breaker prevents retry storms
- Exponential backoff with jitter
- Request coalescing reduces redundant calls
- 15-minute hard timeout on OAuth device flow

### 5. Scope Downgrade

**Risk**: User grants fewer permissions than requested  
**Impact**: App fails unpredictably or operates with insufficient permissions

**Mitigations**:
- Scope validation after token grant
- Clear error message if required scopes missing
- Re-authentication required if scopes insufficient

### 6. Network Attacks (MITM, DNS Poisoning)

**Risk**: Attacker intercepts/modifies GitHub communication  
**Impact**: Token theft, injected content, denial of service

**Mitigations**:
- HTTPS with full certificate validation
- Pinned domain (github.com only)
- No fallback to insecure protocols
- Network timeouts prevent hanging connections

### 7. Dependency Compromise

**Risk**: Malicious code in Python dependencies  
**Impact**: Arbitrary code execution, data exfiltration

**Mitigations**:
- Minimal dependencies (stdlib-only where possible)
- Dependabot/Renovate for automatic updates
- Code review for dependency changes
- PyPI package verification

## Security Best Practices for Users

1. **Revoke tokens you don't recognize**  
   GitHub → Settings → Applications → Authorized OAuth Apps

2. **Don't share your FreeCAD user directory**  
   Contains cached credentials (encrypted but sensitive)

3. **Keep FreeCAD updated**  
   Security patches distributed via FreeCAD Addon Manager

4. **Verify repo ownership**  
   Before pushing, confirm you're writing to your own repo

5. **Use branch protection**  
   Enable GitHub branch protection rules for important branches

6. **Review commit history**  
   Periodically check for unexpected commits

## Rate Limits & Quotas

### Primary Rate Limits (GitHub)
- **Authenticated requests**: 5,000 req/hour per user (GitHub's limit)
- GitPDM enforces stricter limits to stay well below this

### GitPDM Rate Limits
- **Global**: 100 requests/minute
- **Per-user**: 30 requests/minute
- **Circuit breaker**: 5 failures → 30s cooldown

### What Happens When Rate Limited?
1. Request is rejected immediately (no API call made)
2. Error message shows wait time
3. UI suggests retrying after cooldown
4. Background operations automatically queued

### Monitoring Your Usage
Check rate limit status in GitPDM diagnostics (Help → GitPDM Diagnostics):
- Global tokens remaining
- Per-user tokens remaining
- Circuit breaker state

## Abuse Handling

### Reporting Abuse
If you observe GitPDM being used for malicious purposes:

1. **Email**: [Create security issue on GitHub](https://github.com/nerd-sniped/GitPDM/security/advisories/new)
2. **Include**: Description, timestamps, affected repos/users
3. **Response time**: 48 hours for acknowledgment

### Common Abuse Patterns
- **Repo spam**: Automated creation of many repositories
- **Comment spam**: Automated comments via Git commits
- **Rate limit testing**: Intentional exhaustion of quotas

### Anti-Abuse Controls
- Per-user rate limits isolate noisy users
- Circuit breakers prevent retry storms
- Scope limitations prevent org-wide actions
- Input validation blocks injection attempts

## Vulnerability Reporting

### Responsible Disclosure

**Please DO NOT open public issues for security vulnerabilities**

Report security vulnerabilities via:
- **GitHub Security Advisory**: https://github.com/nerd-sniped/GitPDM/security/advisories/new
- **Email**: (if provided in repository)

Include:
1. Description of vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

### Response Timeline
- **24 hours**: Acknowledgment
- **7 days**: Initial assessment and severity classification
- **30 days**: Fix developed and tested
- **Release**: Coordinated disclosure with security advisory

### Scope
**In scope**:
- OAuth token leakage
- Command injection
- Path traversal
- API abuse mechanisms
- Credential storage weaknesses

**Out of scope**:
- Vulnerabilities in GitHub, GitLab, Bitbucket, Gitea/Forgejo, or SourceHut themselves (report to the respective provider)
- FreeCAD core vulnerabilities (report to FreeCAD)
- Denial of service via resource exhaustion (rate limits prevent this)

## Security Updates

### How Updates Are Distributed
1. Security fixes released as new workbench version
2. Announced via GitHub Security Advisories
3. Users notified via FreeCAD Addon Manager
4. Critical patches may auto-update (with user consent)

### Versioning
- **Patch releases** (x.y.Z): Security fixes, no breaking changes
- **Minor releases** (x.Y.0): Security + features, backward compatible
- **Major releases** (X.0.0): May include breaking changes

### Release Notes
Check the [GitHub Releases page](https://github.com/nerd-sniped/GitPDM/releases) for security-related updates.

## Compliance & Privacy

### Data Collection
GitPDM does NOT collect or transmit:
- Usage analytics
- Telemetry
- Crash reports
- Personal information

The only network requests are to the configured Git host's API (GitHub, GitLab, Bitbucket, Gitea/Forgejo, or SourceHut) for repo operations.

### Data Storage
GitPDM stores locally (never uploaded to our servers):
- OAuth tokens (in OS credential storage, encrypted)
- Repository paths (in FreeCAD settings)
- Last commit timestamps (in FreeCAD settings)

### GDPR Compliance
Users can:
- **Access**: View stored credentials via OS credential manager
- **Delete**: Remove credentials by signing out
- **Portability**: Export repo history via Git
- **Right to be forgotten**: Delete all local GitPDM data by uninstalling

### Your Git Host's Data Handling
Whichever provider you connect handles your account data under its own privacy policy, not GitPDM's:
- GitHub: https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement
- GitLab: https://about.gitlab.com/privacy/
- Bitbucket: https://www.atlassian.com/legal/privacy-policy
- Gitea/Forgejo: set by whoever operates the specific instance you connect to
- SourceHut: https://man.sr.ht/privacy.md

## Security Roadmap

### Implemented (Sprint SECURITY-1 to SECURITY-5)
- ✅ Rate limiter with circuit breaker
- ✅ Scope validation
- ✅ Token expiry and refresh
- ✅ OAuth hardening (timeouts, jitter, correlation IDs)
- ✅ Input sanitization
- ✅ Pasted-PAT auth path for GitLab/Bitbucket/Gitea-Forgejo/SourceHut, verified before storage, alongside GitHub's OAuth device flow

### Planned
- 🔲 Webhook signature verification (if webhook support added)
- 🔲 Per-repo operation quotas
- 🔲 Audit log export for enterprise users
- 🔲 Support for GitHub Enterprise Server
- 🔲 Hardware token (FIDO2) support for OAuth

### Future Considerations
- Fine-grained personal access tokens (when GitHub stabilizes API)
- Signed commits (GPG/SSH key integration)
- Encrypted repository contents (client-side encryption)

## Contact

- **Security issues**: https://github.com/nerd-sniped/GitPDM/security/advisories/new
- **General support**: https://github.com/nerd-sniped/GitPDM/issues
- **Documentation**: https://github.com/nerd-sniped/GitPDM/blob/main/docs/README.md

---

**Last updated**: 2026-07-20  
**Security policy version**: 1.1
