# -*- coding: utf-8 -*-
"""
Tests for GitCAD integration layer (Sprint 3)
Tests native Python core implementation.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path

from freecad_gitpdm.export import gitcad_integration


class TestNativeCoreIntegration:
    """Test native Python core integration."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository with GitCAD config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            
            # Create .git directory
            (repo / ".git").mkdir()
            
            # Create GitCAD config
            config_dir = repo / "FreeCAD_Automation"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text("""{
                "uncompressed-directory-structure": {
                    "uncompressed-directory-suffix": "_uncompressed",
                    "uncompressed-directory-prefix": "",
                    "subdirectory": {
                        "put-uncompressed-directory-in-subdirectory": false,
                        "subdirectory-name": ""
                    }
                },
                "compress-non-human-readable-FreeCAD-files": {
                    "enabled": false,
                    "files-to-compress": [],
                    "max-compressed-file-size-gigabyte": 2.0,
                    "compression-level": 6,
                    "zip-file-prefix": "binaries_"
                },
                "require-lock-to-modify-FreeCAD-files": false,
                "include-thumbnails": true
            }""")
            
            yield repo
    
    @pytest.fixture
    def sample_fcstd(self, temp_repo):
        """Create a sample .FCStd file (ZIP archive)."""
        fcstd_path = temp_repo / "test.FCStd"
        
        with zipfile.ZipFile(fcstd_path, 'w') as zf:
            zf.writestr("Document.xml", "<Document/>")
            zf.writestr("GuiDocument.xml", "<GuiDocument/>")
        
        return fcstd_path
    
    def test_export_with_native_core(self, temp_repo, sample_fcstd):
        """Test export using native Python core."""
        # Export the file
        result = gitcad_integration.gitcad_export_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        assert result is True
        
        # Check that uncompressed directory was created
        uncompressed_dir = temp_repo / "test_uncompressed"
        assert uncompressed_dir.exists()
        assert (uncompressed_dir / "Document.xml").exists()
        assert (uncompressed_dir / "GuiDocument.xml").exists()
    
    def test_import_with_native_core(self, temp_repo, sample_fcstd):
        """Test import using native Python core."""
        # First export to create uncompressed directory
        gitcad_integration.gitcad_export_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        # Delete the FCStd file
        sample_fcstd.unlink()
        
        # Import should recreate it
        result = gitcad_integration.gitcad_import_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        assert result is True
        assert sample_fcstd.exists()
        
        # Verify it's a valid ZIP
        with zipfile.ZipFile(sample_fcstd, 'r') as zf:
            assert "Document.xml" in zf.namelist()
            assert "GuiDocument.xml" in zf.namelist()
    
    def test_export_non_fcstd_file(self, temp_repo):
        """Test that non-.FCStd files are ignored."""
        # Try to export a .txt file
        txt_file = temp_repo / "test.txt"
        txt_file.write_text("test")
        
        result = gitcad_integration.gitcad_export_if_available(
            str(temp_repo),
            str(txt_file)
        )
        
        # Should return True but do nothing
        assert result is True
    
    def test_import_nonexistent_uncompressed_dir(self, temp_repo, sample_fcstd):
        """Test that import handles missing uncompressed directory gracefully."""
        # Try to import without exporting first
        result = gitcad_integration.gitcad_import_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        # Should return True (not an error, just nothing to import)
        assert result is True
    
    def test_roundtrip_preserves_content(self, temp_repo, sample_fcstd):
        """Test that export then import preserves file content."""
        # Read original content
        original_content = sample_fcstd.read_bytes()
        
        # Export
        gitcad_integration.gitcad_export_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        # Delete and import
        sample_fcstd.unlink()
        gitcad_integration.gitcad_import_if_available(
            str(temp_repo),
            str(sample_fcstd)
        )
        
        # Verify content is similar (may not be byte-identical due to ZIP compression)
        assert sample_fcstd.exists()
        with zipfile.ZipFile(sample_fcstd, 'r') as zf:
            assert "Document.xml" in zf.namelist()
            assert zf.read("Document.xml") == b"<Document/>"


# Sprint 3: Feature flag tests removed - native core is now the only implementation
