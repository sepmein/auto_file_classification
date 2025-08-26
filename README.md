# 基于LLM和向量数据库的自动文档分类系统

一个智能的文档自动分类和整理系统，基于LLM（大型语言模型）和向量数据库技术，帮助用户自动整理OneDrive等云盘中的文档。

## 功能特性

- 🔍 **智能分类**: 基于文档内容自动识别和分类
- 🏷️ **多标签支持**: 支持交叉分类和多维度标签
- 📁 **自动整理**: 智能移动和重命名文件
- 🔄 **规则引擎**: 可配置的分类和命名规则
- 📊 **向量检索**: 基于语义相似度的智能匹配
- 🛡️ **安全可靠**: 完整的审计日志和回滚机制
- 📄 **多格式支持**: PDF、Word、PowerPoint、文本文件、图片OCR等
- 🎯 **工作流编排**: 基于LangGraph的智能工作流管理

## 技术架构

- **后端**: Python 3.8+
- **工作流引擎**: LangGraph
- **向量数据库**: ChromaDB
- **文档索引**: LlamaIndex
- **LLM支持**: OpenAI, Claude, Ollama
- **嵌入模型**: BGE-M3, E5等
- **文档解析**: pdfminer.six, python-docx, Tesseract OCR
- **配置管理**: YAML + Jinja2模板

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 初始化系统

```bash
python -m ods init
```

### 运行分类整理

```bash
# 处理指定目录
python -m ods apply /path/to/documents

# 模拟运行（不实际移动文件）
python -m ods apply --dry-run /path/to/documents

# 递归处理子目录
python -m ods apply -r /path/to/documents

# 只处理特定文件类型
python -m ods apply --filter-ext pdf --filter-ext docx /path/to/documents
```

### 其他命令

```bash
# 显示系统信息
python -m ods info

# 测试文件解析
python -m ods parse /path/to/document.pdf
```

## LLM配置

系统支持多种LLM提供商，默认使用本地Ollama：

### 使用Ollama（推荐）

```bash
# 1. 安装Ollama
# Windows: winget install Ollama.Ollama
# macOS: brew install ollama  
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# 2. 启动Ollama服务
ollama serve

# 3. 下载模型
ollama pull llama3.2:1b  # 轻量级模型
ollama pull qwen2.5:3b   # 平衡性能

# 4. 测试连接
python test_ollama.py
```

### 使用其他LLM提供商

编辑 `rules.yaml` 文件：

```yaml
llm:
  # 使用OpenAI
  provider: openai
  model: gpt-4o-mini
  api_key: your_openai_api_key_here
  
  # 或使用Claude
  # provider: claude  
  # model: claude-3-haiku-20240307
  # api_key: your_anthropic_api_key_here
```

详细配置说明请参考 [Ollama设置指南](docs/ollama_setup.md)。

## 项目结构

```
auto_file_classification/
├── ods/                    # 核心模块
│   ├── __init__.py
│   ├── cli.py             # 命令行界面
│   ├── core/              # 核心功能
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 数据库操作
│   │   └── workflow.py    # LangGraph工作流引擎
│   ├── parsers/           # 文档解析器
│   │   ├── base_parser.py
│   │   ├── document_parser.py
│   │   ├── pdf_parser.py
│   │   ├── office_parser.py
│   │   ├── text_parser.py
│   │   └── ocr_parser.py
│   ├── classifiers/       # 分类器
│   │   ├── classifier.py
│   │   ├── llm_classifier.py
│   │   ├── retrieval_agent.py
│   │   └── rule_checker.py
│   ├── rules/             # 规则引擎
│   │   └── rule_engine.py
│   ├── storage/           # 存储管理
│   │   ├── file_mover.py
│   │   └── index_updater.py
│   ├── naming/            # 命名管理
│   │   └── renamer.py
│   ├── path_planner/      # 路径规划
│   │   └── path_planner.py
│   ├── embeddings/        # 嵌入模型
│   └── utils/             # 工具函数
├── config/                 # 配置文件
│   ├── category_mapping.yaml
│   ├── naming_templates.yaml
│   └── rules.yaml
├── tests/                  # 测试文件
├── docs/                   # 文档
├── examples/               # 示例代码
└── real_test_documents/   # 测试文档
```

## 已实现功能

### ✅ 阶段1: MVP实现 - 基础分类功能

- [x] 文档解析器（PDF、Word、PowerPoint、文本、OCR）
- [x] 配置管理系统
- [x] 数据库索引
- [x] 基础工作流框架
- [x] 命令行界面
- [x] 文件移动和重命名
- [x] 分类规则引擎
- [x] 向量嵌入和检索
- [x] LLM分类器
- [x] 路径规划器
- [x] 索引更新器

### 🔄 阶段2: 多标签支持与改进

- [ ] 交叉分类优化
- [ ] 高级规则引擎
- [ ] 用户反馈学习

### 📋 阶段3: 规则引擎扩展与高级功能

- [ ] 自定义分类模板
- [ ] 批量处理优化
- [ ] 实时监控

## 使用示例

### 基础使用

```python
from ods.core.workflow import DocumentClassificationWorkflow
from ods.core.config import Config

# 加载配置
config = Config()
workflow = DocumentClassificationWorkflow(config.get_config_dict())

# 处理单个文件
result = workflow.process_file("/path/to/document.pdf")
print(f"分类结果: {result['classification']}")
```

### 文档解析

```python
from ods.parsers.document_parser import DocumentParser

parser = DocumentParser()
result = parser.parse("/path/to/document.pdf")

if result.success:
    print(f"标题: {result.content.title}")
    print(f"内容: {result.content.text[:200]}...")
    print(f"字数: {result.content.word_count}")
```

### 分类器使用

```python
from ods.classifiers.llm_classifier import LLMClassifier

classifier = LLMClassifier()
categories = classifier.classify("这是一份财务报告...")
print(f"分类: {categories}")
```

## 配置说明

系统使用YAML配置文件管理各种设置：

- **category_mapping.yaml**: 分类映射规则
- **naming_templates.yaml**: 文件命名模板
- **rules.yaml**: 分类和移动规则

配置文件支持Jinja2模板语法，可以动态生成路径和文件名。

## 开发指南

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black ods/
flake8 ods/
```

### 类型检查

```bash
mypy ods/
```

## 贡献指南

欢迎提交Issue和Pull Request！请确保：

1. 代码通过所有测试
2. 遵循项目的代码风格
3. 添加适当的文档和注释
4. 更新相关的测试用例

## 许可证

MIT License

## 更新日志

### v0.1.0 (当前版本)

- 完整的文档解析器实现
- 基于LangGraph的工作流引擎
- 向量数据库集成
- LLM分类器支持
- 规则引擎框架
- 命令行界面
- 完整的测试覆盖

## 支持

如果您遇到问题或有建议，请：

1. 查看项目文档
2. 搜索现有Issue
3. 创建新的Issue描述问题
4. 提交Pull Request贡献代码
