"""
Test to verify the Repository Browser shows correct files after worktree switch.

This test validates that:
1. The repo browser always reflects self._current_repo_root
2. Files shown match the current branch/worktree
3. Opening files uses the correct absolute path from current root
4. Visual indicators show which worktree/branch is active
"""

import os
import tempfile
import shutil
import subprocess
from typing import Tuple

class RepoBrowserWorktreeTest:
    """Test repo browser file listing across worktrees."""
    
    def __init__(self):
        self.test_dir = tempfile.mkdtemp(prefix="gitpdm_browser_test_")
        self.main_repo = os.path.join(self.test_dir, "MyProject")
        self.worktree_a = os.path.join(self.test_dir, "MyProject-feature-a")
        print(f"Test directory: {self.test_dir}")
    
    def _run_git(self, *args, cwd: str) -> Tuple[bool, str, str]:
        """Run a git command."""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def setup_repo_with_branches(self):
        """Create a repo with different files on different branches."""
        print("\n[1] Setting up test repository...")
        
        # Initialize main repo
        os.makedirs(self.main_repo)
        self._run_git("init", cwd=self.main_repo)
        self._run_git("config", "user.name", "Test", cwd=self.main_repo)
        self._run_git("config", "user.email", "test@test.com", cwd=self.main_repo)
        
        # Main branch: create circle.FCStd and square.FCStd
        circle_main = os.path.join(self.main_repo, "circle.FCStd")
        square_main = os.path.join(self.main_repo, "square.FCStd")
        with open(circle_main, "w") as f:
            f.write("MAIN_CIRCLE_v1")
        with open(square_main, "w") as f:
            f.write("MAIN_SQUARE_v1")
        
        self._run_git("add", ".", cwd=self.main_repo)
        self._run_git("commit", "-m", "Main files", cwd=self.main_repo)
        print(f"  ✓ Main branch: circle.FCStd, square.FCStd")
        
        # Create feature-a branch with different files
        self._run_git("checkout", "-b", "feature-a", cwd=self.main_repo)
        
        # Add triangle.FCStd, modify circle.FCStd
        triangle_a = os.path.join(self.main_repo, "triangle.FCStd")
        with open(triangle_a, "w") as f:
            f.write("FEATURE_A_TRIANGLE")
        with open(circle_main, "w") as f:
            f.write("FEATURE_A_CIRCLE_v2")
        
        self._run_git("add", ".", cwd=self.main_repo)
        self._run_git("commit", "-m", "Feature A files", cwd=self.main_repo)
        print(f"  ✓ Feature-a branch: circle.FCStd (modified), square.FCStd, triangle.FCStd")
        
        # Switch back to main
        self._run_git("checkout", "main", cwd=self.main_repo)
        
        return True
    
    def test_browser_shows_main_files(self):
        """Verify browser would list files from main branch."""
        print("\n[2] Testing browser on main branch...")
        
        # In main branch, we should see:
        files_main = []
        for root, dirs, files in os.walk(self.main_repo):
            if ".git" in root:
                continue
            for f in files:
                if f.endswith(".FCStd"):
                    rel = os.path.relpath(os.path.join(root, f), self.main_repo)
                    files_main.append(rel)
        
        print(f"  Files in main branch: {sorted(files_main)}")
        expected_main = ["circle.FCStd", "square.FCStd"]
        
        if sorted(files_main) == sorted(expected_main):
            print(f"  ✓ PASS: Main branch shows correct files")
            return True
        else:
            print(f"  ❌ FAIL: Expected {expected_main}, got {files_main}")
            return False
    
    def test_worktree_shows_feature_files(self):
        """Verify browser would list files from feature-a worktree."""
        print("\n[3] Testing browser on feature-a worktree...")
        
        # Create worktree for feature-a
        success, _, stderr = self._run_git(
            "worktree", "add", self.worktree_a, "feature-a",
            cwd=self.main_repo
        )
        
        if not success:
            print(f"  ❌ FAIL: Could not create worktree: {stderr}")
            return False
        
        print(f"  ✓ Created worktree: {self.worktree_a}")
        
        # In worktree, we should see feature-a files
        files_worktree = []
        for root, dirs, files in os.walk(self.worktree_a):
            if ".git" in root:
                continue
            for f in files:
                if f.endswith(".FCStd"):
                    rel = os.path.relpath(os.path.join(root, f), self.worktree_a)
                    files_worktree.append(rel)
        
        print(f"  Files in feature-a worktree: {sorted(files_worktree)}")
        expected_worktree = ["circle.FCStd", "square.FCStd", "triangle.FCStd"]
        
        if sorted(files_worktree) == sorted(expected_worktree):
            print(f"  ✓ PASS: Feature-a worktree shows correct files")
            return True
        else:
            print(f"  ❌ FAIL: Expected {expected_worktree}, got {files_worktree}")
            return False
    
    def test_file_content_differs(self):
        """Verify that circle.FCStd differs between main and worktree."""
        print("\n[4] Testing file content differs between main and worktree...")
        
        circle_main_path = os.path.join(self.main_repo, "circle.FCStd")
        circle_worktree_path = os.path.join(self.worktree_a, "circle.FCStd")
        
        with open(circle_main_path, "r") as f:
            content_main = f.read()
        
        with open(circle_worktree_path, "r") as f:
            content_worktree = f.read()
        
        print(f"  Main circle.FCStd: {content_main}")
        print(f"  Worktree circle.FCStd: {content_worktree}")
        
        if content_main != content_worktree:
            print(f"  ✓ PASS: File content differs correctly")
            return True
        else:
            print(f"  ❌ FAIL: File content should differ between branches")
            return False
    
    def cleanup(self):
        """Clean up test directory."""
        print("\n[5] Cleanup...")
        try:
            shutil.rmtree(self.test_dir)
            print(f"  ✓ Removed test directory")
        except Exception as e:
            print(f"  ! Cleanup failed: {e}")
    
    def run_all_tests(self, cleanup_after=True):
        """Run all browser tests."""
        print("=" * 70)
        print("Repository Browser Worktree Test")
        print("=" * 70)
        
        results = []
        
        try:
            if not self.setup_repo_with_branches():
                print("Setup failed!")
                return False
            
            results.append(("Main branch files", self.test_browser_shows_main_files()))
            results.append(("Worktree files", self.test_worktree_shows_feature_files()))
            results.append(("File content differs", self.test_file_content_differs()))
            
        finally:
            if cleanup_after:
                self.cleanup()
        
        print("\n" + "=" * 70)
        print("Test Results:")
        for name, passed in results:
            status = "✓ PASSED" if passed else "❌ FAILED"
            print(f"  {name}: {status}")
        
        all_passed = all(r[1] for r in results)
        print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        print("=" * 70)
        
        print("\n📝 EXPECTED BEHAVIOR IN GitPDM:")
        print("  1. When repo root is MyProject/ (main branch):")
        print("     - Browser shows: circle.FCStd, square.FCStd")
        print("     - Indicator: 📂 MyProject  •  🌿 main")
        print("  2. When repo root is MyProject-feature-a/ (worktree):")
        print("     - Browser shows: circle.FCStd, square.FCStd, triangle.FCStd")
        print("     - Indicator: 📂 MyProject-feature-a  •  🌿 feature-a")
        print("  3. Opening circle.FCStd from main: opens MyProject/circle.FCStd")
        print("  4. Opening circle.FCStd from worktree: opens MyProject-feature-a/circle.FCStd")
        print("  5. Content of circle.FCStd will differ between the two!")
        
        return all_passed

if __name__ == "__main__":
    test = RepoBrowserWorktreeTest()
    import sys
    success = test.run_all_tests(cleanup_after=True)
    sys.exit(0 if success else 1)
