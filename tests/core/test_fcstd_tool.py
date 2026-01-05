"""
Tests for fcstd_tool module
Sprint 1: Core logic migration testing
"""

import pytest
from pathlib import Path
import tempfile
import zipfile
import shutil

from freecad.gitpdm.core import fcstd_tool
from freecad.gitpdm.core.config_manager import FCStdConfig


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / \".git\").mkdir()
        (repo / \".gitpdm\").mkdir()
        
        # Create a default config
        config_file = repo / \".gitpdm\" / \"config.json\"
        config = FCStdConfig()
        
        import json
        with open(config_file, 'w') as f:
            json.dump(config.to_dict(), f)
        
        yield repo


@pytest.fixture
def sample_fcstd(temp_repo):
    """Create a sample .FCStd file (simple ZIP with some files)."""
    fcstd_path = temp_repo / "test.FCStd"
    
    # Create a simple ZIP file (FCStd is just a ZIP)
    with zipfile.ZipFile(fcstd_path, 'w') as zf:
        zf.writestr("Document.xml", "<Document></Document>")
        zf.writestr("GuiDocument.xml", "<GuiDocument></GuiDocument>")
        zf.writestr("Shape.brp", b"\x00\x01\x02\x03")  # Fake binary
    
    return fcstd_path


class TestExportFCStd:
    """Tests for export_fcstd function."""
    
    def test_export_creates_directory(self, sample_fcstd, temp_repo):
        """Test that export creates an uncompressed directory."""
        result = fcstd_tool.export_fcstd(sample_fcstd)
        
        assert result.ok
        assert isinstance(result.value, fcstd_tool.ExportResult)
        
        output_dir = result.value.output_dir
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_export_extracts_files(self, sample_fcstd, temp_repo):
        """Test that export extracts all files from FCStd."""
        result = fcstd_tool.export_fcstd(sample_fcstd)
        
        assert result.ok
        output_dir = result.value.output_dir
        
        # Check expected files exist
        assert (output_dir / "Document.xml").exists()
        assert (output_dir / "GuiDocument.xml").exists()
        assert (output_dir / "Shape.brp").exists()
        
        # Check file count
        assert result.value.files_exported >= 3
    
    def test_export_handles_missing_file(self, temp_repo):
        """Test error handling for missing file."""
        missing_file = temp_repo / "missing.FCStd"
        
        result = fcstd_tool.export_fcstd(missing_file)
        
        assert not result.ok
        assert result.error.code == "FILE_NOT_FOUND"
    
    def test_export_handles_invalid_extension(self, temp_repo):
        """Test error handling for non-FCStd file."""
        invalid_file = temp_repo / "test.txt"
        invalid_file.write_text("not a fcstd")
        
        result = fcstd_tool.export_fcstd(invalid_file)
        
        assert not result.ok
        assert result.error.code == "INVALID_FILE"
    
    def test_export_uses_config_suffix(self, sample_fcstd, temp_repo):
        """Test that export respects config suffix."""
        config = FCStdConfig(uncompressed_suffix="_data")
        
        result = fcstd_tool.export_fcstd(sample_fcstd, config=config)
        
        assert result.ok
        assert "_data" in str(result.value.output_dir)
    
    def test_export_custom_output_dir(self, sample_fcstd, temp_repo):
        """Test export to a custom directory."""
        custom_dir = temp_repo / "custom_output"
        
        result = fcstd_tool.export_fcstd(sample_fcstd, output_dir=custom_dir)
        
        assert result.ok
        assert result.value.output_dir == custom_dir
        assert custom_dir.exists()


class TestImportFCStd:
    """Tests for import_fcstd function."""
    
    def test_import_creates_fcstd(self, temp_repo):
        """Test that import creates a .FCStd file."""
        # Create an uncompressed directory
        input_dir = temp_repo / "test_uncompressed"
        input_dir.mkdir()
        (input_dir / "Document.xml").write_text("<Document></Document>")
        (input_dir / "GuiDocument.xml").write_text("<GuiDocument></GuiDocument>")
        
        fcstd_path = temp_repo / "output.FCStd"
        
        result = fcstd_tool.import_fcstd(input_dir, fcstd_path)
        
        assert result.ok
        assert fcstd_path.exists()
        assert fcstd_path.suffix == ".FCStd"
    
    def test_import_creates_valid_zip(self, temp_repo):
        """Test that import creates a valid ZIP file."""
        # Create input directory
        input_dir = temp_repo / "test_uncompressed"
        input_dir.mkdir()
        (input_dir / "Document.xml").write_text("<Document></Document>")
        
        fcstd_path = temp_repo / "output.FCStd"
        
        result = fcstd_tool.import_fcstd(input_dir, fcstd_path)
        
        assert result.ok
        
        # Verify it's a valid ZIP
        assert zipfile.is_zipfile(fcstd_path)
        
        # Verify contents
        with zipfile.ZipFile(fcstd_path, 'r') as zf:
            assert "Document.xml" in zf.namelist()
    
    def test_import_handles_missing_dir(self, temp_repo):
        """Test error handling for missing directory."""
        missing_dir = temp_repo / "missing_dir"
        fcstd_path = temp_repo / "output.FCStd"
        
        result = fcstd_tool.import_fcstd(missing_dir, fcstd_path)
        
        assert not result.ok
        assert result.error.code == "DIR_NOT_FOUND"
    
    def test_import_handles_file_instead_of_dir(self, temp_repo):
        """Test error handling when input is a file, not directory."""
        not_a_dir = temp_repo / "file.txt"
        not_a_dir.write_text("test")
        
        fcstd_path = temp_repo / "output.FCStd"
        
        result = fcstd_tool.import_fcstd(not_a_dir, fcstd_path)
        
        assert not result.ok
        assert result.error.code == "NOT_A_DIRECTORY"


class TestRoundTrip:
    """Test export then import roundtrip."""
    
    def test_export_import_roundtrip(self, sample_fcstd, temp_repo):
        """Test that export then import produces equivalent file."""
        # Export
        export_result = fcstd_tool.export_fcstd(sample_fcstd)
        assert export_result.ok
        
        output_dir = export_result.value.output_dir
        
        # Import to new file
        new_fcstd = temp_repo / "roundtrip.FCStd"
        import_result = fcstd_tool.import_fcstd(output_dir, new_fcstd)
        assert import_result.ok
        
        # Verify new file is valid
        assert zipfile.is_zipfile(new_fcstd)
        
        # Compare contents (both should have same files)
        with zipfile.ZipFile(sample_fcstd, 'r') as zf1:
            with zipfile.ZipFile(new_fcstd, 'r') as zf2:
                assert set(zf1.namelist()) == set(zf2.namelist())


class TestFindRepoRoot:
    """Tests for _find_repo_root helper."""
    
    def test_finds_repo_root(self, temp_repo):
        """Test finding repository root."""
        # Create subdirectory
        subdir = temp_repo / "parts" / "brackets"
        subdir.mkdir(parents=True)
        
        # Should find repo root from subdirectory
        root = fcstd_tool._find_repo_root(subdir)
        assert root == temp_repo
    
    def test_raises_when_not_in_repo(self):
        """Test error when not in a repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            not_a_repo = Path(tmpdir)
            
            with pytest.raises(RuntimeError, match="Not in a git repository"):
                fcstd_tool._find_repo_root(not_a_repo)


# TODO: Sprint 1, Task 1.3 - Add tests for binary compression
# class TestBinaryCompression:
#     def test_compress_binaries(self):
#         pass
#
#     def test_decompress_binaries(self):
#         pass
