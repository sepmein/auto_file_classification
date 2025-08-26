"""
文档解析器模块

负责解析各种类型的文档，提取文本内容用于后续分类
"""

from .document_parser import DocumentParser
from .base_parser import BaseParser
from .pdf_parser import PDFParser
from .office_parser import OfficeParser
from .text_parser import TextParser
from .ocr_parser import OCRParser

__all__ = [
    "DocumentParser",
    "BaseParser",
    "PDFParser",
    "OfficeParser",
    "TextParser",
    "OCRParser",
]
