# -*- coding: utf-8 -*-
"""
GitPDM Jobs Module
Sprint 1: Background job runner using QtCore.QProcess
Sprint OAUTH-1: Added support for running Python callables in worker threads
"""

import threading
from freecad_gitpdm.core import log


def _get_qt_core():
    """
    Lazy import of QtCore to handle FreeCAD-only availability

    Returns:
        QtCore module
    """
    try:
        from PySide6 import QtCore
    except ImportError:
        try:
            from PySide2 import QtCore
        except ImportError:
            raise ImportError(
                "Neither PySide6 nor PySide2 found. "
                "FreeCAD installation may be incomplete."
            )
    return QtCore


class _CallableWorkerSignals:
    """
    Helper object that emits signals to marshal callbacks to UI thread.
    This is a workaround for the fact that threading.Thread doesn't
    integrate with Qt's event loop.
    """

    def __init__(self, qt_core):
        self.QtCore = qt_core

        # Create a QObject subclass dynamically to get signal support
        class _SignalEmitter(qt_core.QObject):
            success = qt_core.Signal(object, str)  # result, name
            error = qt_core.Signal(Exception, str)  # error, name

        self._emitter = _SignalEmitter()

    def connect_success(self, callback):
        """Connect success signal to callback"""
        self._emitter.success.connect(
            lambda result, name: self._invoke_success(callback, result, name)
        )

    def connect_error(self, callback):
        """Connect error signal to callback"""
        self._emitter.error.connect(
            lambda error, name: self._invoke_error(callback, error, name)
        )

    def emit_success(self, result, name):
        """Emit success signal (thread-safe)"""
        self._emitter.success.emit(result, name)

    def emit_error(self, error, name):
        """Emit error signal (thread-safe)"""
        self._emitter.error.emit(error, name)

    def _invoke_success(self, callback, result, name):
        """Called on UI thread"""
        try:
            callback(result)
        except Exception as e:
            log.error(f"Success callback error for {name}: {e}")

    def _invoke_error(self, callback, error, name):
        """Called on UI thread"""
        try:
            callback(error)
        except Exception as e:
            log.error(f"Error callback failed for {name}: {e}")


class GitJobRunner:
    """
    Background job runner for git operations.
    Ensures UI stays responsive by running commands in background.
    Uses QProcess to capture output safely.
    Implements last-request-wins: new requests supersede pending ones.
    """

    def __init__(self):
        QtCore = _get_qt_core()

        # Create as QObject subclass dynamically
        class _Runner(QtCore.QObject):
            job_finished = QtCore.Signal(object)

            def __init__(self):
                super().__init__()
                self._process = None
                self._current_job = None
                self._pending_job = None
                self._qt_core = QtCore

        self._runner = _Runner()

    def run_job(self, job_type, command_args, callback=None):
        """
        Queue a job to run in background.
        If a job is running, this new job becomes pending and will run
        after the current job finishes.
        If a job is already pending, it is replaced with this new one.

        Args:
            job_type: str - identifier for the job type
                (e.g. "validate_repo", "get_status")
            command_args: list[str] - command line args (no shell=True)
            callback: callable(dict) - optional callback when job finishes

        Returns:
            None
        """
        job = {
            "type": job_type,
            "args": command_args,
            "callback": callback,
            "result": None,
            "error": None,
        }

        if self._runner._current_job is None:
            # No job running, start this one immediately
            self._start_job(job)
        else:
            # Job running, replace any pending job with this one
            if self._runner._pending_job is not None:
                log.debug(
                    f"Replacing pending job "
                    f"{self._runner._pending_job['type']} "
                    f"with {job_type}"
                )
            self._runner._pending_job = job

    def _start_job(self, job):
        """
        Start a job immediately using QProcess

        Args:
            job: dict - job descriptor
        """
        QtCore = self._runner._qt_core

        if self._runner._process is not None:
            self._runner._process.deleteLater()

        self._runner._current_job = job
        self._runner._process = QtCore.QProcess(self._runner)
        self._runner._process.finished.connect(self._on_job_finished)
        self._runner._process.errorOccurred.connect(self._on_job_error)

        log.debug(f"Starting job {job['type']}: {' '.join(job['args'][:2])}")

        # Start process without shell
        self._runner._process.start(job["args"][0], job["args"][1:])

    def _on_job_finished(self, exit_code):
        """
        Called when a job finishes

        Args:
            exit_code: int - process exit code
        """
        if self._runner._current_job is None:
            return

        job = self._runner._current_job
        stdout = ""
        stderr = ""

        if self._runner._process is not None:
            stdout = bytes(self._runner._process.readAllStandardOutput()).decode(
                "utf-8", errors="replace"
            )
            stderr = bytes(self._runner._process.readAllStandardError()).decode(
                "utf-8", errors="replace"
            )

        job["result"] = {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "exit_code": exit_code,
            "success": exit_code == 0,
        }

        log.debug(f"Job {job['type']} finished with code {exit_code}")

        # Call the callback if provided
        if job["callback"]:
            try:
                job["callback"](job)
            except Exception as e:
                log.error(f"Job callback error: {e}")

        # Emit signal
        self._runner.job_finished.emit(job)

        self._runner._current_job = None

        # Process any pending job
        if self._runner._pending_job is not None:
            pending = self._runner._pending_job
            self._runner._pending_job = None
            self._start_job(pending)

    def _on_job_error(self, error):
        """
        Called when job process encounters an error

        Args:
            error: QProcess.ProcessError
        """
        if self._runner._current_job is None:
            return

        job = self._runner._current_job
        log.error(f"Job {job['type']} process error: {error}")

        job["error"] = str(error)
        job["result"] = {
            "stdout": "",
            "stderr": str(error),
            "exit_code": -1,
            "success": False,
        }

        # Call callback
        if job["callback"]:
            try:
                job["callback"](job)
            except Exception as e:
                log.error(f"Job callback error: {e}")

        # Emit signal
        self._runner.job_finished.emit(job)

        self._runner._current_job = None

        # Process any pending job
        if self._runner._pending_job is not None:
            pending = self._runner._pending_job
            self._runner._pending_job = None
            self._start_job(pending)

    def is_busy(self):
        """
        Check if a job is currently running

        Returns:
            bool: True if a job is running
        """
        return self._runner._current_job is not None

    def run_callable(
        self, name, func, on_success=None, on_error=None, cancel_token=None
    ):
        """
        Run a Python callable in a worker thread.

        This method is useful for network operations (e.g., OAuth polling) that
        would block the UI if run on the main thread.

        Args:
            name: str - Name for this callable job (for logging)
            func: callable() -> result - Function to run in worker thread
                  Must accept no arguments and return a result.
                  If cancel_token is provided, func can check it to support
                  cancellation: if cancel_token.is_cancelled, stop early.
            on_success: callable(result) -> None - Called on UI thread if func succeeds
            on_error: callable(exception) -> None - Called on UI thread if func raises
            cancel_token: CancelToken or None - Token with is_cancelled property
                          that func can check to support cancellation

        Returns:
            None
        """
        QtCore = self._runner._qt_core

        # Create signal emitter for this job
        signals = _CallableWorkerSignals(QtCore)

        # Connect callbacks to signals
        if on_success:
            signals.connect_success(on_success)
        if on_error:
            signals.connect_error(on_error)

        def _worker():
            try:
                log.debug(f"Callable job {name} starting")
                result = func()
                log.debug(f"Callable job {name} completed")

                # Emit success signal (thread-safe, marshals to UI thread)
                if on_success:
                    signals.emit_success(result, name)
            except Exception as e:
                log.error(f"Callable job {name} failed: {e}")

                # Emit error signal (thread-safe, marshals to UI thread)
                if on_error:
                    signals.emit_error(e, name)

        thread = threading.Thread(target=_worker, daemon=True)
        log.debug(f"Starting callable job {name}")
        thread.start()

    @property
    def job_finished(self):
        """Get the job_finished signal for connections"""
        return self._runner.job_finished


# Global instance (singleton-like, created on demand)
_global_job_runner = None


def get_job_runner():
    """
    Get or create the global job runner instance.
    Only initializes when first called (lazy init).

    Returns:
        GitJobRunner: The global job runner
    """
    global _global_job_runner
    if _global_job_runner is None:
        _global_job_runner = GitJobRunner()
    return _global_job_runner
