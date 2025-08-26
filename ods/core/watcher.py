"""Directory watcher module

Provides a simple wrapper around ``watchdog`` to monitor a directory for
file changes. When a file is created or modified, a callback is invoked
with the path to the changed file.

This implements the "文件夹监听" feature described in the project plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class DirectoryWatcher(FileSystemEventHandler):
    """Watch a directory and notify on file changes.

    Parameters
    ----------
    directory: str
        Path to the directory that should be watched.
    callback: Callable[[str], None]
        Function called with the path of a file whenever it is created or
        modified within the directory tree.
    recursive: bool, optional
        Whether to watch sub-directories as well. Defaults to ``True``.
    """

    def __init__(self, directory: str, callback: Callable[[str], None], *, recursive: bool = True) -> None:
        self._path = str(Path(directory))
        self._callback = callback
        self._observer = Observer()
        self._recursive = recursive

    # ------------------------------------------------------------------
    # FileSystemEventHandler methods
    # ------------------------------------------------------------------
    def on_created(self, event):  # pragma: no cover - exercised via integration test
        if not event.is_directory:
            self._callback(event.src_path)

    def on_modified(self, event):  # pragma: no cover - exercised via integration test
        if not event.is_directory:
            self._callback(event.src_path)

    # ------------------------------------------------------------------
    # Observer control methods
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start watching the directory."""
        self._observer.schedule(self, self._path, recursive=self._recursive)
        self._observer.start()

    def stop(self) -> None:
        """Stop watching the directory."""
        self._observer.stop()

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait until the observer thread finishes."""
        self._observer.join(timeout)
