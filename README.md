# 基于LLM和向量数据库的自动文档分类系统

一个智能的文档自动分类和整理系统，基于LLM（大型语言模型）和向量数据库技术，帮助用户自动整理OneDrive等云盘中的文档。

## 功能特性

- 🔍 **智能分类**: 基于文档内容自动识别和分类
- 🏷️ **多标签支持**: 支持交叉分类和多维度标签
- 📁 **自动整理**: 智能移动和重命名文件
- 🔄 **规则引擎**: 可配置的分类和命名规则
- 📊 **向量检索**: 基于语义相似度的智能匹配
- 🛡️ **安全可靠**: 完整的审计日志和回滚机制

## 技术架构

- **后端**: Python 3.8+
- **工作流引擎**: LangGraph
- **向量数据库**: ChromaDB
- **文档索引**: LlamaIndex
- **LLM支持**: OpenAI, Claude, Ollama
- **嵌入模型**: BGE-M3, E5等

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
python -m ods apply
```

## 项目结构

```
auto_file_classification_2/
├── ods/                    # 核心模块
│   ├── __init__.py
│   ├── core/              # 核心功能
│   ├── parsers/           # 文档解析器
│   ├── classifiers/       # 分类器
│   ├── rules/             # 规则引擎
│   ├── storage/           # 存储管理
│   └── utils/             # 工具函数
├── config/                 # 配置文件
├── tests/                  # 测试文件
├── docs/                   # 文档
├── examples/               # 示例配置
└── scripts/                # 脚本工具
```

## 开发计划

- [x] 阶段1: MVP实现 - 基础分类功能
- [ ] 阶段2: 多标签支持与改进
- [ ] 阶段3: 规则引擎扩展与高级功能

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License
