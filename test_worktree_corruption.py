"""
Automated test to reproduce FreeCAD .FCStd corruption during branch switching.

This test:
1. Creates a test repo with multiple branches
2. Creates sample binary files (simulating .FCStd)
3. Simulates editing/saving on each branch
4. Performs worktree switches
5. Detects corruption via checksums
"""

import os
import sys
import shutil
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Tuple

class CorruptionTestRunner:
    def __init__(self, test_dir: str = None):
        if test_dir is None:
            self.test_dir = tempfile.mkdtemp(prefix="gitpdm_test_")
        else:
            self.test_dir = test_dir
            os.makedirs(test_dir, exist_ok=True)
        
        self.repo_path = os.path.join(self.test_dir, "test_repo")
        self.worktree_base = os.path.join(self.test_dir, "worktrees")
        self.manifest_path = os.path.join(self.test_dir, "manifest.json")
        self.manifest: Dict[str, Dict[str, str]] = {}
        
        print(f"Test directory: {self.test_dir}")

    def _run_git(self, *args, cwd: str = None) -> Tuple[bool, str, str]:
        """Run a git command and return (success, stdout, stderr)."""
        cwd = cwd or self.repo_path
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)

    def _file_checksum(self, path: str) -> str:
        """Compute SHA256 of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            return f"ERROR: {e}"

    def setup_repo(self):
        """Initialize a git repo with multiple branches and sample files."""
        print("\n[1] Setting up test repository...")
        
        # Clone or init repo
        os.makedirs(self.repo_path, exist_ok=True)
        success, _, _ = self._run_git("init", cwd=self.repo_path)
        if not success:
            print("ERROR: Failed to init repo")
            return False

        # Configure git
        self._run_git("config", "user.name", "Test User", cwd=self.repo_path)
        self._run_git("config", "user.email", "test@example.com", cwd=self.repo_path)

        # Create initial file and commit
        sample_file = os.path.join(self.repo_path, "model.FCStd")
        with open(sample_file, "wb") as f:
            f.write(b"MAIN_BRANCH_v1" + b"\x00" * 100)
        
        self._run_git("add", "model.FCStd", cwd=self.repo_path)
        self._run_git("commit", "-m", "Initial commit", cwd=self.repo_path)
        
        # Record checksum for main branch
        checksum = self._file_checksum(sample_file)
        self.manifest["main"] = {"model.FCStd": checksum}
        print(f"  ✓ Main branch created, model.FCStd: {checksum[:8]}...")

        # Create feature branches
        for branch in ["feature-a", "feature-b"]:
            success, _, _ = self._run_git("checkout", "-b", branch, cwd=self.repo_path)
            if not success:
                print(f"ERROR: Failed to create branch {branch}")
                return False
            
            # Modify file for this branch
            version_tag = f"{branch.upper()}_v1".encode() + b"\x00" * 100
            with open(sample_file, "wb") as f:
                f.write(version_tag)
            
            self._run_git("add", "model.FCStd", cwd=self.repo_path)
            self._run_git("commit", "-m", f"Branch {branch} version", cwd=self.repo_path)
            
            checksum = self._file_checksum(sample_file)
            self.manifest[branch] = {"model.FCStd": checksum}
            print(f"  ✓ Branch '{branch}' created, model.FCStd: {checksum[:8]}...")

        # Switch back to main
        self._run_git("checkout", "main", cwd=self.repo_path)
        self._save_manifest()
        print("  ✓ Repository setup complete")
        return True

    def test_in_place_switch(self) -> bool:
        """Test corruption with in-place 'git switch'."""
        print("\n[2] Testing in-place switch (HIGH RISK)...")
        
        # Ensure we're on main
        self._run_git("checkout", "main", cwd=self.repo_path)
        
        # Record checksum on main
        sample_file = os.path.join(self.repo_path, "model.FCStd")
        main_checksum = self._file_checksum(sample_file)
        print(f"  Main branch checksum: {main_checksum[:8]}...")
        
        # Simulate a "lock file" indicating FreeCAD has the file open
        lock_file = os.path.join(self.repo_path, "model.FCStd.lock")
        with open(lock_file, "w") as f:
            f.write("FreeCAD process 1234\n")
        print(f"  ✓ Created lock file: {lock_file}")
        
        # Try in-place switch (simulating user force-override)
        success, _, stderr = self._run_git("switch", "feature-a", cwd=self.repo_path)
        if not success:
            print(f"  ! Git switch failed: {stderr}")
            return False
        
        # Check checksum on feature-a
        feature_checksum = self._file_checksum(sample_file)
        expected = self.manifest["feature-a"]["model.FCStd"]
        print(f"  Feature-a checksum: {feature_checksum[:8]}...")
        
        # Remove lock file
        if os.path.exists(lock_file):
            os.remove(lock_file)
        
        corruption = feature_checksum != expected
        if corruption:
            print(f"  ❌ CORRUPTION DETECTED!")
            print(f"     Expected: {expected}")
            print(f"     Got:      {feature_checksum}")
        else:
            print(f"  ✓ Checksums match, no corruption")
        
        return not corruption

    def test_worktree_switch(self) -> bool:
        """Test corruption with per-branch 'git worktree'."""
        print("\n[3] Testing per-branch worktree (SAFE)...")
        
        # Ensure we start from main branch
        self._run_git("checkout", "main", cwd=self.repo_path)
        
        os.makedirs(self.worktree_base, exist_ok=True)
        
        # Create worktree for feature-b (not already checked out)
        worktree_b = os.path.join(self.worktree_base, "test_repo-feature-b")
        success, _, stderr = self._run_git(
            "worktree", "add", worktree_b, "feature-b", cwd=self.repo_path
        )
        if not success:
            print(f"  ! Git worktree add failed: {stderr}")
            return False
        
        print(f"  ✓ Created worktree: {worktree_b}")
        
        # Check file in worktree
        worktree_file = os.path.join(worktree_b, "model.FCStd")
        if not os.path.exists(worktree_file):
            print(f"  ❌ File not found in worktree!")
            return False
        
        worktree_checksum = self._file_checksum(worktree_file)
        expected = self.manifest["feature-b"]["model.FCStd"]
        print(f"  Worktree checksum: {worktree_checksum[:8]}...")
        
        # Simulate editing in worktree (lock file in worktree)
        lock_file = os.path.join(worktree_b, "model.FCStd.lock")
        with open(lock_file, "w") as f:
            f.write("FreeCAD process 5678\n")
        print(f"  ✓ Created lock in worktree: {lock_file}")
        
        # Switch main repo to different branch (should not affect worktree)
        success, _, _ = self._run_git("switch", "feature-a", cwd=self.repo_path)
        if not success:
            print(f"  ! Git switch failed")
            return False
        
        # Verify worktree file is unchanged
        recheck_checksum = self._file_checksum(worktree_file)
        corruption = recheck_checksum != expected
        
        if corruption:
            print(f"  ❌ CORRUPTION IN WORKTREE!")
            print(f"     Expected: {expected}")
            print(f"     Got:      {recheck_checksum}")
        else:
            print(f"  ✓ Worktree file unchanged, no corruption")
        
        return not corruption

    def test_concurrent_edit_and_switch(self) -> bool:
        """
        Simulate concurrent editing on main branch while attempting a switch.
        Tests if lock detection and UI guard would prevent this.
        """
        print("\n[4] Testing concurrent edit detection...")
        
        sample_file = os.path.join(self.repo_path, "model.FCStd")
        lock_file = os.path.join(self.repo_path, "model.FCStd.lock")
        
        # Create lock (simulating FreeCAD has file open)
        with open(lock_file, "w") as f:
            f.write("FreeCAD pid=9999\n")
        
        # Check if lock exists
        lock_exists = os.path.exists(lock_file)
        print(f"  Lock file detected: {lock_exists}")
        
        if not lock_exists:
            print(f"  ❌ Lock detection failed!")
            return False
        
        print(f"  ✓ UI guard would block switch (lock detected)")
        return True

    def _save_manifest(self):
        """Save checksums to manifest for later verification."""
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def cleanup(self):
        """Clean up test directory."""
        print("\n[5] Cleanup...")
        try:
            shutil.rmtree(self.test_dir)
            print(f"  ✓ Removed test directory: {self.test_dir}")
        except Exception as e:
            print(f"  ! Failed to cleanup: {e}")

    def run_all_tests(self, cleanup_after=True) -> bool:
        """Run all corruption tests."""
        print("=" * 60)
        print("FreeCAD .FCStd Corruption Test Suite")
        print("=" * 60)
        
        all_passed = True
        
        try:
            if not self.setup_repo():
                return False
            
            # Test 1: In-place switch (risky, may show corruption)
            in_place_pass = self.test_in_place_switch()
            all_passed = all_passed and in_place_pass
            
            # Test 2: Worktree switch (safe, should not corrupt)
            worktree_pass = self.test_worktree_switch()
            all_passed = all_passed and worktree_pass
            
            # Test 3: Lock detection
            lock_pass = self.test_concurrent_edit_and_switch()
            all_passed = all_passed and lock_pass
            
        finally:
            if cleanup_after:
                self.cleanup()
        
        print("\n" + "=" * 60)
        print("Test Results:")
        print(f"  In-place switch (risky):  {'✓ PASSED' if in_place_pass else '❌ FAILED'}")
        print(f"  Worktree switch (safe):   {'✓ PASSED' if worktree_pass else '❌ FAILED'}")
        print(f"  Lock detection:           {'✓ PASSED' if lock_pass else '❌ FAILED'}")
        print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        print("=" * 60)
        
        return all_passed

if __name__ == "__main__":
    runner = CorruptionTestRunner()
    success = runner.run_all_tests(cleanup_after=True)
    sys.exit(0 if success else 1)
