import time
from pathlib import Path
from unittest.mock import Mock

from ods.core.watcher import DirectoryWatcher


def test_directory_watcher_triggers_callback(tmp_path):
    """DirectoryWatcher should invoke callback when a file is created."""
    callback = Mock()
    watcher = DirectoryWatcher(str(tmp_path), callback)

    try:
        watcher.start()
        # Create a new file inside the watched directory
        test_file = tmp_path / "example.txt"
        test_file.write_text("hello")

        # Give the watcher a moment to process the event
        time.sleep(1)
    finally:
        watcher.stop()
        watcher.join()

    # Ensure callback was invoked with the created file path
    assert any(str(test_file) == call.args[0] for call in callback.call_args_list)
