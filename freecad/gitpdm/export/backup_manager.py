"""
FCBak backup file management for GitPDM.

Handles FreeCAD's automatic backup files (FCBak) by moving them from
source directories to organized preview/Backup folders with configurable
retention policies.
"""

import time
from pathlib import Path
from freecad.gitpdm.core import log


def move_fcbak_to_previews(
    source_fcstd: Path, preview_dir: Path, part_name: str, max_backups: int = 3
) -> bool:
    """
    Move FCBak file from source directory to preview folder.
    FreeCAD creates FCBak files during save with timestamps (e.g., filename.20251230-213417.FCBak).
    This function waits briefly for the file to appear before moving it.
    Also cleans up old backups keeping only the most recent max_backups files.

    Args:
        source_fcstd: Path to the source FCStd file
        preview_dir: Directory where previews are stored
        part_name: Name of the part (used for searching backups)
        max_backups: Maximum number of backup files to keep (default: 3, -1 for unlimited)

    Returns True if FCBak was moved, False otherwise.
    """
    parent = source_fcstd.parent
    stem = source_fcstd.stem  # Get filename without extension

    log.info(f"Looking for FCBak files matching: {stem}.*.FCBak in {parent}")
    log.info(f"Max backups to keep: {max_backups}")

    # Wait up to 2 seconds for FCBak to appear (FreeCAD creates it asynchronously)
    max_attempts = 20
    wait_interval = 0.1  # 100ms

    moved_successfully = False

    for attempt in range(max_attempts):
        try:
            # Search for FCBak files matching the pattern: filename.*.FCBak
            # FreeCAD creates files like "Square Test.20251230-213417.FCBak"
            pattern = f"{stem}.*.FCBak"
            fcbak_files = list(parent.glob(pattern))

            if fcbak_files:
                # Get the most recent FCBak file (in case there are multiple)
                fcbak_source = max(fcbak_files, key=lambda p: p.stat().st_mtime)
                log.info(f"Found FCBak file: {fcbak_source}")

                try:
                    # Create Backup subfolder inside preview directory
                    backup_dir = preview_dir / "Backup"
                    backup_dir.mkdir(parents=True, exist_ok=True)

                    # Keep the timestamped name in the backup folder
                    fcbak_dest = backup_dir / fcbak_source.name
                    # Remove existing FCBak if present (Windows won't overwrite on rename)
                    if fcbak_dest.exists():
                        fcbak_dest.unlink()
                    # Move FCBak to the part's preview/Backup folder
                    fcbak_source.rename(fcbak_dest)
                    log.info(f"FCBak moved to previews/Backup: {fcbak_dest.name}")
                    moved_successfully = True

                    # Clean up old backups - keep only the most recent max_backups files
                    # Skip cleanup if max_backups is -1 (unlimited) or 0 (no backups)
                    if max_backups > 0:
                        cleanup_old_backups(backup_dir, stem, max_backups)

                    return True
                except Exception as e:
                    log.warning(f"Failed to move FCBak: {e}")
                    return False
        except Exception as e:
            log.warning(f"Error searching for FCBak: {e}")

        # Wait a bit before checking again
        if attempt < max_attempts - 1 and not moved_successfully:
            time.sleep(wait_interval)

    # FCBak file never appeared (this is normal if FreeCAD didn't create one)
    log.debug(f"No FCBak file found matching {stem}.*.FCBak")
    return False


def cleanup_old_backups(backup_dir: Path, part_stem: str, max_backups: int):
    """
    Remove old backup files, keeping only the most recent max_backups files.

    Args:
        backup_dir: Directory containing backup files
        part_stem: Stem of the part name (e.g., "Square Test")
        max_backups: Maximum number of backups to keep
    """
    try:
        # Find all backup files for this part
        pattern = f"{part_stem}.*.FCBak"
        backup_files = list(backup_dir.glob(pattern))

        if len(backup_files) <= max_backups:
            return  # Nothing to clean up

        # Sort by modification time, newest first
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Remove old backups beyond the limit
        files_to_remove = backup_files[max_backups:]
        for old_backup in files_to_remove:
            try:
                old_backup.unlink()
                log.info(f"Removed old backup: {old_backup.name}")
            except Exception as e:
                log.warning(f"Failed to remove old backup {old_backup.name}: {e}")
    except Exception as e:
        log.warning(f"Failed to cleanup old backups: {e}")
