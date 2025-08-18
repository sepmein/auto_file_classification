"""
Office文档解析器

支持Word、PowerPoint、Excel等Office文档的文本提取
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Word文档解析
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# PowerPoint文档解析
try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

# Excel文档解析
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# 备用方案：textract
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

from .base_parser import BaseParser, ParsedContent, ParseResult


class OfficeParser(BaseParser):
    """Office文档解析器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supported_extensions = []
        
        # 根据可用库设置支持的扩展名
        if DOCX_AVAILABLE:
            self.supported_extensions.extend(['.docx', '.doc'])
        if PPTX_AVAILABLE:
            self.supported_extensions.extend(['.pptx', '.ppt'])
        if OPENPYXL_AVAILABLE:
            self.supported_extensions.extend(['.xlsx', '.xls'])
        
        # 如果有textract作为备用，支持更多格式
        if TEXTRACT_AVAILABLE:
            self.supported_extensions.extend(['.doc', '.ppt', '.xls'])
        
        self.extract_metadata = config.get("office", {}).get("extract_metadata", True)
        self.max_slides = config.get("office", {}).get("max_slides", 50)  # PPT最大幻灯片数
        self.max_sheets = config.get("office", {}).get("max_sheets", 10)  # Excel最大工作表数
        
        if not any([DOCX_AVAILABLE, PPTX_AVAILABLE, OPENPYXL_AVAILABLE, TEXTRACT_AVAILABLE]):
            self.logger.error("未安装Office文档解析库，无法解析Office文件")
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        解析Office文档
        
        Args:
            file_path: Office文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        if not self.can_parse(file_path):
            return self.create_error_result(file_path, f"无法解析文件: {file_path}")
        
        extension = file_path.suffix.lower()
        
        try:
            # 根据文件类型选择解析方法
            if extension in ['.docx', '.doc']:
                return self._parse_word(file_path)
            elif extension in ['.pptx', '.ppt']:
                return self._parse_powerpoint(file_path)
            elif extension in ['.xlsx', '.xls']:
                return self._parse_excel(file_path)
            else:
                return self.create_error_result(file_path, f"不支持的文件类型: {extension}")
        
        except Exception as e:
            error_msg = f"Office文档解析失败: {str(e)}"
            self.logger.error(f"{error_msg}, 文件: {file_path}")
            return self.create_error_result(file_path, error_msg)
    
    def _parse_word(self, file_path: Path) -> ParseResult:
        """
        解析Word文档
        
        Args:
            file_path: Word文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        text_parts = []
        metadata = {}
        
        try:
            if file_path.suffix.lower() == '.docx' and DOCX_AVAILABLE:
                # 使用python-docx解析.docx文件
                doc = DocxDocument(str(file_path))
                
                # 提取文本
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text)
                
                # 提取元数据
                if self.extract_metadata and hasattr(doc, 'core_properties'):
                    props = doc.core_properties
                    metadata.update({
                        'title': props.title,
                        'author': props.author,
                        'subject': props.subject,
                        'keywords': props.keywords,
                        'creation_date': str(props.created) if props.created else None,
                        'modification_date': str(props.modified) if props.modified else None,
                        'last_modified_by': props.last_modified_by,
                        'revision': props.revision,
                    })
            
            elif TEXTRACT_AVAILABLE:
                # 使用textract作为备用方案
                text = textract.process(str(file_path)).decode('utf-8')
                text_parts = [text]
            
            else:
                raise Exception("没有可用的Word解析库")
            
            if not text_parts:
                return self.create_error_result(file_path, "Word文档为空或无法提取文本")
            
            text = '\n'.join(text_parts)
            text = self.clean_text(text)
            
            content = ParsedContent(
                text=text,
                title=self._extract_title_from_metadata_or_text(metadata, text, file_path.name),
                author=metadata.get('author'),
                creation_date=metadata.get('creation_date'),
                modification_date=metadata.get('modification_date'),
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            raise Exception(f"Word文档解析失败: {e}")
    
    def _parse_powerpoint(self, file_path: Path) -> ParseResult:
        """
        解析PowerPoint文档
        
        Args:
            file_path: PowerPoint文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        text_parts = []
        metadata = {}
        
        try:
            if file_path.suffix.lower() == '.pptx' and PPTX_AVAILABLE:
                # 使用python-pptx解析.pptx文件
                prs = Presentation(str(file_path))
                
                # 提取文本
                slide_count = 0
                for slide in prs.slides:
                    if slide_count >= self.max_slides:
                        break
                    
                    slide_texts = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_texts.append(shape.text)
                    
                    if slide_texts:
                        text_parts.append(f"幻灯片 {slide_count + 1}:\n" + '\n'.join(slide_texts))
                    
                    slide_count += 1
                
                # 提取元数据
                if self.extract_metadata and hasattr(prs, 'core_properties'):
                    props = prs.core_properties
                    metadata.update({
                        'title': props.title,
                        'author': props.author,
                        'subject': props.subject,
                        'keywords': props.keywords,
                        'creation_date': str(props.created) if props.created else None,
                        'modification_date': str(props.modified) if props.modified else None,
                        'last_modified_by': props.last_modified_by,
                        'slide_count': len(prs.slides),
                    })
            
            elif TEXTRACT_AVAILABLE:
                # 使用textract作为备用方案
                text = textract.process(str(file_path)).decode('utf-8')
                text_parts = [text]
            
            else:
                raise Exception("没有可用的PowerPoint解析库")
            
            if not text_parts:
                return self.create_error_result(file_path, "PowerPoint文档为空或无法提取文本")
            
            text = '\n\n'.join(text_parts)
            text = self.clean_text(text)
            
            content = ParsedContent(
                text=text,
                title=self._extract_title_from_metadata_or_text(metadata, text, file_path.name),
                author=metadata.get('author'),
                creation_date=metadata.get('creation_date'),
                modification_date=metadata.get('modification_date'),
                page_count=metadata.get('slide_count'),
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            raise Exception(f"PowerPoint文档解析失败: {e}")
    
    def _parse_excel(self, file_path: Path) -> ParseResult:
        """
        解析Excel文档
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        text_parts = []
        metadata = {}
        
        try:
            if file_path.suffix.lower() == '.xlsx' and OPENPYXL_AVAILABLE:
                # 使用openpyxl解析.xlsx文件
                workbook = openpyxl.load_workbook(str(file_path), read_only=True)
                
                sheet_count = 0
                for sheet_name in workbook.sheetnames:
                    if sheet_count >= self.max_sheets:
                        break
                    
                    worksheet = workbook[sheet_name]
                    sheet_texts = [f"工作表: {sheet_name}"]
                    
                    # 提取前几行作为表头和数据样本
                    row_count = 0
                    for row in worksheet.iter_rows(values_only=True):
                        if row_count >= 20:  # 限制每个工作表最多读取20行
                            break
                        
                        # 过滤空值，组合成文本
                        row_values = [str(cell) for cell in row if cell is not None]
                        if row_values:
                            sheet_texts.append(' | '.join(row_values))
                        
                        row_count += 1
                    
                    if len(sheet_texts) > 1:  # 除了表名外还有内容
                        text_parts.append('\n'.join(sheet_texts))
                    
                    sheet_count += 1
                
                workbook.close()
                
                # Excel元数据相对简单
                metadata.update({
                    'sheet_count': len(workbook.sheetnames),
                    'sheet_names': workbook.sheetnames[:self.max_sheets],
                })
            
            elif TEXTRACT_AVAILABLE:
                # 使用textract作为备用方案
                text = textract.process(str(file_path)).decode('utf-8')
                text_parts = [text]
            
            else:
                raise Exception("没有可用的Excel解析库")
            
            if not text_parts:
                return self.create_error_result(file_path, "Excel文档为空或无法提取文本")
            
            text = '\n\n'.join(text_parts)
            text = self.clean_text(text)
            
            content = ParsedContent(
                text=text,
                title=self._extract_title_from_metadata_or_text(metadata, text, file_path.name),
                creation_date=metadata.get('creation_date'),
                modification_date=metadata.get('modification_date'),
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            raise Exception(f"Excel文档解析失败: {e}")
    
    def _extract_title_from_metadata_or_text(self, metadata: Dict[str, Any], text: str, file_name: str) -> Optional[str]:
        """
        从元数据或文本中提取标题
        
        Args:
            metadata: 文档元数据
            text: 文档文本
            file_name: 文件名
            
        Returns:
            Optional[str]: 提取的标题
        """
        # 优先使用元数据中的标题
        if metadata.get('title'):
            title = metadata['title'].strip()
            if title and title.lower() not in ['document', 'presentation', 'workbook']:
                return title
        
        # 其次从文本内容提取
        text_title = self.extract_title_from_text(text, file_name)
        if text_title:
            return text_title
        
        # 最后使用文件名
        return Path(file_name).stem
    
    def can_parse(self, file_path: Path) -> bool:
        """
        检查是否可以解析Office文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否可以解析
        """
        if not super().can_parse(file_path):
            return False
        
        extension = file_path.suffix.lower()
        
        # 检查特定格式的支持
        if extension in ['.docx'] and not DOCX_AVAILABLE:
            return TEXTRACT_AVAILABLE
        elif extension in ['.pptx'] and not PPTX_AVAILABLE:
            return TEXTRACT_AVAILABLE
        elif extension in ['.xlsx'] and not OPENPYXL_AVAILABLE:
            return TEXTRACT_AVAILABLE
        elif extension in ['.doc', '.ppt', '.xls']:
            return TEXTRACT_AVAILABLE
        
        return True
