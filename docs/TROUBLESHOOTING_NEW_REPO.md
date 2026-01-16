# Troubleshooting: "Repository not found" Error When Creating New Repository

## Problem

When using the "Start New Project" wizard to create a GitHub repository, the push step fails with:

```
ERROR: Push failed: remote: Repository not found.
fatal: repository 'https://github.com/Factorem-io/TestProject.git/' not found
```

## Root Causes

This error typically occurs for one of these reasons:

### 1. **Repository Created Under Wrong Account**
The repository might have been created under your personal GitHub account instead of the `Factorem-io` organization.

**Check:**
- Visit the URL in the error message
- Look at who owns the repository
- Verify you have access to create repos in the `Factorem-io` org

**Fix:**
- If using an organization, ensure you're authenticated with an account that has access
- Recreate the repository under the correct account/org
- Or use your personal account instead of an organization

### 2. **Authentication Issues**
Git can't access GitHub because credentials aren't configured.

**Check:**
- Open PowerShell/Terminal
- Run: `git config --global credential.helper`
- Should show a credential helper (e.g., `manager-core`, `wincred`)

**Fix:**
```powershell
# Windows - Install Git Credential Manager
winget install --id Git.Git -e --source winget

# Or configure manually
git config --global credential.helper manager-core
```

### 3. **URL Format Issues**
Extra trailing slashes or incorrect URL format.

**Fix:** The code has been updated to automatically strip trailing slashes.

### 4. **GitHub Propagation Delay**
Newly created repositories sometimes take a moment to become fully available.

**Fix:**
Wait 30-60 seconds and manually push:
```bash
cd "C:\path\to\your\repository"
git push -u origin main
```

## Step-by-Step Solution

### Option 1: Verify and Manual Push

1. **Check if repository exists on GitHub:**
   - Visit: https://github.com/Factorem-io/TestProject
   - If it exists, the repository was created successfully

2. **Navigate to your local folder:**
   ```powershell
   cd "C:\path\to\TestProject"
   ```

3. **Verify remote is configured:**
   ```bash
   git remote -v
   ```
   Should show:
   ```
   origin  https://github.com/Factorem-io/TestProject.git (fetch)
   origin  https://github.com/Factorem-io/TestProject.git (push)
   ```

4. **Check current branch:**
   ```bash
   git branch
   ```
   Should show `* main` or `* master`

5. **Manually push:**
   ```bash
   git push -u origin main
   ```

### Option 2: Fix Authentication

1. **Check Git credential configuration:**
   ```bash
   git config --list | findstr credential
   ```

2. **If empty, install Git Credential Manager:**
   - Download from: https://github.com/git-ecosystem/git-credential-manager/releases
   - Or use: `winget install --id Git.Git`

3. **Test authentication:**
   ```bash
   git ls-remote https://github.com/Factorem-io/TestProject.git
   ```
   - This will prompt for credentials if not configured
   - Enter your GitHub username and Personal Access Token (PAT)

4. **Retry the push:**
   ```bash
   cd "C:\path\to\TestProject"
   git push -u origin main
   ```

### Option 3: Recreate with Personal Account

If you don't need an organization repository:

1. **Delete the failed repository:**
   - Visit https://github.com/Factorem-io/TestProject/settings
   - Scroll to bottom → "Delete this repository"

2. **Run the wizard again:**
   - Make sure you're logged into GitHub with your personal account
   - The repository will be created as `yourusername/TestProject`

## Prevention

### Before Creating Repository:

1. **Verify GitHub authentication:**
   ```bash
   gh auth status
   # or
   git ls-remote https://github.com/yourusername/test.git
   ```

2. **Check which account you're authenticated as:**
   - Visit https://github.com (should show your username)
   - Or use GitHub CLI: `gh auth status`

3. **For organization repos:**
   - Verify you're a member: https://github.com/orgs/Factorem-io/people
   - Check you have repository creation permissions
   - Org owners can grant this in Settings → Member privileges

## After the Fix

Once authentication is working, the wizard should complete successfully. The updated code now:
- ✅ Strips trailing slashes from URLs automatically
- ✅ Provides detailed error messages with troubleshooting steps
- ✅ Shows the actual URL being used
- ✅ Suggests manual push commands as fallback

## Still Having Issues?

### Check the FreeCAD Console for detailed logs:

The wizard logs detailed information including:
- Exact URL being used
- Authentication status
- Step-by-step progress

### Common Error Patterns:

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| `Repository not found` | Repo doesn't exist or no access | Check URL, verify authentication |
| `Authentication failed` | Invalid credentials | Update Git credentials |
| `Permission denied` | No write access | Check repository permissions |
| `Could not read from remote` | Network/auth issue | Check internet, verify credentials |

## Manual Repository Creation Alternative

If the wizard continues to fail, create manually:

1. **Create repository on GitHub:**
   - Visit https://github.com/new
   - Name it (e.g., "TestProject")
   - Choose visibility (Public/Private)
   - **Don't** check "Initialize with README"
   - Click "Create repository"

2. **Clone it locally:**
   ```bash
   cd "C:\your\projects\folder"
   git clone https://github.com/yourusername/TestProject.git
   cd TestProject
   ```

3. **Add your files and commit:**
   ```bash
   # Create a FreeCAD file or other files
   git add .
   git commit -m "Initial commit"
   git push
   ```

4. **Use GitPDM:**
   - Open GitPDM panel in FreeCAD
   - Browse to the cloned repository folder
   - Start working!

---

**Note:** The code has been updated to provide better error messages and automatically handle common URL issues. After updating GitPDM, you should see more helpful error messages that guide you through solving these issues.
