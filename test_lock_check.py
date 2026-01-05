# Debug script to test lock checking logic
# Run this in FreeCAD's Python console to diagnose lock enforcement issues

def test_lock_logic():
    """Test the lock checking logic"""
    import FreeCAD
    from freecad.gitpdm.core import settings
    
    # Get current FreeCAD GUI
    try:
        from FreeCADGui import getMainWindow
        main_window = getMainWindow()
        
        # Find GitPDM panel
        panel = None
        for widget in main_window.findChildren(type(main_window)):
            if hasattr(widget, '_lock_handler'):
                panel = widget
                break
        
        if not panel:
            print("[ERROR] GitPDM panel not found!")
            return
        
        print("=" * 60)
        print("LOCK HANDLER DEBUG INFO")
        print("=" * 60)
        
        # Check lock handler state
        lock_handler = panel._lock_handler
        print("\n1. Lock Handler State:")
        print("   Available: {}".format(lock_handler._available))
        print("   Current Username: '{}'".format(lock_handler._current_username))
        print("   Lock Manager: {}".format(lock_handler._lock_manager))
        
        # Check GitHub settings
        print("\n2. GitHub Settings:")
        github_login = settings.load_github_login()
        github_connected = settings.load_github_connected()
        print("   GitHub Login: '{}'".format(github_login))
        print("   GitHub Connected: {}".format(github_connected))
        
        # Check current locks
        print("\n3. Current Locks ({}):".format(len(lock_handler._current_locks)))
        if lock_handler._current_locks:
            for path, lock_info in lock_handler._current_locks.items():
                is_mine = lock_info.owner == lock_handler._current_username
                indicator = "[YOU]" if is_mine else "[OTHER]"
                print("   {} {}".format(indicator, path))
                print("       Owner: {}".format(lock_info.owner))
                print("       Lock ID: {}".format(lock_info.lock_id))
        else:
            print("   (no locks)")
        
        # Test lock violation check
        print("\n4. Testing Lock Violation Check:")
        if hasattr(panel, '_commit_push'):
            has_viol, msg, files = panel._commit_push._check_lock_violations()
            print("   Has Violations: {}".format(has_viol))
            if has_viol:
                print("   Locked Files: {}".format(files))
                print("   Message: {}...".format(msg[:100]))
        
        print("\n" + "=" * 60)
        print("To refresh: panel._lock_handler.refresh_username()")
        print("=" * 60)
        
    except Exception as e:
        print("[ERROR] {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lock_logic()
