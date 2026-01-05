"""
Verification script for Phase 2 module restructuring
Tests that the new freecad.gitpdm structure is correct
"""

import sys
from pathlib import Path

def verify_structure():
    """Verify the new module structure exists and is correct."""
    
    print("=" * 60)
    print("Phase 2 Structure Verification")
    print("=" * 60)
    
    root = Path(__file__).parent
    issues = []
    successes = []
    
    # Check new structure exists
    checks = [
        ("freecad/__init__.py", "FreeCAD namespace package"),
        ("freecad/gitpdm/__init__.py", "GitPDM entry point"),
        ("freecad/gitpdm/init_gui.py", "GitPDM GUI entry point"),
        ("freecad/gitpdm/commands.py", "Commands module"),
        ("freecad/gitpdm/workbench.py", "Workbench module"),
        ("freecad/gitpdm/auth/", "Auth package"),
        ("freecad/gitpdm/core/", "Core package"),
        ("freecad/gitpdm/export/", "Export package"),
        ("freecad/gitpdm/git/", "Git package"),
        ("freecad/gitpdm/github/", "GitHub package"),
        ("freecad/gitpdm/gitcad/", "GitCAD package"),
        ("freecad/gitpdm/ui/", "UI package"),
        ("package.xml", "FreeCAD addon metadata"),
        ("README.md", "Root README"),
    ]
    
    print("\n✓ Checking new structure...")
    for path, description in checks:
        full_path = root / path
        if full_path.exists():
            successes.append(f"  ✓ {description}: {path}")
        else:
            issues.append(f"  ✗ MISSING: {description} at {path}")
    
    # Check old structure removed
    old_checks = [
        ("freecad_gitpdm/", "Old module directory"),
        ("Init.py", "Old entry point"),
        ("InitGui.py", "Old GUI entry point"),
    ]
    
    print("\n✓ Checking old structure removed...")
    for path, description in old_checks:
        full_path = root / path
        if not full_path.exists():
            successes.append(f"  ✓ {description} removed: {path}")
        else:
            issues.append(f"  ✗ STILL EXISTS: {description} at {path}")
    
    # Check for old imports in Python files
    print("\n✓ Checking for old imports in Python files...")
    old_import_count = 0
    for py_file in root.rglob("*.py"):
        # Skip this verification script
        if py_file.name == Path(__file__).name:
            continue
        # Skip files in htmlcov, __pycache__, .git
        if any(skip in str(py_file) for skip in ["htmlcov", "__pycache__", ".git"]):
            continue
            
        try:
            content = py_file.read_text(encoding='utf-8')
            if 'freecad_gitpdm' in content:
                old_import_count += 1
                issues.append(f"  ✗ Old imports in: {py_file.relative_to(root)}")
        except Exception as e:
            pass  # Skip files we can't read
    
    if old_import_count == 0:
        successes.append(f"  ✓ No old imports found in Python files")
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if successes:
        print("\n✓ Successes:")
        for success in successes:
            print(success)
    
    if issues:
        print("\n✗ Issues Found:")
        for issue in issues:
            print(issue)
        print("\n⚠️  Phase 2 verification FAILED")
        return False
    else:
        print("\n✅ Phase 2 verification PASSED")
        print("\nNext steps:")
        print("  1. Test addon loading in FreeCAD 1.2.0+")
        print("  2. Run test suite: pytest")
        print("  3. Proceed to Phase 3: Qt cleanup")
        return True

if __name__ == "__main__":
    success = verify_structure()
    sys.exit(0 if success else 1)
