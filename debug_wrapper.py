"""
Check logs and test wrapper creation directly
"""
import sys
from freecad_gitpdm.core import log

# Try to create wrapper directly
repo = r"C:\Factorem\Nerd-Sniped\GitPDM"

print("Testing GitCADWrapper creation...")
try:
    from freecad_gitpdm.gitcad import GitCADWrapper
    wrapper = GitCADWrapper(repo)
    print(f"✓ SUCCESS: Wrapper created")
    print(f"  Bash exe: {wrapper._bash_exe}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Check what _find_bash_executable returns
print("\nTesting bash detection...")
try:
    from freecad_gitpdm.gitcad.wrapper import _find_bash_executable
    bash = _find_bash_executable()
    print(f"Bash path: {bash}")
except Exception as e:
    print(f"Error finding bash: {e}")
    import traceback
    traceback.print_exc()
