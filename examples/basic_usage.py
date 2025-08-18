#!/usr/bin/env python3
"""
基本使用示例

展示如何使用文档解析器解析各种类型的文档
"""

import logging
from pathlib import Path
import tempfile

from ods.core.config import Config
from ods.parsers.document_parser import DocumentParser


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_sample_files():
    """创建示例文件用于测试"""
    sample_files = []
    
    # 创建文本文件
    txt_content = """项目报告

这是一份关于自动文档分类系统的项目报告。

项目目标：
- 实现智能文档分类
- 支持多种文件格式
- 提供用户友好的界面

技术栈：
- Python 3.8+
- LangGraph工作流引擎
- ChromaDB向量数据库
- LlamaIndex文档索引

项目进展：
1. 完成需求分析
2. 设计系统架构
3. 实现文档解析模块
4. 开发分类算法

下一步计划：
- 集成LLM模型
- 实现用户界面
- 进行系统测试
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(txt_content)
        sample_files.append(('文本文件', f.name))
    
    # 创建Markdown文件
    md_content = """# 技术文档

## 系统架构

本系统采用**模块化设计**，主要包含以下组件：

### 核心模块
1. **文档解析器** - 提取文档内容
2. **分类引擎** - 智能分类算法
3. **规则引擎** - 用户自定义规则
4. **存储管理** - 文件操作和索引

### 工作流程
```
文档输入 → 内容解析 → 智能分类 → 规则应用 → 文件移动 → 索引更新
```

## API接口

### DocumentParser
- `parse(file_path)` - 解析文档
- `can_parse(file_path)` - 检查是否支持
- `get_parser_info()` - 获取解析器信息

### 配置选项
- 支持YAML格式配置
- 热重载配置更新
- 多环境配置支持
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(md_content)
        sample_files.append(('Markdown文件', f.name))
    
    # 创建JSON配置文件
    json_content = """{
  "system": {
    "name": "自动文档分类系统",
    "version": "0.1.0",
    "description": "基于LLM和向量数据库的智能文档分类工具"
  },
  "features": [
    "多格式文档解析",
    "智能内容分类",
    "自定义规则引擎",
    "向量语义搜索",
    "批量文件处理"
  ],
  "supported_formats": {
    "documents": [".pdf", ".docx", ".doc", ".pptx", ".ppt"],
    "text": [".txt", ".md", ".rst", ".csv"],
    "code": [".py", ".js", ".java", ".cpp", ".html"],
    "images": [".jpg", ".png", ".gif", ".bmp", ".tiff"]
  },
  "configuration": {
    "max_file_size": "100MB",
    "batch_size": 50,
    "confidence_threshold": 0.8,
    "enable_ocr": true,
    "languages": ["zh-CN", "en-US"]
  }
}"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        f.write(json_content)
        sample_files.append(('JSON配置文件', f.name))
    
    return sample_files


def demonstrate_parsing():
    """演示文档解析功能"""
    print("=== 自动文档分类系统 - 解析器演示 ===\n")
    
    # 设置日志
    setup_logging()
    
    # 创建配置
    print("1. 初始化系统配置...")
    config = Config()
    print(f"   配置文件路径: {config.config_path}")
    
    # 创建文档解析器
    print("2. 初始化文档解析器...")
    parser = DocumentParser(config.get_config_dict())
    
    # 显示解析器信息
    parser_info = parser.get_parser_info()
    print(f"   可用解析器: {', '.join(parser_info['available_parsers'])}")
    print(f"   支持文件类型: {', '.join(parser_info['supported_extensions'][:10])}...")
    
    # 创建示例文件
    print("3. 创建示例文件...")
    sample_files = create_sample_files()
    
    # 解析示例文件
    print("4. 解析文档示例:\n")
    
    for file_type, file_path in sample_files:
        print(f"   正在解析 {file_type}: {Path(file_path).name}")
        
        try:
            result = parser.parse(file_path)
            
            if result.success:
                print(f"   ✓ 解析成功")
                print(f"     解析器: {result.parser_type}")
                print(f"     标题: {result.content.title or '未提取到标题'}")
                print(f"     字数: {result.content.word_count}")
                print(f"     摘要: {result.summary[:100]}...")
                
                # 显示特殊元数据
                metadata = result.content.metadata
                if 'file_type' in metadata:
                    print(f"     文件类型: {metadata['file_type']}")
                if 'json_structure' in metadata:
                    print(f"     JSON结构: {metadata['json_structure']}")
                if 'total_headings' in metadata:
                    print(f"     标题数量: {metadata['total_headings']}")
                
            else:
                print(f"   ✗ 解析失败: {result.error}")
            
        except Exception as e:
            print(f"   ✗ 解析异常: {str(e)}")
        
        print()
    
    # 批量解析演示
    print("5. 批量解析演示:")
    file_paths = [path for _, path in sample_files]
    batch_results = parser.parse_batch(file_paths)
    
    success_count = sum(1 for r in batch_results if r.success)
    print(f"   批量解析结果: {success_count}/{len(batch_results)} 成功")
    
    # 清理临时文件
    print("6. 清理临时文件...")
    for _, file_path in sample_files:
        try:
            Path(file_path).unlink()
        except:
            pass
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    demonstrate_parsing()
