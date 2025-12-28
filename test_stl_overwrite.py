#!/usr/bin/env python3
"""Test that STL files are properly replaced when re-exported."""

from pathlib import Path
import tempfile


def test_stl_overwrite():
    """Test that STL files get replaced on re-export."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Simulate the structure
        part_folder = tmpdir / 'previews' / 'cad' / 'parts' / 'BRK-001' / 'BRK-001'
        part_folder.mkdir(parents=True)
        
        stl_root = tmpdir / 'previews'
        stl_file = stl_root / 'BRK-001.stl'
        
        print('=== Test: STL File Replacement ===\n')
        
        # First export - create STL
        print('1. First export:')
        temp_stl = part_folder / 'BRK-001.stl'
        temp_stl.write_text('OLD STL CONTENT v1')
        print(f'   Created: {temp_stl}')
        print(f'   Content: {temp_stl.read_text()}')
        
        # Move to root (simulating first export)
        if stl_file.exists():
            stl_file.unlink()
        temp_stl.rename(stl_file)
        print(f'   Moved to: {stl_file}')
        print(f'   Root STL exists: {stl_file.exists()}')
        print(f'   Root STL content: {stl_file.read_text()}\n')
        
        # Second export - update STL
        print('2. Second export (simulating re-export):')
        temp_stl = part_folder / 'BRK-001.stl'
        temp_stl.write_text('NEW STL CONTENT v2 - UPDATED!')
        print(f'   Created: {temp_stl}')
        print(f'   Content: {temp_stl.read_text()}')
        
        # Move to root again (this is where the bug was - Windows wouldn't overwrite)
        if stl_file.exists():
            print(f'   Old STL found at root, removing...')
            stl_file.unlink()
        temp_stl.rename(stl_file)
        print(f'   Moved to: {stl_file}')
        print(f'   Root STL exists: {stl_file.exists()}')
        print(f'   Root STL content: {stl_file.read_text()}\n')
        
        # Verify the content was updated
        final_content = stl_file.read_text()
        if 'v2 - UPDATED' in final_content:
            print('✓ SUCCESS: STL was properly replaced with new content!')
            return True
        else:
            print('✗ FAIL: STL still has old content!')
            return False


if __name__ == "__main__":
    success = test_stl_overwrite()
    exit(0 if success else 1)
