# Simple STL converter test
from pathlib import Path
import tempfile
import struct
from freecad_gitpdm.export.stl_converter import obj_to_stl

print("Testing OBJ to STL conversion...")

# Create temp directory
tmpdir = Path(tempfile.mkdtemp())
print(f"Temp dir: {tmpdir}")

# Create simple cube OBJ
obj = tmpdir / "cube.obj"
lines = [
    "v 0 0 0",
    "v 1 0 0",
    "v 1 1 0",
    "v 0 1 0",
    "f 1 2 3",
    "f 1 3 4",
]
obj.write_text("\n".join(lines))
print(f"Created OBJ: {obj}")

# Convert to STL
stl = tmpdir / "cube.stl"
err = obj_to_stl(obj, stl)

if err:
    print(f"❌ Error: {err}")
else:
    # Verify STL
    data = stl.read_bytes()
    tc = struct.unpack("<I", data[80:84])[0]
    file_size = len(data)
    expected_size = 84 + 50 * tc
    
    print(f"✓ Conversion successful!")
    print(f"  Triangle count: {tc}")
    print(f"  File size: {file_size} bytes")
    print(f"  Expected size: {expected_size} bytes")
    
    if file_size == expected_size:
        print(f"✓ File size matches! STL is valid.")
    else:
        print(f"⚠ File size mismatch")
