"""
主要文档解析器

统一的文档解析入口，根据文件类型自动选择合适的解析器
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .base_parser import ParseResult
from .pdf_parser import PDFParser
from .office_parser import OfficeParser
from .text_parser import TextParser
from .ocr_parser import OCRParser


class DocumentParser:
    """
    主要文档解析器

    负责根据文件类型自动选择合适的解析器进行文档内容提取
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化文档解析器

        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化各种解析器
        self.parsers = {}
        self._init_parsers()

        # 解析器优先级配置
        self.parser_priority = config.get("parser", {}).get(
            "priority", ["pdf", "office", "text", "ocr"]
        )

        # 是否启用OCR作为后备方案
        self.ocr_fallback = config.get("parser", {}).get("ocr_fallback", True)

        # 支持的文件扩展名
        self.supported_extensions = self._get_supported_extensions()

        self.logger.info(
            f"文档解析器初始化完成，支持的文件类型: {self.supported_extensions}"
        )

    def _init_parsers(self) -> None:
        """初始化各种解析器"""
        try:
            self.parsers["pdf"] = PDFParser(self.config)
            self.logger.info("PDF解析器初始化成功")
        except Exception as e:
            self.logger.warning(f"PDF解析器初始化失败: {e}")

        try:
            self.parsers["office"] = OfficeParser(self.config)
            self.logger.info("Office解析器初始化成功")
        except Exception as e:
            self.logger.warning(f"Office解析器初始化失败: {e}")

        try:
            self.parsers["text"] = TextParser(self.config)
            self.logger.info("文本解析器初始化成功")
        except Exception as e:
            self.logger.warning(f"文本解析器初始化失败: {e}")

        try:
            self.parsers["ocr"] = OCRParser(self.config)
            self.logger.info("OCR解析器初始化成功")
        except Exception as e:
            self.logger.warning(f"OCR解析器初始化失败: {e}")

    def _get_supported_extensions(self) -> List[str]:
        """获取所有支持的文件扩展名"""
        extensions = set()
        for parser in self.parsers.values():
            extensions.update(parser.supported_extensions)
        return sorted(list(extensions))

    def parse(self, file_path: str | Path) -> ParseResult:
        """
        解析文档

        Args:
            file_path: 文件路径（字符串或Path对象）

        Returns:
            ParseResult: 解析结果
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return ParseResult(
                success=False,
                error=f"文件不存在: {file_path}",
                file_path=str(file_path),
            )

        if not file_path.is_file():
            return ParseResult(
                success=False,
                error=f"路径不是文件: {file_path}",
                file_path=str(file_path),
            )

        extension = file_path.suffix.lower()

        # 检查文件类型是否支持
        if extension not in self.supported_extensions:
            return ParseResult(
                success=False,
                error=f"不支持的文件类型: {extension}",
                file_path=str(file_path),
            )

        self.logger.info(f"开始解析文件: {file_path}")

        # 按优先级尝试解析器
        result = self._try_parsers(file_path)

        # 如果主要解析器都失败，且启用了OCR后备方案
        if not result.success and self.ocr_fallback:
            result = self._try_ocr_fallback(file_path, result.error)

        # 记录解析结果
        if result.success:
            word_count = len(result.text.split()) if result.text else 0
            self.logger.info(
                f"文件解析成功: {file_path}, 字数: {word_count}, 解析器: {result.parser_type}"
            )
        else:
            self.logger.error(f"文件解析失败: {file_path}, 错误: {result.error}")

        return result

    def _try_parsers(self, file_path: Path) -> ParseResult:
        """
        按优先级尝试解析器

        Args:
            file_path: 文件路径

        Returns:
            ParseResult: 解析结果
        """
        extension = file_path.suffix.lower()
        errors = []

        # 根据文件扩展名确定可能的解析器
        possible_parsers = self._get_possible_parsers(extension)

        # 按配置的优先级排序
        sorted_parsers = []
        for priority in self.parser_priority:
            if priority in possible_parsers:
                sorted_parsers.append(priority)

        # 添加其他可能的解析器
        for parser_name in possible_parsers:
            if parser_name not in sorted_parsers:
                sorted_parsers.append(parser_name)

        # 逐个尝试解析器
        for parser_name in sorted_parsers:
            if parser_name not in self.parsers:
                continue

            parser = self.parsers[parser_name]

            if not parser.can_parse(file_path):
                continue

            try:
                result = parser.parse(file_path)
                if result.success:
                    return result
                else:
                    errors.append(f"{parser_name}: {result.error}")
            except Exception as e:
                error_msg = f"{parser_name}解析器异常: {str(e)}"
                self.logger.warning(error_msg)
                errors.append(error_msg)

        # 所有解析器都失败
        return ParseResult(
            success=False,
            error=f"所有解析器都失败: {'; '.join(errors)}",
            file_path=str(file_path),
        )

    def _get_possible_parsers(self, extension: str) -> List[str]:
        """
        根据文件扩展名获取可能的解析器列表

        Args:
            extension: 文件扩展名

        Returns:
            List[str]: 可能的解析器名称列表
        """
        possible_parsers = []

        # PDF文件
        if extension == ".pdf":
            possible_parsers.extend(["pdf", "ocr"])  # PDF可能需要OCR

        # Office文件
        elif extension in [".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"]:
            possible_parsers.append("office")

        # 文本文件
        elif extension in [
            ".txt",
            ".md",
            ".markdown",
            ".rst",
            ".csv",
            ".json",
            ".xml",
            ".html",
            ".htm",
            ".py",
            ".js",
            ".css",
            ".yaml",
            ".yml",
            ".ini",
            ".cfg",
            ".conf",
            ".log",
        ]:
            possible_parsers.append("text")

        # 图片文件
        elif extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"]:
            possible_parsers.append("ocr")

        return possible_parsers

    def _try_ocr_fallback(self, file_path: Path, original_error: str) -> ParseResult:
        """
        尝试OCR后备方案

        Args:
            file_path: 文件路径
            original_error: 原始错误信息

        Returns:
            ParseResult: OCR解析结果
        """
        if "ocr" not in self.parsers:
            return ParseResult(
                success=False,
                error=f"OCR后备方案不可用。原始错误: {original_error}",
                file_path=str(file_path),
            )

        ocr_parser = self.parsers["ocr"]
        extension = file_path.suffix.lower()

        try:
            # 对于PDF文件，尝试OCR解析
            if extension == ".pdf":
                if hasattr(ocr_parser, "is_scanned_pdf") and ocr_parser.is_scanned_pdf(
                    file_path
                ):
                    self.logger.info(f"检测到扫描PDF，尝试OCR解析: {file_path}")
                    result = ocr_parser.parse_pdf_with_ocr(file_path)
                    if result.success:
                        return result

            # 对于图片文件，直接使用OCR
            elif extension in ocr_parser.supported_extensions:
                self.logger.info(f"尝试OCR后备方案: {file_path}")
                result = ocr_parser.parse(file_path)
                if result.success:
                    return result

        except Exception as e:
            self.logger.warning(f"OCR后备方案失败: {e}")

        return ParseResult(
            success=False,
            error=f"OCR后备方案也失败。原始错误: {original_error}",
            file_path=str(file_path),
        )

    def can_parse(self, file_path: str | Path) -> bool:
        """
        检查是否可以解析该文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否可以解析
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists() or not file_path.is_file():
            return False

        extension = file_path.suffix.lower()
        return extension in self.supported_extensions

    def get_parser_info(self) -> Dict[str, Any]:
        """
        获取解析器信息

        Returns:
            Dict[str, Any]: 解析器信息
        """
        info = {
            "available_parsers": list(self.parsers.keys()),
            "supported_extensions": self.supported_extensions,
            "parser_priority": self.parser_priority,
            "ocr_fallback": self.ocr_fallback,
        }

        # 各解析器支持的扩展名
        parser_extensions = {}
        for name, parser in self.parsers.items():
            parser_extensions[name] = parser.supported_extensions
        info["parser_extensions"] = parser_extensions

        return info

    def parse_batch(self, file_paths: List[str | Path]) -> List[ParseResult]:
        """
        批量解析文件

        Args:
            file_paths: 文件路径列表

        Returns:
            List[ParseResult]: 解析结果列表
        """
        results = []

        for file_path in file_paths:
            try:
                result = self.parse(file_path)
                results.append(result)
            except Exception as e:
                error_result = ParseResult(
                    success=False,
                    error=f"批量解析异常: {str(e)}",
                    file_path=str(file_path),
                )
                results.append(error_result)

        # 记录批量解析统计
        success_count = sum(1 for r in results if r.success)
        self.logger.info(
            f"批量解析完成: 总计 {len(results)}, 成功 {success_count}, 失败 {len(results) - success_count}"
        )

        return results
