"""
Test the full check_gitcad_availability flow
"""
try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets
import FreeCADGui as Gui

mw = Gui.getMainWindow()
dw = mw.findChild(QtWidgets.QDockWidget, "GitPDM_DockWidget")

if dw and dw.widget():
    scroll_area = dw.widget()
    panel = scroll_area.widget() if hasattr(scroll_area, 'widget') else scroll_area
    print(f"Panel found: Yes")
    print(f"Panel type: {type(panel)}")
    print(f"Current repo: {panel._current_repo_root if hasattr(panel, '_current_repo_root') else 'N/A'}")
    
    if hasattr(panel, '_gitcad_lock'):
        lock = panel._gitcad_lock
        repo = r"C:\Factorem\Nerd-Sniped\GitPDM"
        
        print(f"\nCalling check_gitcad_availability...")
        
        # Step through the method manually to see where it fails
        from freecad_gitpdm.gitcad import is_gitcad_initialized, GitCADWrapper
        
        print(f"1. is_gitcad_initialized: {is_gitcad_initialized(repo)}")
        
        try:
            print(f"2. Creating GitCADWrapper...")
            wrapper = GitCADWrapper(repo)
            print(f"   ✓ Wrapper created")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        try:
            print(f"3. Getting git user.name...")
            username = lock._git_client.get_config_value(repo, "user.name")
            print(f"   Username: {username}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n4. Calling lock.check_gitcad_availability...")
        result = lock.check_gitcad_availability(repo)
        print(f"   Result: {result}")
        print(f"   lock._gitcad_available: {lock._gitcad_available}")
        print(f"   lock._gitcad_wrapper: {lock._gitcad_wrapper}")
    else:
        print(f"No _gitcad_lock attribute")
else:
    print("Panel not found")
