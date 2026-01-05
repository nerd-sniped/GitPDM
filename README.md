# GitPDM - Git-based Product Data Management for FreeCAD

**Version 1.0.0 - FreeCAD 1.2.0+ Required**

GitPDM is a FreeCAD workbench addon that brings Git version control, file locking, and automated FCStd file management directly into FreeCAD. Built with native Python for cross-platform reliability.

## 🎉 What's New in v1.0.0

**Major Release - Consolidated & Polished!**

GitPDM v1.0.0 represents a complete consolidation of GitCAD and GitPDM, featuring:

- ✅ **Native Python Core** - No bash dependencies, pure Python everywhere
- ✅ **FreeCAD 1.2.0+ Ready** - Modern Qt6/PySide6, proper namespace isolation
- ✅ **Simplified Configuration** - Single `.gitpdm/config.json` location
- ✅ **Backward Compatible** - Auto-migrates legacy GitCAD configurations
- ✅ **Cleaner Codebase** - 2,400+ lines of legacy code removed
- ✅ **Consistent Naming** - Professional, unified API throughout

**Breaking Changes:** Requires FreeCAD 1.2.0+ and Python 3.10+. For older versions, use GitPDM v0.1.x from the `legacy-pre-1.2` branch.

## Requirements

- **FreeCAD 1.2.0 or newer** (required for Qt6/PySide6 support)
- **Python 3.10+** (included with FreeCAD 1.2.0)
- **Git** installed and available on PATH
- **Git LFS** (optional, for file locking features)

> **Upgrading from v0.1.x?** See [FREECAD_1_2_MIGRATION_PLAN.md](FREECAD_1_2_MIGRATION_PLAN.md) for detailed upgrade instructions.

## Features

### Core Functionality
- 🔄 **Full Git Workflow** - Clone, commit, push, pull, branch, merge - all from within FreeCAD
- 📁 **Smart FCStd Handling** - Automatic export/import of FreeCAD files to version-control-friendly format
- 🔒 **File Locking** - Git LFS locking prevents merge conflicts in collaborative teams
- ⚙️ **Automatic Compression** - Binary files (.brp) compressed separately for optimal repository size

### GitHub Integration
- 🔐 **Secure Authentication** - OAuth device flow (no password storage)
- 📤 **Push/Pull Operations** - Seamless remote repository sync
- 🌐 **Repository Management** - Create and clone GitHub repos directly

### Workflow Automation
- 📊 **Visual File Browser** - Navigate repository with lock indicators
- 🎯 **Workbench Integration** - Native FreeCAD panel and toolbar
- 🔧 **Configurable** - Customize export behavior, compression, locking rules
- 🏗️ **Repository Wizards** - Guided setup for new and existing projects

## Installation

### Via FreeCAD Addon Manager (Recommended)

1. Open FreeCAD 1.2.0+
2. Go to **Tools → Addon Manager**
3. Search for "GitPDM"
4. Click **Install**
5. Restart FreeCAD

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/nerd-sniped/GitPDM/releases)
2. Extract to your FreeCAD Mod folder:
   - **Windows**: `%APPDATA%\FreeCAD\Mod\GitPDM`
   - **macOS**: `~/Library/Application Support/FreeCAD/Mod/GitPDM`
   - **Linux**: `~/.FreeCAD/Mod/GitPDM`
3. Restart FreeCAD
4. Select **Git PDM** from the workbench dropdown

## Quick Start

1. **Activate Workbench**: Select "Git PDM" from workbench dropdown
2. **Open Panel**: Click "Toggle GitPDM Panel" button
3. **Create Repository**: Click "Browse for Folder" and select/create a project folder
4. **Initialize**: Click "Create Repo" to set up Git
5. **Work**: Create your FreeCAD documents in the repository
6. **Commit**: Use the panel to commit your changes

## History

GitPDM incorporates and builds upon innovations from the GitCAD project by Michael Marais, which pioneered FreeCAD `.FCStd` file version control. GitPDM v1.0 represents a complete consolidation, combining GitCAD's proven core algorithms (now in native Python) with a modern FreeCAD 1.2 workbench interface. See [docs/GITCAD_HISTORY.md](docs/GITCAD_HISTORY.md) for the full story and attribution.

## Documentation

Comprehensive documentation is available in the [docs](docs/) folder:

- **[Complete Documentation](docs/README.md)** - Full user guide, tutorials, and reference
- **[GitCAD History](docs/GITCAD_HISTORY.md)** - Project origins and consolidation story
- **[Migration Guide](MIGRATION_GUIDE.md)** - Upgrading from v0.1.x to v0.2.0
- **[Testing Guide](TESTING_GUIDE.md)** - For contributors and testers
- **[Implementation Guide](IMPLEMENTATION_QUICKSTART.md)** - For developers
- **[Migration Plan](FREECAD_1_2_MIGRATION_PLAN.md)** - Details on v0.2.0 changes

## Module Structure

Following FreeCAD 1.2.0+ standards:

```
GitPDM/
├── freecad/
│   └── gitpdm/               # Main addon package
│       ├── __init__.py       # Entry point (non-GUI)
│       ├── init_gui.py       # GUI entry point
│       ├── workbench.py      # Workbench definition
│       ├── commands.py       # FreeCAD commands
│       ├── auth/             # GitHub authentication
│       ├── core/             # Core functionality
│       ├── export/           # Export workflows
│       ├── git/              # Git operations
│       ├── github/           # GitHub API
│       ├── gitcad/           # GitCAD integration
│       └── ui/               # User interface
├── tests/                    # Test suite
├── docs/                     # Documentation
├── package.xml               # FreeCAD addon metadata
└── pyproject.toml            # Python package config
```

## Breaking Changes from v0.1.x

If you're upgrading from v0.1.x, note these changes:

### For Users
- Requires FreeCAD 1.2.0+ (older versions not supported)
- May need to reinstall the addon via Addon Manager

### For Contributors
- Import paths changed: `freecad_gitpdm` → `freecad.gitpdm`
- Entry points renamed: `Init.py` → `__init__.py`, `InitGui.py` → `init_gui.py`
- Only PySide6 supported (no PySide2 compatibility)
- Python 2 compatibility code removed

## Contributing

We welcome contributions! Please see:

- [Testing Guide](TESTING_GUIDE.md) for development setup
- [GitHub Issues](https://github.com/nerd-sniped/GitPDM/issues) for bugs and features
- [Pull Requests](https://github.com/nerd-sniped/GitPDM/pulls) for contributions

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/nerd-sniped/GitPDM/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nerd-sniped/GitPDM/discussions)
- **Documentation**: [docs/README.md](docs/README.md)

## Version History

- **v1.0.0** (2026-01-04): **Major consolidation release**
  - Native Python core (no bash dependencies)
  - Simplified configuration (`.gitpdm/config.json`)
  - Removed 2,400+ lines of legacy code
  - Standardized naming throughout
  - Auto-migration from legacy GitCAD configs
  - 6 major consolidation sprints completed
- **v0.2.0** (2026-01-03): FreeCAD 1.2.0+ restructuring, Qt6 only, new module layout
- **v0.1.x**: Legacy version for FreeCAD 0.20/0.21/1.0 (see `legacy-pre-1.2` branch)

---

Made with ❤️ for the FreeCAD community
