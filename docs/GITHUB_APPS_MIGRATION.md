# GitHub Apps Migration Plan

## Overview

This document outlines the path to supporting **per-repository permissions** 
by migrating from OAuth Apps to GitHub Apps (or supporting both).

## Current Architecture: OAuth Apps

**What we use now**: GitHub OAuth App with Device Flow

**Permissions model**:
- User authorizes GitPDM once
- Token grants access to ALL repositories
- Cannot limit to specific repos
- Simple setup, immediate access

**Limitations**:
- No per-repository control
- Broad `repo` scope required
- Users concerned about security must use workarounds

## Proposed Architecture: GitHub Apps

**What GitHub Apps offer**:
- User "installs" app and selects specific repositories
- Token scoped only to selected repos
- Granular permissions (read vs write)
- User can add/remove repos at any time

**How it works**:
1. User visits GitHub App installation page
2. Selects which repositories to grant access
3. App receives installation token for only those repos
4. User can modify repository access in GitHub Settings

## Technical Challenges

### 1. Device Flow Limitations

GitHub Apps have limited Device Flow support. Workarounds:

- **Option A**: Use OAuth Web Flow with callback (requires localhost server)
- **Option B**: Hybrid approach - OAuth for auth, GitHub App for repos
- **Option C**: Manual PAT generation (user friction)

### 2. Installation vs Authorization

- OAuth Apps: "Authorize" (one click)
- GitHub Apps: "Install" (select repos, more steps)
- Need clear UI explaining the difference

### 3. Token Management

Current:
```python
token = store.load(host, account)
```

With GitHub Apps:
```python
installation_id = get_installation_id(account)
installation_token = get_installation_token(installation_id)
# Installation tokens expire after 1 hour, need refresh
```

### 4. API Differences

OAuth App:
```bash
GET /user/repos  # Returns ALL repos
```

GitHub App:
```bash
GET /installation/repositories  # Returns ONLY installed repos
```

### 5. Migration Path

Existing users have OAuth tokens. How do we migrate?
- Keep OAuth support (deprecated)
- Offer "Upgrade to GitHub App" flow
- Maintain backward compatibility

## Implementation Plan

### Phase 1: Research & Prototype (Sprint 1-2)

- [ ] Create test GitHub App
- [ ] Prototype installation flow UI
- [ ] Test Device Flow alternatives
- [ ] Verify git push works with installation tokens
- [ ] Document permission differences

### Phase 2: Dual-Mode Support (Sprint 3-5)

- [ ] Add GitHub App config (separate client ID)
- [ ] Add `auth_mode` setting: "oauth" | "github-app"
- [ ] Implement installation flow UI
- [ ] Handle installation token refresh (1hr TTL)
- [ ] Update API client for installation tokens
- [ ] Add per-repo token storage

### Phase 3: UI/UX Improvements (Sprint 6-7)

- [ ] Add "Switch to GitHub App" wizard
- [ ] Show which repos are accessible
- [ ] Add "Request Access" button for new repos
- [ ] Explain tradeoffs in settings
- [ ] Migration guide documentation

### Phase 4: Testing & Rollout (Sprint 8-9)

- [ ] Test with private/org/forked repos
- [ ] Test token expiry/refresh edge cases
- [ ] User acceptance testing
- [ ] Update all documentation
- [ ] Announce feature

### Phase 5: Deprecation (Future)

- [ ] Mark OAuth mode as "legacy"
- [ ] Encourage GitHub App migration
- [ ] Eventually sunset OAuth mode

## Alternative: Hybrid Approach

Keep OAuth for simplicity, add GitHub App as "advanced mode":

**Onboarding Flow**:
```
┌─────────────────────────────────┐
│  Connect to GitHub              │
│                                 │
│  ○ Quick Mode (OAuth)           │
│    ✓ One-click setup            │
│    ✓ Access all repositories    │
│    ⚠ Broad permissions          │
│                                 │
│  ○ Advanced Mode (GitHub App)   │
│    ✓ Select specific repos      │
│    ✓ Minimal permissions        │
│    ⚠ More setup steps           │
│                                 │
│  [Continue]                     │
└─────────────────────────────────┘
```

## User Benefits

### For All Users:
- Peace of mind about security
- Transparency about access
- Control over which repos GitPDM touches

### For Enterprise/Org Users:
- Compliance requirements satisfied
- Org admins can audit installations
- No access to sensitive repos by default

### For Individual Users:
- Separate work/personal repos
- Limit to project-specific repos
- Easy to understand what's accessible

## Technical Benefits

- Better alignment with GitHub's security model
- Preparation for fine-grained tokens
- Cleaner permission model
- Easier to explain to security teams

## Drawbacks & Tradeoffs

**Complexity**:
- More code to maintain (two auth modes)
- Installation flow UX is harder than OAuth
- Token refresh logic more complex (1hr vs never)

**User Friction**:
- Extra setup steps
- Must remember to "install" for new repos
- More decisions during onboarding

**Migration Risk**:
- Breaking changes for existing users
- Need to support both modes indefinitely
- Testing complexity doubles

## Recommendation

**Short term**: Keep OAuth, document limitations clearly ✅ (current approach)

**Medium term**: Implement GitHub App as opt-in advanced feature

**Long term**: Make GitHub App the default, keep OAuth for backwards compatibility

## Community Input Welcome

This is a significant architectural decision. We'd love community input:

- Would you use per-repository mode?
- Is the extra setup friction worth it?
- Should it be default or opt-in?

**Discuss**: [GitHub Issue #XX](https://github.com/nerd-sniped/GitPDM/issues/XX)

## References

- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [GitHub Apps vs OAuth Apps](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-apps)
- [GitHub App Installation Flow](https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-github-marketplace-for-your-organizations)
- [Installation Access Tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
