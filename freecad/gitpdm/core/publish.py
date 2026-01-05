"""
Publish Coordinator for GitPDM (Sprint 7)

Orchestrates precheck -> export -> stage -> commit -> push workflow.
Designed to be called from UI with progress callbacks.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from freecad.gitpdm.core import log
from freecad.gitpdm.core import paths as core_paths
from freecad.gitpdm.export import exporter
from freecad.gitpdm.git import client


class PublishStep(Enum):
    PRECHECK = "precheck"
    EXPORT = "export"
    STAGE = "stage"
    COMMIT = "commit"
    PUSH = "push"
    DONE = "done"


@dataclass
class PublishResult:
    ok: bool
    step: PublishStep
    message: str
    details: Optional[Dict[str, Any]] = None


class PublishCoordinator:
    """
    Coordinates multi-step publish workflow.
    Keeps UI responsive by yielding between steps.
    """

    def __init__(self, git_client: client.GitClient):
        self.git = git_client
        self.current_step = PublishStep.PRECHECK
        self.abort_requested = False

    def precheck(self, repo_root: str, remote: str = "origin") -> PublishResult:
        """
        Run preflight checks before publish.
        Returns PublishResult with ok=True if ready.
        """
        try:
            import FreeCAD

            doc = FreeCAD.ActiveDocument
        except Exception:
            doc = None

        if not doc:
            return PublishResult(
                ok=False,
                step=PublishStep.PRECHECK,
                message="No active document",
            )

        file_name = getattr(doc, "FileName", "")
        if not file_name:
            return PublishResult(
                ok=False,
                step=PublishStep.PRECHECK,
                message="Document not saved",
            )

        if not core_paths.is_inside_repo(file_name, repo_root):
            return PublishResult(
                ok=False,
                step=PublishStep.PRECHECK,
                message="Document outside repo",
            )

        if not self.git.is_git_available():
            return PublishResult(
                ok=False,
                step=PublishStep.PRECHECK,
                message="Git not available",
            )

        if not self.git.has_remote(repo_root, remote):
            return PublishResult(
                ok=False,
                step=PublishStep.PRECHECK,
                message=f"Remote '{remote}' not found",
            )

        # Check ahead/behind
        upstream = self.git.default_upstream_ref(repo_root, remote)
        behind = 0
        if upstream:
            ab = self.git.ahead_behind(repo_root, upstream)
            if ab["ok"]:
                behind = ab["behind"]

        # Check working tree (allow dirty if only preview artifacts)
        has_changes = self.git.has_uncommitted_changes(repo_root)

        return PublishResult(
            ok=True,
            step=PublishStep.PRECHECK,
            message="Precheck passed",
            details={
                "file_name": file_name,
                "behind": behind,
                "has_changes": has_changes,
                "upstream": upstream,
            },
        )

    def export_previews(self, repo_root: str) -> PublishResult:
        """
        Run export (PNG + JSON + GLB).
        """
        self.current_step = PublishStep.EXPORT

        result = exporter.export_active_document(repo_root)

        if not result.ok:
            return PublishResult(
                ok=False,
                step=PublishStep.EXPORT,
                message=result.message or "Export failed",
                details={"export_result": result},
            )

        warnings = []
        if result.thumbnail_error:
            warnings.append(result.thumbnail_error)
        if result.glb_error:
            warnings.append(result.glb_error)
        warnings.extend(result.warnings or [])

        return PublishResult(
            ok=True,
            step=PublishStep.EXPORT,
            message="Export completed",
            details={
                "export_result": result,
                "warnings": warnings,
            },
        )

    def stage_files(
        self,
        repo_root: str,
        source_path: str,
        export_result: exporter.ExportResult,
        stage_all: bool = False,
    ) -> PublishResult:
        """
        Stage source + artifacts.
        """
        self.current_step = PublishStep.STAGE

        paths_to_stage = []

        # Source file
        src_rel = core_paths.to_repo_rel(source_path, repo_root)
        if src_rel:
            paths_to_stage.append(src_rel)

        # Artifacts
        if export_result.png_path and export_result.png_path.exists():
            png_rel = core_paths.to_repo_rel(str(export_result.png_path), repo_root)
            if png_rel:
                paths_to_stage.append(png_rel)

        if export_result.json_path and export_result.json_path.exists():
            json_rel = core_paths.to_repo_rel(str(export_result.json_path), repo_root)
            if json_rel:
                paths_to_stage.append(json_rel)

        if export_result.glb_path and export_result.glb_path.exists():
            glb_rel = core_paths.to_repo_rel(str(export_result.glb_path), repo_root)
            if glb_rel:
                paths_to_stage.append(glb_rel)

        # If requested, stage everything in working tree
        if stage_all:
            cmd_result = self.git.stage_all(repo_root)
        else:
            if not paths_to_stage:
                return PublishResult(
                    ok=False,
                    step=PublishStep.STAGE,
                    message="No files to stage",
                )
            cmd_result = self.git.stage_paths(repo_root, paths_to_stage)

        if not cmd_result.ok:
            return PublishResult(
                ok=False,
                step=PublishStep.STAGE,
                message="Staging failed",
                details={"stderr": cmd_result.stderr},
            )

        return PublishResult(
            ok=True,
            step=PublishStep.STAGE,
            message=f"Staged {len(paths_to_stage)} files",
            details={"staged_paths": paths_to_stage},
        )

    def commit_changes(self, repo_root: str, message: str) -> PublishResult:
        """
        Create commit with message.
        """
        self.current_step = PublishStep.COMMIT

        if not message or not message.strip():
            return PublishResult(
                ok=False,
                step=PublishStep.COMMIT,
                message="Empty commit message",
            )

        cmd_result = self.git.commit(repo_root, message)

        if not cmd_result.ok:
            if cmd_result.error_code == "NOTHING_TO_COMMIT":
                return PublishResult(
                    ok=False,
                    step=PublishStep.COMMIT,
                    message="No changes to commit",
                    details={"error_code": "NOTHING_TO_COMMIT"},
                )
            elif cmd_result.error_code == "MISSING_IDENTITY":
                return PublishResult(
                    ok=False,
                    step=PublishStep.COMMIT,
                    message="Git identity not configured",
                    details={"error_code": "MISSING_IDENTITY"},
                )
            else:
                return PublishResult(
                    ok=False,
                    step=PublishStep.COMMIT,
                    message="Commit failed",
                    details={"stderr": cmd_result.stderr},
                )

        return PublishResult(
            ok=True,
            step=PublishStep.COMMIT,
            message="Commit created",
        )

    def push_to_remote(self, repo_root: str, remote: str = "origin") -> PublishResult:
        """
        Push to remote.
        """
        self.current_step = PublishStep.PUSH

        cmd_result = self.git.push(repo_root, remote)

        if not cmd_result.ok:
            return PublishResult(
                ok=False,
                step=PublishStep.PUSH,
                message="Push failed",
                details={
                    "stderr": cmd_result.stderr,
                    "error_code": cmd_result.error_code,
                },
            )

        return PublishResult(
            ok=True,
            step=PublishStep.PUSH,
            message="Pushed to remote",
        )

    def request_abort(self):
        """Request coordinator to abort (best-effort)."""
        self.abort_requested = True
