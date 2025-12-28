#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test of the OBJ to STL converter.

This creates a simple test OBJ file and converts it to STL,
verifying the converter works correctly.
"""

from pathlib import Path
import tempfile
import struct

# Add the freecad_gitpdm module to path
from freecad_gitpdm.export.stl_converter import obj_to_stl, parse_obj


def create_test_obj(obj_path: Path):
    """Create a simple test OBJ file (a cube)."""
    obj_content = """# Simple test cube
# Vertices
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 1.0 1.0 0.0
v 0.0 1.0 0.0
v 0.0 0.0 1.0
v 1.0 0.0 1.0
v 1.0 1.0 1.0
v 0.0 1.0 1.0

# Faces (bottom, top, front, back, left, right)
f 1 2 3
f 1 3 4
f 5 8 7
f 5 7 6
f 1 4 8
f 1 8 5
f 2 6 7
f 2 7 3
f 4 3 7
f 4 7 8
f 1 5 6
f 1 6 2
"""
    with obj_path.open("w") as f:
        f.write(obj_content)


def verify_stl(stl_path: Path) -> bool:
    """Verify STL file structure."""
    if not stl_path.exists():
        print(f"❌ STL file not created: {stl_path}")
        return False
    
    file_size = stl_path.stat().st_size
    if file_size < 84:
        print(f"❌ STL file too small: {file_size} bytes (min 84)")
        return False
    
    # Binary STL format check
    with stl_path.open("rb") as f:
        # Read header (80 bytes)
        header = f.read(80)
        if len(header) != 80:
            print(f"❌ Header too small: {len(header)} bytes")
            return False
        
        # Read triangle count (4 bytes, little-endian uint32)
        tri_count_bytes = f.read(4)
        if len(tri_count_bytes) != 4:
            print(f"❌ Triangle count field too small")
            return False
        
        tri_count = struct.unpack("<I", tri_count_bytes)[0]
        print(f"✓ Triangle count: {tri_count}")
        
        # Calculate expected file size: 80 (header) + 4 (count) + 50*tri_count
        expected_size = 80 + 4 + (50 * tri_count)
        if file_size != expected_size:
            print(f"⚠ File size mismatch: {file_size} vs expected {expected_size}")
            return False
        
        # Try reading first triangle
        tri_data = f.read(50)
        if len(tri_data) != 50:
            print(f"❌ Could not read first triangle")
            return False
        
        # Parse normal (3 floats)
        normal = struct.unpack("<fff", tri_data[0:12])
        print(f"✓ First triangle normal: {normal}")
        
        # Parse first vertex (3 floats)
        v1 = struct.unpack("<fff", tri_data[12:24])
        print(f"✓ First vertex: {v1}")
    
    print(f"✓ STL structure valid: {tri_count} triangles, {file_size} bytes")
    return True


def main():
    print("=" * 60)
    print("OBJ to STL Converter Test")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test OBJ
        obj_path = tmpdir / "test.obj"
        stl_path = tmpdir / "test.stl"
        
        print("\n1. Creating test OBJ file...")
        create_test_obj(obj_path)
        print(f"   ✓ Created: {obj_path}")
        
        # Parse OBJ to verify
        print("\n2. Parsing OBJ file...")
        verts, tris, err = parse_obj(obj_path)
        if err:
            print(f"   ❌ Parse error: {err}")
            return False
        print(f"   ✓ Parsed {len(verts)} vertices, {len(tris)} triangles")
        
        # Convert to STL
        print("\n3. Converting OBJ to STL...")
        err = obj_to_stl(obj_path, stl_path)
        if err:
            print(f"   ❌ Conversion error: {err}")
            return False
        print(f"   ✓ Converted successfully")
        
        # Verify STL
        print("\n4. Verifying STL structure...")
        if not verify_stl(stl_path):
            return False
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
