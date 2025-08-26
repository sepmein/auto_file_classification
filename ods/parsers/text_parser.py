"""
文本文件解析器

支持各种纯文本格式文件的解析
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
import chardet

from .base_parser import BaseParser, ParsedContent, ParseResult


class TextParser(BaseParser):
    """文本文件解析器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supported_extensions = [
            '.txt', '.md', '.markdown', '.rst', '.csv', '.json', '.xml', '.html', '.htm',
            '.py', '.js', '.css', '.yaml', '.yml', '.ini', '.cfg', '.conf', '.log'
        ]
        self.max_text_length = config.get("text", {}).get("max_length", 1000000)  # 1MB文本
        self.encoding_detection = config.get("text", {}).get("encoding_detection", True)
        self.default_encoding = config.get("text", {}).get("default_encoding", "utf-8")
    
    def parse(self, file_path: Path | str) -> ParseResult:
        """解析文本文件.

        测试用例会以 ``str`` 形式传入路径，因此在这里允许
        ``str``/``Path`` 两种类型并在内部统一转换。这使得解析器
        更易于使用并避免由于类型不匹配导致的 ``AttributeError``。

        Args:
            file_path: 文本文件路径

        Returns:
            ParseResult: 解析结果
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not self.can_parse(file_path):
            return self.create_error_result(file_path, f"无法解析文件: {file_path}")

        try:
            # 检测编码并读取文件
            raw_text = self._read_text_file(file_path)
            
            if not raw_text:
                return self.create_error_result(file_path, "文本文件为空")

            # 提取标题需要原始文本中的换行符，因此在清理前进行
            title = self._extract_title_by_type(file_path, raw_text)

            # 检查文本长度
            text = raw_text
            if len(text) > self.max_text_length:
                text = text[:self.max_text_length] + "\n... (文本被截断)"
                self.logger.warning(f"文本过长已截断: {file_path}")

            # 清理文本
            text = self.clean_text(text)

            # 根据文件类型提取特定信息
            metadata = self._extract_text_metadata(file_path, text)

            content = ParsedContent(
                text=text,
                title=title,
                metadata={**self.get_file_metadata(file_path), **metadata}
            )
            
            return self.create_success_result(file_path, content)
            
        except Exception as e:
            error_msg = f"文本文件解析失败: {str(e)}"
            self.logger.error(f"{error_msg}, 文件: {file_path}")
            return self.create_error_result(file_path, error_msg)
    
    def _read_text_file(self, file_path: Path) -> str:
        """
        读取文本文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
        """
        try:
            # 首先尝试默认编码
            try:
                with open(file_path, 'r', encoding=self.default_encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                if not self.encoding_detection:
                    raise
                
                # 如果默认编码失败且启用了编码检测，尝试检测编码
                encoding = self._detect_encoding(file_path)
                if encoding and encoding != self.default_encoding:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                else:
                    raise
        
        except Exception as e:
            # 最后尝试二进制读取并忽略错误
            self.logger.warning(f"使用二进制模式读取文件: {file_path}, 错误: {e}")
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                return raw_data.decode('utf-8', errors='ignore')
    
    def _detect_encoding(self, file_path: Path) -> Optional[str]:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 检测到的编码
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10240)  # 读取前10KB用于编码检测
                
            result = chardet.detect(raw_data)
            encoding = result.get('encoding')
            confidence = result.get('confidence', 0)
            
            # 只有当置信度较高时才使用检测到的编码
            if encoding and confidence > 0.7:
                self.logger.info(f"检测到编码: {encoding} (置信度: {confidence:.2f})")
                return encoding
            
        except Exception as e:
            self.logger.warning(f"编码检测失败: {e}")
        
        return None
    
    def _extract_text_metadata(self, file_path: Path, text: str) -> Dict[str, Any]:
        """
        提取文本文件的元数据
        
        Args:
            file_path: 文件路径
            text: 文件内容
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        extension = file_path.suffix.lower()
        
        # 统计信息
        lines = text.split('\n')
        metadata.update({
            'line_count': len(lines),
            'char_count': len(text),
            'word_count': len(text.split()),
            'file_type': self._get_file_type_description(extension),
        })
        
        # 根据文件类型提取特定信息
        if extension in ['.md', '.markdown']:
            metadata.update(self._extract_markdown_metadata(text))
        elif extension == '.json':
            metadata.update(self._extract_json_metadata(text))
        elif extension in ['.yaml', '.yml']:
            metadata.update(self._extract_yaml_metadata(text))
        elif extension in ['.py', '.js']:
            metadata.update(self._extract_code_metadata(text, extension))
        elif extension == '.csv':
            metadata.update(self._extract_csv_metadata(text))
        
        return metadata
    
    def _get_file_type_description(self, extension: str) -> str:
        """
        获取文件类型描述
        
        Args:
            extension: 文件扩展名
            
        Returns:
            str: 文件类型描述
        """
        type_map = {
            '.txt': '纯文本文件',
            '.md': 'Markdown文档',
            '.markdown': 'Markdown文档',
            '.rst': 'reStructuredText文档',
            '.csv': 'CSV数据文件',
            '.json': 'JSON数据文件',
            '.xml': 'XML文档',
            '.html': 'HTML网页',
            '.htm': 'HTML网页',
            '.py': 'Python代码',
            '.js': 'JavaScript代码',
            '.css': 'CSS样式表',
            '.yaml': 'YAML配置文件',
            '.yml': 'YAML配置文件',
            '.ini': 'INI配置文件',
            '.cfg': '配置文件',
            '.conf': '配置文件',
            '.log': '日志文件',
        }
        return type_map.get(extension, '文本文件')
    
    def _extract_markdown_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取Markdown文档的元数据
        
        Args:
            text: Markdown文本
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        lines = text.split('\n')
        
        # 计算标题数量
        h1_count = sum(1 for line in lines if line.startswith('# '))
        h2_count = sum(1 for line in lines if line.startswith('## '))
        h3_count = sum(1 for line in lines if line.startswith('### '))
        
        metadata.update({
            'h1_count': h1_count,
            'h2_count': h2_count, 
            'h3_count': h3_count,
            'total_headings': h1_count + h2_count + h3_count,
        })
        
        # 检查是否有YAML front matter
        if text.startswith('---\n'):
            try:
                end_index = text.find('\n---\n', 4)
                if end_index != -1:
                    import yaml
                    front_matter = text[4:end_index]
                    yaml_data = yaml.safe_load(front_matter)
                    if isinstance(yaml_data, dict):
                        metadata['front_matter'] = yaml_data
            except Exception:
                pass
        
        return metadata
    
    def _extract_json_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取JSON文件的元数据
        
        Args:
            text: JSON文本
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        try:
            import json
            data = json.loads(text)
            
            if isinstance(data, dict):
                metadata['json_keys'] = list(data.keys())[:10]  # 最多10个键
                metadata['json_structure'] = 'object'
            elif isinstance(data, list):
                metadata['json_length'] = len(data)
                metadata['json_structure'] = 'array'
            
        except json.JSONDecodeError:
            metadata['json_valid'] = False
        
        return metadata
    
    def _extract_yaml_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取YAML文件的元数据
        
        Args:
            text: YAML文本
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        try:
            import yaml
            data = yaml.safe_load(text)
            
            if isinstance(data, dict):
                metadata['yaml_keys'] = list(data.keys())[:10]
                metadata['yaml_structure'] = 'mapping'
            elif isinstance(data, list):
                metadata['yaml_length'] = len(data)
                metadata['yaml_structure'] = 'sequence'
            
        except yaml.YAMLError:
            metadata['yaml_valid'] = False
        
        return metadata
    
    def _extract_code_metadata(self, text: str, extension: str) -> Dict[str, Any]:
        """
        提取代码文件的元数据
        
        Args:
            text: 代码文本
            extension: 文件扩展名
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        lines = text.split('\n')
        
        # 基础统计
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        
        metadata.update({
            'code_lines': len(code_lines),
            'comment_lines': len(comment_lines),
            'blank_lines': len(lines) - len(code_lines) - len(comment_lines),
        })
        
        # 语言特定的分析
        if extension == '.py':
            metadata.update(self._extract_python_metadata(text))
        elif extension == '.js':
            metadata.update(self._extract_javascript_metadata(text))
        
        return metadata
    
    def _extract_python_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取Python代码的元数据
        
        Args:
            text: Python代码
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        
        # 简单的关键字计数
        import_count = text.count('import ')
        def_count = text.count('def ')
        class_count = text.count('class ')
        
        metadata.update({
            'import_count': import_count,
            'function_count': def_count,
            'class_count': class_count,
        })
        
        return metadata
    
    def _extract_javascript_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取JavaScript代码的元数据
        
        Args:
            text: JavaScript代码
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        
        # 简单的关键字计数
        function_count = text.count('function ')
        const_count = text.count('const ')
        let_count = text.count('let ')
        var_count = text.count('var ')
        
        metadata.update({
            'function_count': function_count,
            'const_count': const_count,
            'let_count': let_count,
            'var_count': var_count,
        })
        
        return metadata
    
    def _extract_csv_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取CSV文件的元数据
        
        Args:
            text: CSV文本
            
        Returns:
            Dict[str, Any]: 元数据
        """
        metadata = {}
        lines = text.strip().split('\n')
        
        if lines:
            # 第一行通常是表头
            first_line = lines[0]
            # 简单地按逗号分割来估算列数
            estimated_columns = len(first_line.split(','))
            
            metadata.update({
                'estimated_rows': len(lines),
                'estimated_columns': estimated_columns,
                'header_row': first_line[:100] + '...' if len(first_line) > 100 else first_line,
            })
        
        return metadata
    
    def _extract_title_by_type(self, file_path: Path, text: str) -> Optional[str]:
        """
        根据文件类型提取标题
        
        Args:
            file_path: 文件路径
            text: 文件内容
            
        Returns:
            Optional[str]: 提取的标题
        """
        extension = file_path.suffix.lower()
        
        # Markdown文件：查找第一个H1标题
        if extension in ['.md', '.markdown']:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    if title:
                        return title
        
        # HTML文件：查找title标签
        elif extension in ['.html', '.htm']:
            import re
            title_match = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()
        
        # 其他文件类型使用通用方法
        return self.extract_title_from_text(text, file_path.name)
