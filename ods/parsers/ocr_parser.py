"""
OCR图片解析器

支持从图片和扫描PDF中提取文字内容
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Tesseract OCR
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# PDF处理
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from .base_parser import BaseParser, ParsedContent, ParseResult


class OCRParser(BaseParser):
    """OCR图片解析器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
        
        # OCR配置
        ocr_config = config.get("ocr", {})
        self.language = ocr_config.get("language", "chi_sim+eng")  # 中文简体+英文
        self.psm = ocr_config.get("psm", 3)  # Page Segmentation Mode
        self.oem = ocr_config.get("oem", 3)  # OCR Engine Mode
        self.dpi = ocr_config.get("dpi", 300)  # 图片DPI
        self.min_confidence = ocr_config.get("min_confidence", 60)  # 最小置信度
        
        # 图片预处理
        self.preprocess = ocr_config.get("preprocess", True)
        self.resize_factor = ocr_config.get("resize_factor", 2.0)  # 图片放大倍数
        
        if not TESSERACT_AVAILABLE:
            self.logger.error("pytesseract或PIL未安装，无法进行OCR")
        
        # 检查Tesseract是否正确安装
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                self.logger.error(f"Tesseract未正确安装: {e}")
                self.logger.info("请参考文档安装Tesseract OCR引擎")
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        解析图片文件
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        if not TESSERACT_AVAILABLE:
            return self.create_error_result(file_path, "OCR功能不可用：pytesseract或PIL未安装")
        
        if not self.can_parse(file_path):
            return self.create_error_result(file_path, f"无法解析文件: {file_path}")
        
        try:
            # 加载图片
            image = Image.open(file_path)
            
            # 图片预处理
            if self.preprocess:
                image = self._preprocess_image(image)
            
            # 执行OCR
            text, confidence = self._perform_ocr(image)
            
            if not text or confidence < self.min_confidence:
                return self.create_error_result(
                    file_path, 
                    f"OCR提取失败或置信度过低 (置信度: {confidence:.1f}%)"
                )
            
            # 清理文本
            text = self.clean_text(text)
            
            # 提取元数据
            metadata = self._extract_image_metadata(file_path, image, confidence)
            
            content = ParsedContent(
                text=text,
                title=self.extract_title_from_text(text, file_path.name),
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            error_msg = f"OCR解析失败: {str(e)}"
            self.logger.error(f"{error_msg}, 文件: {file_path}")
            return self.create_error_result(file_path, error_msg)
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        图片预处理以提高OCR准确率
        
        Args:
            image: PIL图片对象
            
        Returns:
            Image.Image: 预处理后的图片
        """
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整图片大小（放大）
            if self.resize_factor != 1.0:
                width, height = image.size
                new_width = int(width * self.resize_factor)
                new_height = int(height * self.resize_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为灰度图
            image = image.convert('L')
            
            # 简单的对比度增强
            import numpy as np
            img_array = np.array(image)
            
            # 计算图片的平均亮度
            mean_brightness = np.mean(img_array)
            
            # 如果图片太暗或太亮，进行调整
            if mean_brightness < 100:
                # 图片太暗，增加亮度
                img_array = np.clip(img_array * 1.2 + 20, 0, 255)
            elif mean_brightness > 200:
                # 图片太亮，降低亮度
                img_array = np.clip(img_array * 0.8 - 10, 0, 255)
            
            image = Image.fromarray(img_array.astype(np.uint8))
            
            return image
            
        except Exception as e:
            self.logger.warning(f"图片预处理失败，使用原图: {e}")
            return image
    
    def _perform_ocr(self, image: Image.Image) -> tuple:
        """
        执行OCR识别
        
        Args:
            image: PIL图片对象
            
        Returns:
            tuple: (识别的文本, 置信度)
        """
        # 配置Tesseract参数
        custom_config = f'--oem {self.oem} --psm {self.psm} -l {self.language}'
        
        # 执行OCR
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # 获取置信度信息
        try:
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        except Exception as e:
            self.logger.warning(f"获取OCR置信度失败: {e}")
            avg_confidence = 50  # 默认置信度
        
        return text, avg_confidence
    
    def _extract_image_metadata(self, file_path: Path, image: Image.Image, confidence: float) -> Dict[str, Any]:
        """
        提取图片元数据
        
        Args:
            file_path: 文件路径
            image: PIL图片对象
            confidence: OCR置信度
            
        Returns:
            Dict[str, Any]: 图片元数据
        """
        metadata = {
            'image_width': image.width,
            'image_height': image.height,
            'image_mode': image.mode,
            'image_format': image.format,
            'ocr_confidence': confidence,
            'ocr_language': self.language,
        }
        
        # 提取EXIF信息
        try:
            exif = image._getexif()
            if exif:
                # 提取一些常用的EXIF标签
                exif_tags = {
                    'DateTime': 306,
                    'DateTimeOriginal': 36867,
                    'DateTimeDigitized': 36868,
                    'Make': 271,
                    'Model': 272,
                    'Software': 305,
                    'XResolution': 282,
                    'YResolution': 283,
                }
                
                for tag_name, tag_id in exif_tags.items():
                    if tag_id in exif:
                        metadata[f'exif_{tag_name.lower()}'] = str(exif[tag_id])
                        
        except Exception:
            pass  # EXIF信息不是必需的
        
        return metadata
    
    def parse_pdf_with_ocr(self, file_path: Path) -> ParseResult:
        """
        对扫描PDF进行OCR解析
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            ParseResult: 解析结果
        """
        if not PYMUPDF_AVAILABLE:
            return self.create_error_result(file_path, "PyMuPDF未安装，无法处理PDF图片")
        
        if not TESSERACT_AVAILABLE:
            return self.create_error_result(file_path, "OCR功能不可用")
        
        try:
            doc = fitz.open(str(file_path))
            text_parts = []
            total_confidence = 0
            page_count = 0
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # 将PDF页面转换为图片
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2倍缩放
                img_data = pix.tobytes("png")
                
                # 转换为PIL图片
                from io import BytesIO
                image = Image.open(BytesIO(img_data))
                
                # 执行OCR
                page_text, confidence = self._perform_ocr(image)
                
                if page_text.strip():
                    text_parts.append(f"第{page_num + 1}页:\n{page_text}")
                    total_confidence += confidence
                    page_count += 1
            
            doc.close()
            
            if not text_parts:
                return self.create_error_result(file_path, "PDF中未找到可识别的文本")
            
            text = '\n\n'.join(text_parts)
            text = self.clean_text(text)
            
            avg_confidence = total_confidence / page_count if page_count > 0 else 0
            
            metadata = {
                'pdf_pages': len(doc),
                'ocr_pages': page_count,
                'avg_ocr_confidence': avg_confidence,
                'ocr_language': self.language,
            }
            
            content = ParsedContent(
                text=text,
                title=self.extract_title_from_text(text, file_path.name),
                page_count=len(doc),
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            error_msg = f"PDF OCR解析失败: {str(e)}"
            self.logger.error(f"{error_msg}, 文件: {file_path}")
            return self.create_error_result(file_path, error_msg)
    
    def can_parse(self, file_path: Path) -> bool:
        """
        检查是否可以进行OCR解析
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否可以解析
        """
        if not TESSERACT_AVAILABLE:
            return False
        
        return super().can_parse(file_path)
    
    def is_scanned_pdf(self, file_path: Path) -> bool:
        """
        检查PDF是否为扫描版（主要包含图片）
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 是否为扫描PDF
        """
        if not PYMUPDF_AVAILABLE or file_path.suffix.lower() != '.pdf':
            return False
        
        try:
            doc = fitz.open(str(file_path))
            
            # 检查前几页
            check_pages = min(3, len(doc))
            text_pages = 0
            
            for page_num in range(check_pages):
                page = doc.load_page(page_num)
                text = page.get_text().strip()
                
                # 如果页面有足够的文本，认为不是扫描版
                if len(text) > 100:
                    text_pages += 1
            
            doc.close()
            
            # 如果大部分页面都没有文本，可能是扫描版
            return text_pages / check_pages < 0.5
            
        except Exception:
            return False
