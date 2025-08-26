"""Database module tests.

These tests focus on the audit logging and rollback functionality
implemented in :class:`ods.core.database.Database`.  The project plan
mentions an audit and rollback mechanism so we ensure the feature works
as expected.
"""

from datetime import datetime
from pathlib import Path
import shutil

from ods.core.database import Database


def _create_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("data", encoding="utf-8")


def test_operation_rollback(tmp_path):
    """A logged move can be undone using ``rollback_operation``."""

    db = Database({"database": {"path": str(tmp_path / "db.sqlite")}})

    src = tmp_path / "a.txt"
    dst = tmp_path / "sub" / "a.txt"

    _create_file(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dst)

    file_info = {
        "file_name": dst.name,
        "file_size": dst.stat().st_size,
        "file_extension": dst.suffix,
        "creation_time": datetime.now(),
        "modification_time": datetime.now(),
    }
    file_id = db.insert_file(str(dst), file_info)
    op_id = db.log_operation(
        file_id,
        {
            "operation_type": "move",
            "old_path": str(src),
            "new_path": str(dst),
            "old_name": src.name,
            "new_name": dst.name,
            "tags": [],
            "success": True,
        },
    )

    assert dst.exists()

    assert db.rollback_operation(op_id) is True
    assert src.exists()
    assert not dst.exists()

    # File record updated to original path
    assert db.get_file_by_path(str(src)) is not None

    # Second log entry should be the rollback record
    logs = db.get_operation_logs(file_id)
    assert any(log["operation_type"] == "rollback" for log in logs)


def test_rollback_nonexistent_operation(tmp_path):
    """Rolling back a missing operation returns ``False``."""

    db = Database({"database": {"path": str(tmp_path / "db.sqlite")}})
    assert db.rollback_operation(9999) is False

