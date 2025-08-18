"""
解析器测试

测试各种文档解析器的功能
"""

import pytest
import tempfile
from pathlib import Path

from ods.parsers.document_parser import DocumentParser
from ods.parsers.text_parser import TextParser
from ods.core.config import Config


class TestDocumentParser:
    """文档解析器测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            "file": {"max_file_size": 10 * 1024 * 1024},
            "text": {
                "max_length": 100000,
                "encoding_detection": True,
                "default_encoding": "utf-8"
            },
            "parser": {
                "priority": ["text", "pdf", "office", "ocr"],
                "ocr_fallback": False
            }
        }
    
    @pytest.fixture
    def parser(self, config):
        """创建解析器实例"""
        return DocumentParser(config)
    
    def test_text_file_parsing(self, parser):
        """测试文本文件解析"""
        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是一个测试文档。\n\n包含多行内容。\n第三行内容。")
            temp_path = f.name
        
        try:
            result = parser.parse(temp_path)
            
            assert result.success
            assert result.parser_type == "TextParser"
            assert "测试文档" in result.text
            assert result.content.word_count > 0
            
        finally:
            Path(temp_path).unlink()
    
    def test_markdown_file_parsing(self, parser):
        """测试Markdown文件解析"""
        markdown_content = """# 测试标题

这是一个Markdown测试文档。

## 子标题

- 列表项1
- 列表项2

**粗体文本** 和 *斜体文本*。
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            result = parser.parse(temp_path)
            
            assert result.success
            assert result.parser_type == "TextParser"
            assert "测试标题" in result.text
            assert result.content.title == "测试标题"
            
        finally:
            Path(temp_path).unlink()
    
    def test_unsupported_file(self, parser):
        """测试不支持的文件类型"""
        with tempfile.NamedTemporaryFile(suffix='.unknown', delete=False) as f:
            temp_path = f.name
        
        try:
            result = parser.parse(temp_path)
            
            assert not result.success
            assert "不支持的文件类型" in result.error
            
        finally:
            Path(temp_path).unlink()
    
    def test_nonexistent_file(self, parser):
        """测试不存在的文件"""
        result = parser.parse("/path/that/does/not/exist.txt")
        
        assert not result.success
        assert "文件不存在" in result.error
    
    def test_parser_info(self, parser):
        """测试解析器信息"""
        info = parser.get_parser_info()
        
        assert isinstance(info, dict)
        assert "available_parsers" in info
        assert "supported_extensions" in info
        assert isinstance(info["supported_extensions"], list)


class TestTextParser:
    """文本解析器专门测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return {
            "file": {"max_file_size": 10 * 1024 * 1024},
            "text": {
                "max_length": 100000,
                "encoding_detection": True,
                "default_encoding": "utf-8"
            }
        }
    
    @pytest.fixture
    def text_parser(self, config):
        """创建文本解析器实例"""
        return TextParser(config)
    
    def test_json_file_parsing(self, text_parser):
        """测试JSON文件解析"""
        json_content = '{"name": "测试", "type": "文档", "items": [1, 2, 3]}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            result = text_parser.parse(temp_path)
            
            assert result.success
            assert "测试" in result.text
            assert result.content.metadata.get('json_structure') == 'object'
            assert 'name' in result.content.metadata.get('json_keys', [])
            
        finally:
            Path(temp_path).unlink()
    
    def test_python_file_parsing(self, text_parser):
        """测试Python文件解析"""
        python_content = '''#!/usr/bin/env python3
"""测试Python文件"""

import os
import sys

def test_function():
    """测试函数"""
    print("Hello, World!")

class TestClass:
    """测试类"""
    pass

if __name__ == "__main__":
    test_function()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(python_content)
            temp_path = f.name
        
        try:
            result = text_parser.parse(temp_path)
            
            assert result.success
            assert "测试Python文件" in result.text
            assert result.content.metadata.get('function_count', 0) > 0
            assert result.content.metadata.get('class_count', 0) > 0
            assert result.content.metadata.get('import_count', 0) > 0
            
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__])
