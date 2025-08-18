# 分类判定模块

## 概述

分类判定模块（LangGraph节点：ClassifierAgent + RetrievalActions）是系统的智能核心，负责根据文档向量及文本摘要，确定文档所属的类别标签。该模块结合向量检索和LLM推理两方面，实现了基于内容的智能分类决策。

## 架构设计

### 核心组件

1. **RetrievalAgent（检索代理）**
   - 负责与Chroma向量数据库交互
   - 检索相似文档和类别示例
   - 管理向量数据库的增删改查操作

2. **LLMClassifier（LLM分类器）**
   - 调用LLM进行智能分类决策
   - 支持多种LLM提供商（OpenAI、Anthropic、Ollama）
   - 智能提示模板和响应解析

3. **RuleChecker（规则检查器）**
   - 应用用户定义的分类规则
   - 支持多种规则类型（文件扩展名、文件名、内容关键词等）
   - 规则优先级管理和动态调整

4. **DocumentClassifier（文档分类器）**
   - 整合所有分类组件的主控制器
   - 协调完整的分类流水线
   - 提供批量处理和统计功能

### 工作流程

```
文档输入 → 向量检索 → LLM分类 → 规则检查 → 结果存储 → 分类完成
    ↓           ↓         ↓         ↓         ↓
  解析结果   相似文档   智能分类   规则应用   向量数据库
```

## 功能特性

### 向量检索

- **相似文档搜索**: 基于文档向量在ChromaDB中检索语义相似的文档
- **类别示例获取**: 为每个类别提供代表性文档示例
- **元数据管理**: 完整的文档元数据存储和查询
- **集合管理**: 支持多个文档集合的独立管理

### LLM智能分类

- **多提供商支持**: OpenAI GPT系列、Anthropic Claude、Ollama本地模型
- **智能提示**: 基于相似文档和类别示例的动态提示构建
- **响应解析**: 智能解析LLM输出，支持JSON和自然语言格式
- **置信度评估**: 自动评估分类结果的置信度
- **备用策略**: 当LLM不可用时的备用分类方法

### 规则引擎

- **文件扩展名规则**: 基于文件类型的快速分类
- **文件名规则**: 基于文件名关键词的分类
- **内容关键词规则**: 基于文档内容的语义分类
- **文件大小规则**: 基于文件大小的分类策略
- **自定义规则**: 支持复杂的条件表达式

### 分类管理

- **多标签支持**: 支持一个文档属于多个类别
- **置信度阈值**: 可配置的分类置信度阈值
- **人工复核**: 低置信度结果的自动标记
- **批量处理**: 支持大量文档的并行分类
- **结果导出**: 分类结果的多种格式导出

## 配置说明

### 基础配置

```yaml
# 分类配置
classification:
  categories:
    - "工作"
    - "个人" 
    - "财务"
    - "其他"
  confidence_threshold: 0.8
  review_threshold: 0.6
  max_tags: 3

# LLM配置
llm:
  provider: "openai"  # openai, anthropic, ollama
  model: "gpt-4"
  api_key: "your-api-key"
  temperature: 0.1
  max_tokens: 1000

# 向量数据库配置
database:
  vector_db_path: ".ods/vector_db"
  collection_name: "documents"
  top_k: 5
  similarity_threshold: 0.7

# 规则配置
rules:
  enable_rules: true
  strict_mode: false
  rules_file: "config/rules.yaml"
```

### 规则配置示例

```yaml
# 文件扩展名规则
file_extension:
  ".pdf": 
    category: "文档"
    priority: 1
  ".docx":
    category: "文档"
    priority: 1

# 文件名规则
file_name:
  "发票":
    category: "财务"
    priority: 2
  "合同":
    category: "工作"
    priority: 2

# 内容关键词规则
content_keywords:
  "发票":
    category: "财务"
    priority: 3
  "项目":
    category: "工作"
    priority: 3
```

## 使用方法

### 基本用法

```python
from ods.classifiers.classifier import DocumentClassifier

# 创建分类器
config = {
    'classification': {
        'categories': ['工作', '个人', '财务', '其他'],
        'confidence_threshold': 0.8
    },
    'llm': {
        'provider': 'openai',
        'api_key': 'your-api-key'
    }
}

classifier = DocumentClassifier(config)

# 分类单个文档
document_data = {
    'file_path': '/path/to/document.pdf',
    'summary': '这是一份关于项目管理的文档',
    'embedding': document_embedding,
    'metadata': {'size': 1024}
}

result = classifier.classify_document(document_data)
print(f"分类结果: {result['primary_category']}")
print(f"置信度: {result['confidence_score']}")
print(f"需要复核: {result['needs_review']}")
```

### 批量分类

```python
# 批量分类多个文档
documents = [
    {'file_path': '/doc1.pdf', 'summary': '文档1内容...'},
    {'file_path': '/doc2.pdf', 'summary': '文档2内容...'},
    # ...更多文档
]

results = classifier.batch_classify(documents)

for result in results:
    if result['status'] == 'success':
        print(f"成功分类: {result['file_path']} -> {result['primary_category']}")
    else:
        print(f"分类失败: {result['file_path']}: {result['error_message']}")
```

### 规则管理

```python
from ods.classifiers.rule_checker import RuleChecker

rule_checker = RuleChecker(config)

# 添加新规则
rule_checker.add_rule('file_name', '简历', '个人', 2)

# 删除规则
rule_checker.remove_rule('file_name', '简历')

# 获取规则摘要
summary = rule_checker.get_rules_summary()
print(f"总规则数: {summary['total_rules']}")
```

### 向量检索

```python
from ods.classifiers.retrieval_agent import RetrievalAgent

retrieval_agent = RetrievalAgent(config)

# 搜索相似文档
similar_docs = retrieval_agent.search_similar_documents(
    query_embedding, 
    top_k=5
)

# 获取类别示例
examples = retrieval_agent.get_category_examples('工作', top_k=3)

# 获取统计信息
stats = retrieval_agent.get_collection_stats()
print(f"总文档数: {stats['total_documents']}")
```

## 高级功能

### 自定义规则

```python
# 自定义规则配置
custom_rules = {
    'complex_rule': {
        'condition': 'path_contains("重要") and size_greater_than(1048576)',
        'category': '重要文档',
        'priority': 5
    }
}

# 应用自定义规则
rule_checker.import_rules(custom_rules)
```

### 分类结果更新

```python
# 更新文档分类
new_classification = {
    'primary_category': '工作',
    'secondary_categories': ['项目管理'],
    'confidence_score': 0.95,
    'needs_review': False
}

success = classifier.update_document_classification(
    doc_id='doc_123',
    new_classification=new_classification
)
```

### 数据导出

```python
# 导出分类数据
classifier.export_classification_data('export/classification_data.json')

# 导出规则配置
rule_checker.export_rules('export/rules.yaml')
```

## 性能优化

### 批量处理

- 使用ThreadPoolExecutor进行并行处理
- 可配置的批处理大小和并行度
- 内存使用优化和垃圾回收

### 向量检索优化

- 支持多种相似度算法
- 可配置的检索参数（top_k、阈值等）
- 索引优化和查询缓存

### LLM调用优化

- 智能重试机制
- 响应缓存和复用
- 批量请求优化

## 错误处理

### 常见错误

1. **LLM连接失败**
   - 自动切换到备用分类策略
   - 记录错误日志和重试信息

2. **向量数据库错误**
   - 优雅降级到内存存储
   - 自动重连和恢复机制

3. **规则解析错误**
   - 跳过有问题的规则
   - 记录规则执行日志

### 重试机制

- 可配置的重试次数和间隔
- 指数退避策略
- 错误分类和优先级处理

## 监控和日志

### 性能监控

- 分类处理时间统计
- 成功率监控
- 资源使用情况

### 日志记录

- 详细的分类过程日志
- 错误和异常记录
- 性能指标记录

### 统计报告

- 分类结果统计
- 规则使用情况
- 系统健康状态

## 扩展开发

### 添加新LLM提供商

```python
class CustomLLMClassifier(LLMClassifier):
    def _setup_llm_client(self):
        # 实现自定义LLM客户端设置
        pass
    
    def _call_llm(self, prompt: str) -> str:
        # 实现自定义LLM调用逻辑
        pass
```

### 自定义规则类型

```python
class CustomRuleChecker(RuleChecker):
    def _check_custom_rules(self, document_data, rules):
        # 实现自定义规则检查逻辑
        pass
```

### 集成新的向量数据库

```python
class CustomRetrievalAgent(RetrievalAgent):
    def _setup_vector_db(self):
        # 实现自定义向量数据库连接
        pass
```

## 测试和验证

### 运行测试

```bash
# 运行所有分类器测试
pytest tests/test_classifiers.py -v

# 运行特定测试类
pytest tests/test_classifiers.py::TestDocumentClassifier -v

# 运行特定测试方法
pytest tests/test_classifiers.py::TestDocumentClassifier::test_classify_document -v
```

### 演示脚本

```bash
# 运行分类模块演示
python examples/classification_demo.py
```

### 性能测试

```bash
# 运行性能基准测试
python -m pytest tests/test_classifiers.py::TestPerformance -v
```

## 部署和运维

### 环境要求

- Python 3.8+
- 足够的RAM（建议8GB+）
- GPU支持（可选，用于本地模型）

### 依赖安装

```bash
pip install chromadb openai anthropic pyyaml
pip install sentence-transformers torch
```

### 配置管理

- 使用环境变量管理敏感信息
- 支持多环境配置
- 配置热重载支持

### 监控告警

- 分类成功率监控
- 响应时间告警
- 错误率监控

## 故障排除

### 常见问题

1. **LLM响应超时**
   - 检查网络连接
   - 调整超时参数
   - 使用备用模型

2. **向量数据库性能问题**
   - 检查索引状态
   - 优化查询参数
   - 考虑分片和复制

3. **分类准确率下降**
   - 检查训练数据质量
   - 调整置信度阈值
   - 更新规则配置

### 调试技巧

- 启用详细日志
- 使用测试模式
- 逐步验证各组件

## 更新日志

### v0.1.0 (当前版本)
- 初始版本，支持基本的分类功能
- 集成ChromaDB向量数据库
- 支持OpenAI、Anthropic、Ollama
- 实现规则引擎和LLM分类器
- 提供完整的测试和文档

### 计划功能
- 支持更多LLM提供商
- 增强的规则引擎
- 实时分类流处理
- 多语言支持
- 高级分析和报告功能

## 贡献指南

### 代码规范
- 遵循PEP 8编码规范
- 添加完整的类型注解
- 编写详细的文档字符串

### 测试要求
- 新功能需要添加测试
- 保持测试覆盖率在90%以上
- 包含单元测试和集成测试

### 文档更新
- 新功能需要更新文档
- 保持示例代码的可运行性
- 及时更新配置说明
