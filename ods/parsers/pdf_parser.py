"""
PDF文档解析器

使用pdfminer.six提取PDF文档的文本内容
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

try:
    from pdfminer.high_level import extract_text, extract_pages
    from pdfminer.layout import LTTextContainer, LTChar, LTFigure
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LAParams

    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

from .base_parser import BaseParser, ParsedContent, ParseResult


class PDFParser(BaseParser):
    """PDF文档解析器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supported_extensions = [".pdf"]
        self.max_pages = config.get("pdf", {}).get("max_pages", 100)  # 最大解析页数
        self.extract_metadata = config.get("pdf", {}).get("extract_metadata", True)

        if not PDFMINER_AVAILABLE:
            self.logger.error("pdfminer.six未安装，无法解析PDF文件")

    def parse(self, file_path: Path) -> ParseResult:
        """
        解析PDF文档

        Args:
            file_path: PDF文件路径

        Returns:
            ParseResult: 解析结果
        """
        if not PDFMINER_AVAILABLE:
            return self.create_error_result(file_path, "pdfminer.six未安装")

        if not self.can_parse(file_path):
            return self.create_error_result(file_path, f"无法解析文件: {file_path}")

        try:
            # 检查文件是否损坏
            if not self._is_valid_pdf(file_path):
                return self.create_error_result(file_path, "PDF文件损坏或格式无效")

            # 提取文本内容
            text = self._extract_text(file_path)

            if not text or len(text.strip()) == 0:
                return self.create_error_result(file_path, "PDF文档为空或无法提取文本")

            # 清理文本
            text = self.clean_text(text)

            # 提取元数据
            metadata = (
                self._extract_pdf_metadata(file_path) if self.extract_metadata else {}
            )

            # 创建解析内容
            content = ParsedContent(
                text=text,
                title=self._extract_title(text, file_path.name, metadata),
                author=metadata.get("author"),
                creation_date=metadata.get("creation_date"),
                modification_date=metadata.get("modification_date"),
                page_count=metadata.get("page_count"),
                metadata={**self.get_file_metadata(file_path), **metadata},
            )

            return self.create_success_result(file_path, content)

        except Exception as e:
            error_msg = f"PDF解析失败: {str(e)}"
            self.logger.error(f"{error_msg}, 文件: {file_path}")
            return self.create_error_result(file_path, error_msg)

    def _is_valid_pdf(self, file_path: Path) -> bool:
        """检查PDF文件是否有效"""
        try:
            with open(file_path, "rb") as file:
                # 检查PDF文件头
                header = file.read(8)
                if header.startswith(b"%PDF"):
                    return True

                # 尝试解析PDF结构
                file.seek(0)
                from pdfminer.pdfparser import PDFParser as PDFParserLow
                from pdfminer.pdfdocument import PDFDocument

                parser = PDFParserLow(file)
                document = PDFDocument(parser)
                return document.info is not None

        except Exception:
            return False

        return False

    def _extract_text(self, file_path: Path) -> str:
        """
        提取PDF文本内容

        Args:
            file_path: PDF文件路径

        Returns:
            str: 提取的文本
        """
        try:
            # 使用高级API提取文本
            text = extract_text(
                str(file_path), maxpages=self.max_pages, password="", caching=True
            )
            return text
        except Exception as e:
            # 如果高级API失败，尝试使用低级API
            self.logger.warning(f"高级API提取失败，尝试低级API: {e}")
            return self._extract_text_low_level(file_path)

    def _extract_text_low_level(self, file_path: Path) -> str:
        """
        使用低级API提取PDF文本

        Args:
            file_path: PDF文件路径

        Returns:
            str: 提取的文本
        """
        text_parts = []

        try:
            with open(file_path, "rb") as file:
                resource_manager = PDFResourceManager()
                laparams = LAParams(char_margin=2.0, line_margin=0.5, word_margin=0.1)
                device = PDFPageAggregator(resource_manager, laparams=laparams)
                interpreter = PDFPageInterpreter(resource_manager, device)

                page_count = 0
                for page in PDFPage.get_pages(file, caching=True):
                    if page_count >= self.max_pages:
                        break

                    interpreter.process_page(page)
                    layout = device.get_result()

                    for element in layout:
                        if isinstance(element, LTTextContainer):
                            text_parts.append(element.get_text())

                    page_count += 1

            return "\n".join(text_parts)

        except Exception as e:
            self.logger.error(f"低级API提取也失败: {e}")
            raise

    def _extract_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        提取PDF元数据

        Args:
            file_path: PDF文件路径

        Returns:
            Dict[str, Any]: PDF元数据
        """
        metadata = {}

        try:
            from pdfminer.pdfparser import PDFParser as PDFParserLow
            from pdfminer.pdfdocument import PDFDocument

            with open(file_path, "rb") as file:
                parser = PDFParserLow(file)
                document = PDFDocument(parser)

                if document.info:
                    info = document.info[0]

                    # 提取标准元数据字段
                    if "Title" in info:
                        metadata["title"] = self._decode_pdf_string(info["Title"])
                    if "Author" in info:
                        metadata["author"] = self._decode_pdf_string(info["Author"])
                    if "Subject" in info:
                        metadata["subject"] = self._decode_pdf_string(info["Subject"])
                    if "Creator" in info:
                        metadata["creator"] = self._decode_pdf_string(info["Creator"])
                    if "Producer" in info:
                        metadata["producer"] = self._decode_pdf_string(info["Producer"])
                    if "CreationDate" in info:
                        metadata["creation_date"] = str(info["CreationDate"])
                    if "ModDate" in info:
                        metadata["modification_date"] = str(info["ModDate"])

                # 计算页数
                metadata["page_count"] = sum(1 for _ in PDFPage.create_pages(document))

        except Exception as e:
            self.logger.warning(f"提取PDF元数据失败: {e}")

        return metadata

    def _decode_pdf_string(self, pdf_string) -> str:
        """
        解码PDF字符串

        Args:
            pdf_string: PDF字符串对象

        Returns:
            str: 解码后的字符串
        """
        try:
            if hasattr(pdf_string, "resolve"):
                pdf_string = pdf_string.resolve()

            if isinstance(pdf_string, bytes):
                # 尝试不同的编码
                for encoding in ["utf-8", "utf-16", "latin1", "cp1252"]:
                    try:
                        return pdf_string.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 如果所有编码都失败，使用错误处理
                return pdf_string.decode("utf-8", errors="ignore")

            return str(pdf_string)

        except Exception:
            return str(pdf_string)

    def _extract_title(
        self, text: str, file_name: str, metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        提取文档标题

        Args:
            text: 文档文本
            file_name: 文件名
            metadata: PDF元数据

        Returns:
            Optional[str]: 提取的标题
        """
        # 优先使用PDF元数据中的标题
        if metadata.get("title"):
            title = metadata["title"].strip()
            if title and title.lower() not in ["untitled", "document"]:
                return title

        # 其次从文本内容提取
        text_title = self.extract_title_from_text(text, file_name)
        if text_title:
            return text_title

        # 最后使用文件名
        return Path(file_name).stem

    def can_parse(self, file_path: Path) -> bool:
        """
        检查是否可以解析PDF文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否可以解析
        """
        if not PDFMINER_AVAILABLE:
            return False

        return super().can_parse(file_path)
