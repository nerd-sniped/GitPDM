# GitPDM

Git version control and multi-host collaboration (GitHub, GitLab, Bitbucket,
Gitea/Forgejo, SourceHut) for FreeCAD documents — commit, push, pull, and
share `.FCStd` files without leaving FreeCAD.

## Install

1. Find your FreeCAD `Mod` folder:
   - **Windows**: `%APPDATA%\FreeCAD\Mod`
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod`
   - **Linux**: `~/.FreeCAD/Mod/`
   - Create it if it doesn't exist.
2. Download the [latest release](https://github.com/nerd-sniped/GitPDM/releases)
   and extract it into that folder, so you have `Mod/GitPDM/Init.py`,
   `Mod/GitPDM/InitGui.py`, `Mod/GitPDM/freecad_gitpdm/`.
3. Restart FreeCAD, then select **Git PDM** from the workbench dropdown.

Requires FreeCAD (current stable + one prior release) and Git on your `PATH`
(`git --version` should work in a terminal).

## Quick start

1. Click **Toggle GitPDM Panel** in the Git PDM toolbar.
2. In the panel, browse to (or create) an empty project folder — GitPDM
   offers a **Create Repo** button once it notices the folder isn't a Git
   repository yet.
3. Save your FreeCAD document inside that folder, then commit from the
   panel.
4. Ready to back up or collaborate? Open the **Git PDM** menu →
   **Connections** to connect a GitHub/GitLab/Bitbucket/Gitea-Forgejo/
   SourceHut account, then push.
   - **Linux/macOS:** this step needs one extra one-time package install
     the first time — see [Linux](docs/README.md#how-to-set-up-linux-token-storage-gnome-keyring--kwallet)
     / [macOS](docs/README.md#how-to-fix-macos-keychain-access-issues)
     setup if **Connect** doesn't succeed.

## Learn more

- **[Full documentation](docs/README.md)** — tutorials, how-to guides,
  technical reference (credential chain, continuous checkpointing,
  advisory file presence, previews) and explanations (why branch
  switching is tricky with `.FCStd` files, and more)
- **[Platform support](docs/PLATFORM_SUPPORT.md)**
- **[Security policy](SECURITY.md)**

## Contributing / development

[CLAUDE.md](CLAUDE.md) covers the module layout and conventions for working
in this codebase. [Dev_Docs/](Dev_Docs/) holds the roadmap, requirements,
and manual test checklist.

## License

MIT — see [LICENSE](LICENSE).
