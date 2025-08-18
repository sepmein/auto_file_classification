# 项目结构说明

## 目录结构

```
auto_file_classification_2/
├── ods/                        # 核心模块包
│   ├── __init__.py            # 主模块入口
│   ├── cli.py                 # 命令行界面
│   ├── core/                  # 核心功能模块
│   │   ├── __init__.py
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库操作
│   │   └── workflow.py        # LangGraph工作流引擎
│   ├── parsers/               # 文档解析器模块
│   │   ├── __init__.py
│   │   ├── base_parser.py     # 基础解析器抽象类
│   │   ├── document_parser.py # 主文档解析器
│   │   ├── pdf_parser.py      # PDF解析器
│   │   ├── office_parser.py   # Office文档解析器
│   │   ├── text_parser.py     # 文本文件解析器
│   │   └── ocr_parser.py      # OCR图片解析器
│   ├── classifiers/           # 分类器模块（占位符）
│   │   ├── __init__.py
│   │   └── classifier.py
│   ├── rules/                 # 规则引擎模块（占位符）
│   │   ├── __init__.py
│   │   └── rule_engine.py
│   ├── storage/               # 存储管理模块（占位符）
│   │   ├── __init__.py
│   │   ├── file_mover.py
│   │   └── index_updater.py
│   └── utils/                 # 工具函数模块
│       └── __init__.py
├── config/                    # 配置文件
│   └── rules.yaml            # 默认配置文件
├── tests/                     # 测试文件
│   ├── __init__.py
│   └── test_parsers.py       # 解析器测试
├── examples/                  # 使用示例
│   └── basic_usage.py        # 基本使用示例
├── docs/                      # 文档（未创建）
├── scripts/                   # 脚本工具（未创建）
├── requirements.txt           # Python依赖
├── pyproject.toml            # 项目配置
├── README.md                 # 项目说明
├── .gitignore               # Git忽略文件
├── project_plan.md          # 项目计划文档
└── PROJECT_STRUCTURE.md     # 本文件
```

## 模块说明

### 核心模块 (ods/core/)

- **config.py**: 配置管理器，负责加载、验证和管理系统配置
- **database.py**: SQLite数据库管理，处理文件索引、分类结果和操作日志
- **workflow.py**: LangGraph工作流引擎，协调各个模块的执行

### 解析器模块 (ods/parsers/)

内容提取模块的完整实现，支持多种文档格式：

- **base_parser.py**: 定义解析器抽象接口和通用功能
- **document_parser.py**: 主解析器，根据文件类型自动选择合适的解析器
- **pdf_parser.py**: PDF文档解析，使用pdfminer.six提取文本和元数据
- **office_parser.py**: Office文档解析，支持Word、PowerPoint、Excel
- **text_parser.py**: 文本文件解析，支持多种编码和格式
- **ocr_parser.py**: OCR图片解析，使用Tesseract提取图片中的文字

### 其他模块

- **classifiers/**: 分类器模块（当前为占位符实现）
- **rules/**: 规则引擎模块（当前为占位符实现）
- **storage/**: 存储管理模块（当前为占位符实现）
- **utils/**: 工具函数模块

## 已实现功能

### ✅ 内容提取模块
- [x] 基础解析器框架
- [x] PDF文档解析（pdfminer.six）
- [x] Office文档解析（python-docx, python-pptx, openpyxl）
- [x] 文本文件解析（支持多种编码）
- [x] OCR图片解析（Tesseract）
- [x] 统一解析器接口
- [x] 错误处理和日志记录
- [x] 批量解析支持
- [x] 文档元数据提取

### ✅ 配置管理
- [x] YAML配置文件支持
- [x] 配置验证和默认值
- [x] 多层级配置结构
- [x] 配置文件自动创建

### ✅ 数据库管理
- [x] SQLite数据库设计
- [x] 文件索引表
- [x] 分类结果表
- [x] 操作日志表
- [x] 用户反馈表

### ✅ 命令行界面
- [x] 基础CLI命令
- [x] 文件解析测试功能
- [x] 系统信息查看
- [x] 配置管理命令

## 待实现功能

### 🔲 分类器模块
- [ ] LLM集成（OpenAI/Claude/Ollama）
- [ ] 向量嵌入模型集成
- [ ] ChromaDB向量数据库
- [ ] LlamaIndex文档索引
- [ ] 多标签分类支持

### 🔲 规则引擎
- [ ] 规则解析和执行
- [ ] Jinja2模板支持
- [ ] 条件匹配逻辑
- [ ] 规则优先级管理

### 🔲 存储管理
- [ ] 文件移动和重命名
- [ ] 多视图软链接创建
- [ ] 路径冲突处理
- [ ] 审计和回滚功能

### 🔲 工作流集成
- [ ] LangGraph节点连接
- [ ] 错误恢复机制
- [ ] 并行处理支持
- [ ] 进度监控

## 技术特性

### 文档解析能力
- **多格式支持**: PDF、Word、PowerPoint、Excel、文本、图片
- **智能编码检测**: 自动检测文本文件编码
- **元数据提取**: 提取文档标题、作者、创建时间等信息
- **OCR支持**: 从图片和扫描PDF中提取文字
- **错误恢复**: 多层级的错误处理和备用方案

### 系统设计
- **模块化架构**: 清晰的模块分离，便于扩展和维护
- **配置驱动**: 通过YAML配置文件控制系统行为
- **日志记录**: 完整的操作日志和错误追踪
- **测试覆盖**: 单元测试和集成测试支持

## 使用方法

### 安装依赖
```bash
pip install -r requirements.txt
```

### 初始化系统
```bash
python -m ods init
```

### 解析文档
```bash
python -m ods parse path/to/document.pdf
```

### 查看系统信息
```bash
python -m ods info
```

### 运行示例
```bash
python examples/basic_usage.py
```

### 运行测试
```bash
pytest tests/
```

## 开发计划

按照项目计划文档，后续将按以下阶段继续开发：

1. **阶段2**: 多标签支持与改进
   - 实现LLM分类器
   - 添加向量数据库支持
   - 实现多标签分类和交叉分类

2. **阶段3**: 规则引擎扩展与高级功能
   - 完善规则引擎
   - 实现文件移动和重命名
   - 添加审计和回滚功能

目前已完成阶段1的核心内容提取模块，为后续功能实现奠定了坚实基础。
