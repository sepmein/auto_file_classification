"""
基础文档解析器

定义文档解析器的抽象接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass
import logging
import mimetypes
import os


@dataclass
class ParsedContent:
    """解析后的文档内容"""

    text: str  # 提取的文本内容
    title: Optional[str] = None  # 文档标题
    author: Optional[str] = None  # 作者
    creation_date: Optional[str] = None  # 创建日期
    modification_date: Optional[str] = None  # 修改日期
    page_count: Optional[int] = None  # 页数
    word_count: Optional[int] = None  # 字数
    metadata: Dict[str, Any] = None  # 其他元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.word_count is None and self.text:
            self.word_count = len(self.text.split())


@dataclass
class ParseResult:
    """解析结果"""

    success: bool
    content: Optional[ParsedContent] = None
    error: Optional[str] = None
    file_path: Optional[str] = None
    parser_type: Optional[str] = None

    @property
    def text(self) -> str:
        """获取文本内容"""
        return self.content.text if self.content else ""

    @property
    def summary(self) -> str:
        """获取文本摘要（前500字符）"""
        if not self.content or not self.content.text:
            return ""
        text = self.content.text.strip()
        return text[:500] + "..." if len(text) > 500 else text


class BaseParser(ABC):
    """文档解析器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.supported_extensions: List[str] = []
        self.max_file_size = config.get("file", {}).get(
            "max_file_size", 100 * 1024 * 1024
        )  # 100MB

    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> ParseResult:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            ParseResult: 解析结果
        """
        pass

    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """
        检查是否可以解析该文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否可以解析
        """
        # 确保是Path对象
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists() or not file_path.is_file():
            return False

        # 检查文件扩展名
        extension = file_path.suffix.lower()
        if extension not in self.supported_extensions:
            return False

        # 检查文件大小
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                self.logger.warning(
                    f"文件过大，跳过解析: {file_path} ({file_size} bytes)"
                )
                return False
        except OSError as e:
            self.logger.error(f"无法获取文件信息: {file_path}, 错误: {e}")
            return False

        return True

    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        获取文件基础元数据

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 文件元数据
        """
        try:
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))

            return {
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "file_extension": file_path.suffix.lower(),
                "mime_type": mime_type,
                "creation_time": stat.st_ctime,
                "modification_time": stat.st_mtime,
                "access_time": stat.st_atime,
            }
        except Exception as e:
            self.logger.error(f"获取文件元数据失败: {file_path}, 错误: {e}")
            return {}

    def clean_text(self, text: str) -> str:
        """
        清理提取的文本

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""

        # 替换多个连续的空白字符为单个空格
        import re

        text = re.sub(r"\s+", " ", text)

        # 移除首尾空白
        text = text.strip()

        return text

    def extract_title_from_text(self, text: str, file_name: str) -> Optional[str]:
        """
        从文本中提取标题

        Args:
            text: 文档文本
            file_name: 文件名

        Returns:
            Optional[str]: 提取的标题
        """
        if not text:
            return None

        # 尝试从文本第一行提取标题
        lines = text.split("\n")
        if lines:
            first_line = lines[0].strip()
            # 如果第一行不为空且长度合适，作为标题
            if first_line and 5 <= len(first_line) <= 100:
                return first_line

        # 如果无法从文本提取，使用文件名（去掉扩展名）
        title = Path(file_name).stem
        return title if title else None

    def create_error_result(self, file_path: Path, error: str) -> ParseResult:
        """
        创建错误结果

        Args:
            file_path: 文件路径
            error: 错误信息

        Returns:
            ParseResult: 错误结果
        """
        return ParseResult(
            success=False,
            error=error,
            file_path=str(file_path),
            parser_type=self.__class__.__name__,
        )

    def create_success_result(
        self, file_path: Path, content: ParsedContent
    ) -> ParseResult:
        """
        创建成功结果

        Args:
            file_path: 文件路径
            content: 解析的内容

        Returns:
            ParseResult: 成功结果
        """
        return ParseResult(
            success=True,
            content=content,
            file_path=str(file_path),
            parser_type=self.__class__.__name__,
        )
