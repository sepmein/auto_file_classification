"""
核心功能模块

包含系统的主要组件：工作流引擎、配置管理、数据库操作等
"""

try:
    from .workflow import DocumentClassificationWorkflow
except Exception:  # pragma: no cover
    DocumentClassificationWorkflow = None

from .config import Config
from .database import Database
from .watcher import DirectoryWatcher

__all__ = [
    "DocumentClassificationWorkflow",
    "Config",
    "Database",
    "DirectoryWatcher",
]
