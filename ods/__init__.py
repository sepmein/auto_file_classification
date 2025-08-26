"""
基于LLM和向量数据库的自动文档分类系统

一个智能的文档自动分类和整理系统，基于LLM（大型语言模型）和向量数据库技术，
帮助用户自动整理OneDrive等云盘中的文档。
"""

__version__ = "0.1.0"
__author__ = "Auto File Classification Team"
__email__ = "team@example.com"

try:
    from .core.workflow import DocumentClassificationWorkflow
except Exception:  # pragma: no cover - 依赖未安装时提供降级导入
    DocumentClassificationWorkflow = None

from .core.config import Config
from .core.database import Database

__all__ = [
    "DocumentClassificationWorkflow",
    "Config",
    "Database",
]
