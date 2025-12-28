#!/usr/bin/env python3
"""Test FCBak file handling with timing simulation."""

from pathlib import Path
import tempfile
import time
import threading


def test_fcbak_timing():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Simulate source directory
        source_dir = tmpdir / 'cad' / 'parts' / 'BRK-001'
        source_dir.mkdir(parents=True)
        
        # Create fake FCStd file
        fcstd_file = source_dir / 'BRK-001.FCStd'
        fcstd_file.write_text('fake fcstd content')
        
        # Simulate the preview directory
        preview_dir = tmpdir / 'previews' / 'cad' / 'parts' / 'BRK-001' / 'BRK-001'
        preview_dir.mkdir(parents=True)
        
        print('Test 1: FCBak exists immediately')
        fcbak_file = source_dir / 'BRK-001.FCBak'
        fcbak_file.write_text('backup content')
        
        # Import the function
        from freecad_gitpdm.export.exporter import _move_fcbak_to_previews
        result = _move_fcbak_to_previews(fcstd_file, preview_dir, 'BRK-001')
        
        print(f'  Result: {result}')
        print(f'  FCBak in source: {fcbak_file.exists()}')
        fcbak_preview = preview_dir / "BRK-001.FCBak"
        print(f'  FCBak in preview: {fcbak_preview.exists()}')
        
        print('\nTest 2: FCBak appears after delay')
        fcstd_file2 = source_dir / 'test2.FCStd'
        fcstd_file2.write_text('test')
        fcbak_file2 = source_dir / 'test2.FCBak'
        
        # Simulate async creation
        def create_delayed():
            time.sleep(0.3)
            fcbak_file2.write_text('delayed backup')
        
        thread = threading.Thread(target=create_delayed)
        thread.start()
        
        result2 = _move_fcbak_to_previews(fcstd_file2, preview_dir, 'test2')
        thread.join()
        
        print(f'  Result: {result2}')
        print(f'  FCBak in source: {fcbak_file2.exists()}')
        fcbak_preview2 = preview_dir / "test2.FCBak"
        print(f'  FCBak in preview: {fcbak_preview2.exists()}')
        
        print('\nTest 3: FCBak never appears')
        fcstd_file3 = source_dir / 'test3.FCStd'
        fcstd_file3.write_text('test')
        # Don't create FCBak - simulates when FreeCAD doesn't create one
        
        result3 = _move_fcbak_to_previews(fcstd_file3, preview_dir, 'test3')
        
        print(f'  Result: {result3}')
        print(f'  (This is expected - no FCBak to move)')


if __name__ == "__main__":
    test_fcbak_timing()
    print('\n✓ All FCBak timing tests completed!')
