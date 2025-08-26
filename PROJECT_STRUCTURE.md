# 项目结构说明

## 目录结构

```
auto_file_classification/
├── ods/                    # 核心模块包
│   ├── __init__.py
│   ├── __main__.py         # 模块入口点
│   ├── cli.py              # 命令行界面
│   ├── core/               # 核心功能模块
│   │   ├── __init__.py
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库操作
│   │   └── workflow.py     # LangGraph工作流引擎
│   ├── parsers/            # 文档解析器
│   │   ├── __init__.py
│   │   ├── base_parser.py  # 解析器基类
│   │   ├── document_parser.py  # 通用文档解析器
│   │   ├── pdf_parser.py   # PDF解析器
│   │   ├── office_parser.py    # Office文档解析器
│   │   ├── text_parser.py  # 文本文件解析器
│   │   └── ocr_parser.py   # OCR图像解析器
│   ├── classifiers/        # 分类器模块
│   │   ├── __init__.py
│   │   ├── classifier.py   # 分类器基类
│   │   ├── llm_classifier.py   # LLM分类器
│   │   ├── retrieval_agent.py  # 检索代理
│   │   └── rule_checker.py     # 规则检查器
│   ├── rules/              # 规则引擎
│   │   ├── __init__.py
│   │   └── rule_engine.py  # 规则引擎核心
│   ├── storage/            # 存储管理
│   │   ├── __init__.py
│   │   ├── file_mover.py   # 文件移动器
│   │   └── index_updater.py    # 索引更新器
│   ├── naming/             # 命名管理
│   │   ├── __init__.py
│   │   └── renamer.py      # 文件重命名器
│   ├── path_planner/       # 路径规划
│   │   ├── __init__.py
│   │   └── path_planner.py # 路径规划器
│   ├── embeddings/         # 嵌入模型（待实现）
│   │   └── __init__.py
│   └── utils/              # 工具函数（待实现）
│       └── __init__.py
├── config/                  # 配置文件目录
│   ├── category_mapping.yaml   # 分类映射规则
│   ├── naming_templates.yaml   # 文件命名模板
│   └── rules.yaml             # 主配置文件
├── tests/                   # 测试文件目录
│   ├── __init__.py
│   ├── test_classifiers.py    # 分类器测试
│   ├── test_embeddings.py     # 嵌入模型测试
│   ├── test_file_mover.py     # 文件移动器测试
│   ├── test_index_updater.py  # 索引更新器测试
│   ├── test_parsers.py        # 解析器测试
│   ├── test_path_planner.py   # 路径规划器测试
│   ├── test_renamer.py        # 重命名器测试
│   └── test_stage1_e2e.py    # 端到端测试
├── docs/                    # 项目文档
│   ├── README.md               # 文档目录说明
│   ├── classification_module.md    # 分类模块文档
│   ├── embeddings_module.md       # 嵌入模块文档
│   ├── index_updater_module.md    # 索引更新模块文档
│   ├── naming_module.md           # 命名模块文档
│   ├── path_planning_module.md    # 路径规划模块文档
│   ├── ollama_setup.md            # Ollama设置指南
│   └── classification_implementation_summary.md  # 实现总结
├── examples/                # 示例代码
│   ├── README.md               # 示例说明
│   ├── classification_demo.py  # 分类演示
│   ├── embedding_demo.py       # 嵌入演示
│   ├── index_updater_demo.py   # 索引更新演示
│   ├── naming_demo.py          # 命名演示
│   └── path_planning_demo.py   # 路径规划演示
├── data/                    # 数据目录
│   ├── chroma_db/             # ChromaDB向量数据库
│   └── llama_index/           # LlamaIndex索引数据
├── real_test_documents/     # 真实测试文档
├── test_documents/          # 测试文档
├── OneDrive/                # OneDrive同步目录
├── pyproject.toml           # 项目配置文件
├── PROJECT_STRUCTURE.md     # 项目结构说明
├── project_plan.md          # 项目计划
└── README.md                # 项目主文档
```

## 模块说明

### 核心模块 (ods/core/)

- **config.py**: 配置管理，支持YAML配置文件和环境变量
- **database.py**: 数据库操作，包括SQLite和向量数据库
- **workflow.py**: LangGraph工作流引擎，协调各个模块

### 解析器模块 (ods/parsers/)

- **base_parser.py**: 所有解析器的基类，定义通用接口
- **document_parser.py**: 通用文档解析器，支持多种格式
- **pdf_parser.py**: PDF文档解析，使用pdfminer.six
- **office_parser.py**: Office文档解析，支持Word、PowerPoint、Excel
- **text_parser.py**: 纯文本文件解析
- **ocr_parser.py**: 图像OCR解析，使用Tesseract

### 分类器模块 (ods/classifiers/)

- **classifier.py**: 分类器基类，定义分类接口
- **llm_classifier.py**: 基于LLM的分类器
- **retrieval_agent.py**: 检索增强分类代理
- **rule_checker.py**: 基于规则的分类检查器

### 存储模块 (ods/storage/)

- **file_mover.py**: 文件移动和重命名操作
- **index_updater.py**: 向量索引和数据库更新

### 其他模块

- **naming/**: 智能文件命名生成
- **path_planner/**: 文件路径规划和目录结构管理
- **rules/**: 可配置的分类和移动规则引擎

## 配置文件说明

### rules.yaml (主配置文件)

- LLM服务配置
- 嵌入模型设置
- 数据库配置
- 分类规则
- 文件处理参数
- 系统设置

### category_mapping.yaml

- 分类映射规则
- 标签关联关系
- 优先级设置

### naming_templates.yaml

- 文件命名模板
- 变量定义
- 冲突解决策略

## 测试结构

测试文件按模块组织，每个模块都有对应的测试文件：

- 单元测试覆盖核心功能
- 集成测试验证模块间协作
- 端到端测试验证完整工作流

## 示例代码

示例代码展示各模块的使用方法：

- 基础用法演示
- 高级功能展示
- 配置示例
- 最佳实践

## 文档结构

文档按模块组织，包含：

- 模块设计说明
- API接口文档
- 使用示例
- 配置指南
- 部署说明
