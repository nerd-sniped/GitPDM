#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sprint 7 Test Script
Tests GLB export, mesh stats, and publish workflow components
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_preset_mesh_settings():
    """Test that preset loader handles mesh settings correctly."""
    print("\n=== Test 1: Preset Mesh Settings ===")
    
    from freecad_gitpdm.export import preset
    
    # Test default mesh settings
    result = preset.load_preset("/nonexistent/repo")
    assert result.preset is not None, "Should return preset"
    assert result.error is None, "Should not have error with defaults"
    assert "mesh" in result.preset
    
    mesh = result.preset["mesh"]
    assert mesh["linearDeflection"] == 0.1, "Default linearDeflection"
    assert mesh["angularDeflectionDeg"] == 15, "Default angularDeflectionDeg"
    assert mesh["relative"] is False, "Default relative"
    
    print("✓ Default mesh settings loaded correctly")
    print(f"  linearDeflection: {mesh['linearDeflection']}")
    print(f"  angularDeflectionDeg: {mesh['angularDeflectionDeg']}")
    print(f"  relative: {mesh['relative']}")


def test_publish_coordinator():
    """Test PublishCoordinator initialization and structure."""
    print("\n=== Test 2: Publish Coordinator ===")
    
    from freecad_gitpdm.core import publish
    from freecad_gitpdm.git import client
    
    # Create mock git client
    git_client = client.GitClient()
    
    # Create coordinator (only takes git_client)
    coordinator = publish.PublishCoordinator(git_client)
    
    assert coordinator is not None
    assert hasattr(coordinator, 'precheck')
    assert hasattr(coordinator, 'export_previews')
    assert hasattr(coordinator, 'stage_files')
    assert hasattr(coordinator, 'commit_changes')
    assert hasattr(coordinator, 'push_to_remote')
    
    print("✓ PublishCoordinator has all required methods")
    print(f"  - precheck")
    print(f"  - export_previews")
    print(f"  - stage_files")
    print(f"  - commit_changes")
    print(f"  - push_to_remote")


def test_publish_result():
    """Test PublishResult dataclass."""
    print("\n=== Test 3: Publish Result ===")
    
    from freecad_gitpdm.core import publish
    
    # Test success result
    result = publish.PublishResult(
        ok=True,
        step=publish.PublishStep.PUSH,
        message="Success",
        details={"pushed": True}
    )
    
    assert result.ok is True
    assert result.step == publish.PublishStep.PUSH
    assert result.message == "Success"
    assert result.details == {"pushed": True}
    
    print("✓ PublishResult structure correct")
    print(f"  ok: {result.ok}")
    print(f"  step: {result.step.name}")
    print(f"  message: {result.message}")


def test_export_result_glb_fields():
    """Test that ExportResult has GLB-related fields."""
    print("\n=== Test 4: Export Result GLB Fields ===")
    
    from freecad_gitpdm.export import exporter
    
    # Create a result with GLB fields
    result = exporter.ExportResult(
        ok=True,
        message="Test",
        rel_dir="previews/test/",
        png_path="/path/to/preview.png",
        json_path="/path/to/preview.json",
        thumbnail_error=None,
        glb_path="/path/to/model.glb",
        glb_error=None,
        mesh_stats={"triangles": 1234, "vertices": 567},
        warnings=["test warning"],
        preset_used={"presetVersion": 1}
    )
    
    assert result.glb_path == "/path/to/model.glb"
    assert result.glb_error is None
    assert result.mesh_stats["triangles"] == 1234
    assert result.mesh_stats["vertices"] == 567
    assert len(result.warnings) == 1
    
    print("✓ ExportResult has Sprint 7 fields")
    print(f"  glb_path: {result.glb_path}")
    print(f"  mesh_stats: {result.mesh_stats}")
    print(f"  warnings: {result.warnings}")


def main():
    """Run all tests."""
    print("Sprint 7 Test Suite")
    print("=" * 50)
    
    try:
        test_preset_mesh_settings()
        test_publish_coordinator()
        test_publish_result()
        test_export_result_glb_fields()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return 0
    
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
