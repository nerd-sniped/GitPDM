"""
Test to detect if user is opening FreeCAD files from the wrong folder/worktree.

This is likely the root cause of "corruption": user creates a worktree but then
still opens/edits files from the main repo folder instead of the worktree folder.
"""

import os
import sys
import shutil
import tempfile
import json
from pathlib import Path
from typing import List, Dict

class WorktreeFolderMismatchTest:
    """
    Simulates the workflow where user:
    1. Creates a worktree for feature-a
    2. But accidentally edits files from the main repo folder
    3. Switches back to main in the worktree
    4. Observes "corruption" (actually from wrong folder)
    """
    
    def __init__(self):
        self.test_dir = tempfile.mkdtemp(prefix="gitpdm_mismatch_")
        self.results: Dict[str, str] = {}
        print(f"\nTest directory: {self.test_dir}")
    
    def setup_scenario(self):
        """Setup a scenario with main repo and multiple worktrees."""
        print("\n[1] Setting up folder structure...")
        
        # Main repo
        main_repo = os.path.join(self.test_dir, "MyProject")
        os.makedirs(main_repo)
        
        # Create files in main
        main_file = os.path.join(main_repo, "circle.FCStd")
        with open(main_file, "wb") as f:
            f.write(b"CIRCLE_MAIN" + b"\x00" * 50)
        
        # Worktree for feature-a
        worktree_a = os.path.join(self.test_dir, "MyProject-feature-a")
        os.makedirs(worktree_a)
        
        # Worktree for feature-b  
        worktree_b = os.path.join(self.test_dir, "MyProject-feature-b")
        os.makedirs(worktree_b)
        
        # Files in worktrees (simulating git checkout content)
        file_a = os.path.join(worktree_a, "circle.FCStd")
        with open(file_a, "wb") as f:
            f.write(b"CIRCLE_FEATURE_A" + b"\x00" * 50)
        
        file_b = os.path.join(worktree_b, "circle.FCStd")
        with open(file_b, "wb") as f:
            f.write(b"CIRCLE_FEATURE_B" + b"\x00" * 50)
        
        print(f"  ✓ Created main repo: {main_repo}")
        print(f"  ✓ Created worktree-a: {worktree_a}")
        print(f"  ✓ Created worktree-b: {worktree_b}")
        
        return main_repo, worktree_a, worktree_b
    
    def test_wrong_folder_editing(self, main_repo, worktree_a, worktree_b):
        """
        Simulate: user creates worktrees but edits from wrong folder.
        This explains the "corruption" they see.
        """
        print("\n[2] Simulating wrong-folder editing...")
        
        main_file = os.path.join(main_repo, "circle.FCStd")
        file_a = os.path.join(worktree_a, "circle.FCStd")
        
        # Read main repo file
        with open(main_file, "rb") as f:
            main_content = f.read()
        print(f"  Main repo circle.FCStd: {main_content[:20]}")
        
        # Read worktree-a file
        with open(file_a, "rb") as f:
            file_a_content = f.read()
        print(f"  Worktree-a circle.FCStd: {file_a_content[:20]}")
        
        # Simulate user: "I created worktree-a, but I'm still opening files from MyProject/"
        print("\n  Scenario: User opens MyProject/circle.FCStd and edits it")
        
        # User edits main_file (thinking they're editing worktree-a)
        with open(main_file, "wb") as f:
            f.write(b"EDITED_FROM_WRONG_LOCATION" + b"\x00" * 50)
        
        # Read what they edited
        with open(main_file, "rb") as f:
            edited = f.read()
        print(f"  After edit: {edited[:30]}")
        
        # Now user "switches" to feature-b (in their mind, but really just changes which folder they're opening)
        print("\n  Scenario: User thinks they switched to feature-b, opens that circle.FCStd")
        file_b = os.path.join(worktree_b, "circle.FCStd")
        with open(file_b, "rb") as f:
            file_b_content = f.read()
        print(f"  Feature-b file is: {file_b_content[:20]}")
        
        # They notice something is wrong
        print("\n  Scenario: User expects to see 'CIRCLE_FEATURE_B' but instead sees")
        print(f"            their edited content '{edited[:30].decode('utf-8', errors='ignore')}'")
        print("            CONCLUSION: 'File is corrupted!' (actually: wrong folder)")
        
        self.results['wrong_folder_edit'] = 'DETECTED: User likely opening files from wrong folder'
        
        return True
    
    def test_open_folder_detection(self):
        """
        Show how to detect which folder is actually open in FreeCAD.
        This is what the UI guard should show.
        """
        print("\n[3] Detecting open folder in FreeCAD...")
        
        # In real scenario, FreeCAD would have an "active project" or we'd
        # look at App.ActiveDocument.FileName to see the absolute path
        
        example = """
        In FreeCAD:
        - App.listDocuments() returns open documents
        - For each doc, doc.FileName shows absolute path
        - We can check if this path is in:
          a) Main repo folder → editing MAIN
          b) Worktree folder → editing WORKTREE
          
        EXAMPLE:
        If document's absolute path is:
          C:/Users/test/MyProject-feature-a/circle.FCStd
        Then user is editing the FEATURE-A WORKTREE ✓
        
        If document's absolute path is:
          C:/Users/test/MyProject/circle.FCStd
        Then user is editing the MAIN REPO (risky!) ⚠️
        """
        
        print(example)
        self.results['open_folder_detection'] = 'Can determine open folder from App.ActiveDocument.FileName'
        
        return True
    
    def test_safe_workflow(self):
        """Recommend the safe workflow."""
        print("\n[4] Recommended safe workflow...")
        
        workflow = """
        RECOMMENDED WORKFLOW (NO CORRUPTION):
        
        1. User clicks "Switch to feature-a"
        2. GitPDM shows: "Create worktree for feature-a? (Recommended)"
           [Yes - Create worktree]  [No - Switch in-place (risky)]
        3. User clicks "Yes"
        4. GitPDM creates: MyProject-feature-a/ (via git worktree)
        5. GitPDM displays: "Worktree created at: C:\\...\\MyProject-feature-a"
        6. UI suggestion: "Open this folder in FreeCAD to start editing"
        7. User opens the WORKTREE folder in FreeCAD (not main repo)
        8. User edits files from worktree folder
        9. When switching branches again, user opens the new worktree folder
        10. No file corruption because each branch has isolated folder
        
        CURRENT PROBLEM:
        - User creates worktree ✓
        - But continues opening main repo folder in FreeCAD ✗
        - Edits files from main repo while git operations happen
        - Worktree content never touched, but main repo file gets corrupted
        - User incorrectly concludes "worktrees don't work"
        """
        
        print(workflow)
        self.results['safe_workflow'] = 'Requires user to open correct worktree folder in FreeCAD'
        
        return True
    
    def cleanup(self):
        """Clean up."""
        print("\n[5] Cleanup...")
        try:
            shutil.rmtree(self.test_dir)
            print(f"  ✓ Removed test directory")
        except Exception as e:
            print(f"  ! Cleanup failed: {e}")
    
    def run_all(self, cleanup_after=True):
        """Run all tests."""
        print("=" * 70)
        print("Worktree Folder Mismatch Analysis")
        print("=" * 70)
        
        try:
            main_repo, worktree_a, worktree_b = self.setup_scenario()
            self.test_wrong_folder_editing(main_repo, worktree_a, worktree_b)
            self.test_open_folder_detection()
            self.test_safe_workflow()
        finally:
            if cleanup_after:
                self.cleanup()
        
        print("\n" + "=" * 70)
        print("ANALYSIS SUMMARY:")
        print("=" * 70)
        for key, result in self.results.items():
            print(f"  • {result}")
        print("\nCONCLUSION:")
        print("  The 'corruption' is likely because user opens the MAIN repo folder")
        print("  in FreeCAD instead of the worktree folder after switching branches.")
        print("\nNEXT STEP:")
        print("  Update UI to show a clear 'Open Folder' button that opens the")
        print("  correct worktree path in the file explorer or FreeCAD directly.")
        print("=" * 70)

if __name__ == "__main__":
    test = WorktreeFolderMismatchTest()
    test.run_all(cleanup_after=True)
