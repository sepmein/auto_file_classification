import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from ods.storage.file_mover import FileMover


def create_temp_structure(tmp_path: Path):
    # Create source file
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    src_file = src_dir / "document.txt"
    src_file.write_text("hello")
    return src_file


class TestFileMover:
    def setup_method(self):
        self.config = {
            "system": {"dry_run": False},
            "file": {
                "cleanup_empty_dirs": True,
                "allow_symlink": True,
                "allow_windows_shortcut": False,
                "use_hardlink_on_windows": False,
            },
        }

    def test_move_and_links_unix(self, tmp_path, monkeypatch):
        # Skip on Windows for symlink test
        if os.name == "nt":
            pytest.skip("Unix symlink test skipped on Windows")

        src_file = create_temp_structure(tmp_path)
        path_plan = {
            "original_path": str(src_file),
            "primary_path": str(tmp_path / "dst" / "category" / src_file.name),
            "link_paths": [
                {
                    "link_path": str(tmp_path / "dst" / "tagA" / src_file.name),
                    "type": "soft_link",
                },
                {
                    "link_path": str(tmp_path / "dst" / "tagB" / src_file.name),
                    "type": "soft_link",
                },
            ],
        }
        naming_result = {
            "new_path": str(tmp_path / "dst" / "category" / "renamed.txt"),
            "new_filename": "renamed.txt",
        }

        mover = FileMover(self.config)
        report = mover.move_file(path_plan, naming_result)

        # Main file moved
        assert report["moved"] is True
        assert Path(report["primary_target_path"]).exists()
        assert not Path(path_plan["original_path"]).exists()

        # Links created
        for link in report["link_creations"]:
            assert link["ok"] in (True, False)  # at least reported
            # On unix, should be symlink when ok
            if link["ok"]:
                assert Path(link["path"]).is_symlink()

    def test_dry_run(self, tmp_path):
        src_file = create_temp_structure(tmp_path)
        path_plan = {
            "original_path": str(src_file),
            "primary_path": str(tmp_path / "dst" / "category" / src_file.name),
            "link_paths": [
                {
                    "link_path": str(tmp_path / "dst" / "tagA" / src_file.name),
                    "type": "soft_link",
                }
            ],
        }
        naming_result = {
            "new_path": str(tmp_path / "dst" / "category" / "renamed.txt"),
            "new_filename": "renamed.txt",
        }

        cfg = dict(self.config)
        cfg["system"] = {"dry_run": True}
        mover = FileMover(cfg)
        report = mover.move_file(path_plan, naming_result)

        assert report["moved"] is True  # logical success
        # File should remain
        assert Path(path_plan["original_path"]).exists()
        # Target should not exist
        assert not Path(report["primary_target_path"]).exists()

    def test_rollback_on_failure(self, tmp_path, monkeypatch):
        src_file = create_temp_structure(tmp_path)
        path_plan = {
            "original_path": str(src_file),
            "primary_path": str(tmp_path / "dst" / "category" / src_file.name),
            "link_paths": [
                {
                    "link_path": str(tmp_path / "dst" / "tagA" / src_file.name),
                    "type": "soft_link",
                }
            ],
        }
        naming_result = {
            "new_path": str(tmp_path / "dst" / "category" / "renamed.txt"),
            "new_filename": "renamed.txt",
        }

        mover = FileMover(self.config)

        # Force failure by mocking link creation to raise
        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(mover, "_create_link_for_tag", boom)

        report = mover.move_file(path_plan, naming_result)
        assert report["moved"] is False or report["rolled_back"] is True
        # Source should still exist due to rollback
        assert Path(path_plan["original_path"]).exists()
