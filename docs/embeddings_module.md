# 嵌入生成模块

## 概述

嵌入生成模块（LangGraph节点：Embedder）是系统的核心组件之一，负责将文档文本转换为高维向量表示。通过向量化，系统可以利用数学空间中的相似度来衡量文档语义相近性，为后续的分类和检索提供基础。

## 架构设计

### 核心组件

1. **TextProcessor（文本处理器）**
   - 文本清理和预处理
   - 长文本智能分块
   - 摘要生成
   - 关键词提取
   - 文本统计分析

2. **EmbeddingModel（嵌入模型）**
   - 抽象基类定义统一接口
   - 支持本地模型和API模型
   - 自动设备选择（CPU/GPU）
   - 模型信息管理

3. **Embedder（嵌入生成器）**
   - LangGraph节点实现
   - 文档处理流水线
   - 批量处理支持
   - 错误处理和重试机制

### 支持模型

#### 本地模型
- **BGE-M3**: 多语言嵌入模型，支持8192字符输入，1024维输出
- **E5-Large**: 英文嵌入模型，支持512字符输入，1024维输出
- **自定义模型**: 支持本地训练的模型文件

#### API模型
- **OpenAI**: text-embedding-ada-002等
- **Anthropic**: Claude相关模型
- **自定义端点**: 支持私有部署的模型服务

## 功能特性

### 文本预处理
- **智能清理**: 移除多余空白、特殊字符、URL等
- **停用词过滤**: 可选的停用词移除
- **词形还原**: 可选的词形还原处理
- **编码处理**: 自动检测和处理各种文本编码

### 长文本处理
- **智能分块**: 基于句子边界的智能分块策略
- **固定分块**: 固定大小的分块策略
- **重叠处理**: 保持块之间的语义连续性
- **池化合并**: 多块嵌入的智能合并策略

### 向量生成
- **批量处理**: 支持批量文档处理
- **并行计算**: 多线程并行处理提高效率
- **错误恢复**: 自动重试和错误处理
- **质量保证**: 向量维度和质量验证

### 元数据提取
- **摘要生成**: 自动生成文档摘要
- **关键词提取**: 基于词频的关键词识别
- **统计信息**: 字符数、词数、句子数等统计
- **处理信息**: 分块策略、处理时间等元数据

## 配置说明

### 基础配置

```yaml
embedding:
  type: "local"  # local 或 api
  model_name: "BAAI/bge-m3"
  device: "auto"  # auto, cpu, cuda
  max_length: 8192
  dimension: 1024
  batch_size: 32
  max_workers: 4
  chunk_strategy: "smart"  # smart, fixed, none
  fallback_strategy: "retry"  # retry, skip, alternative
```

### 本地模型配置

```yaml
embedding:
  local:
    model_path: null  # 自定义模型路径
    cache_dir: ".ods/models"
```

### API模型配置

```yaml
embedding:
  api:
    provider: "openai"
    api_key: "your-api-key"
    api_base: null  # 自定义API端点
    timeout: 30
    retry_attempts: 3
```

### 文本处理配置

```yaml
text_processing:
  max_chunk_size: 1000
  overlap_size: 100
  min_chunk_size: 100
  clean_text: true
  remove_stopwords: false
  lemmatize: false
  generate_summary: true
  extract_keywords: true
  max_summary_length: 200
  max_keywords: 10
```

## 使用方法

### 基本用法

```python
from ods.embeddings.embedder import Embedder

# 创建嵌入生成器
config = {
    'embedding': {
        'type': 'local',
        'model_name': 'BAAI/bge-m3'
    }
}
embedder = Embedder(config)

# 处理单个文档
document_data = {
    'file_path': '/path/to/document.pdf',
    'text_content': '文档内容...',
    'metadata': {'size': 1024}
}

result = embedder.process_document(document_data)
print(f"向量维度: {result['embedding_dimension']}")
print(f"摘要: {result['summary']}")
print(f"关键词: {result['keywords']}")
```

### 批量处理

```python
# 批量处理多个文档
documents = [
    {'file_path': '/doc1.pdf', 'text_content': '内容1...'},
    {'file_path': '/doc2.pdf', 'text_content': '内容2...'},
    # ...更多文档
]

results = embedder.process_batch(documents)
for result in results:
    if result['status'] == 'success':
        print(f"成功处理: {result['file_path']}")
    else:
        print(f"处理失败: {result['file_path']}: {result['error_message']}")
```

### 工作流集成

```python
from ods.core.workflow import DocumentClassificationWorkflow

# 工作流会自动调用嵌入节点
workflow = DocumentClassificationWorkflow(config)
result = workflow.process_file('/path/to/document.pdf')

# 结果包含嵌入信息
if result.get('embedding_success'):
    embedding = result['embedding']
    summary = result['embedding_summary']
    keywords = result['embedding_keywords']
```

## 性能优化

### 模型选择
- **本地模型**: 适合离线环境，无网络延迟，但需要本地计算资源
- **API模型**: 适合在线环境，无需本地资源，但有网络延迟和成本

### 分块策略
- **smart**: 智能分块，保持语义完整性，推荐使用
- **fixed**: 固定分块，处理速度快，但可能破坏语义
- **none**: 不分块，适合短文本

### 并行处理
- 调整 `max_workers` 参数优化并行度
- 根据CPU核心数和内存大小调整 `batch_size`
- 监控GPU内存使用情况

## 错误处理

### 常见错误
1. **模型加载失败**: 检查模型名称和路径
2. **内存不足**: 减少batch_size或使用更小的模型
3. **网络超时**: 增加timeout参数或检查网络连接
4. **文本过长**: 调整max_length或启用分块

### 重试机制
- 自动重试失败的请求
- 可配置重试次数和间隔
- 支持备用策略（跳过、使用替代模型）

## 测试和验证

### 运行测试

```bash
# 运行所有测试
pytest tests/test_embeddings.py -v

# 运行特定测试类
pytest tests/test_embeddings.py::TestTextProcessor -v

# 运行特定测试方法
pytest tests/test_embeddings.py::TestTextProcessor::test_clean_text -v
```

### 演示脚本

```bash
# 运行演示脚本
python examples/embedding_demo.py
```

## 扩展开发

### 添加新模型
1. 继承 `EmbeddingModel` 基类
2. 实现 `encode` 和 `get_model_info` 方法
3. 在 `EmbeddingModelFactory` 中注册

### 自定义文本处理
1. 继承 `TextProcessor` 类
2. 重写相关方法
3. 在配置中指定自定义处理器

### 集成新提供商
1. 在 `APIEmbeddingModel` 中添加新提供商支持
2. 实现相应的客户端设置
3. 更新配置验证逻辑

## 注意事项

1. **模型下载**: 首次使用本地模型会自动下载，需要网络连接
2. **内存管理**: 大模型需要足够的内存，建议使用GPU加速
3. **API限制**: 使用API模型时注意请求频率和配额限制
4. **文本编码**: 确保输入文本使用正确的编码格式
5. **模型版本**: 不同版本的模型可能有不同的输入输出格式

## 故障排除

### 问题诊断
1. 检查日志输出获取详细错误信息
2. 验证配置文件格式和参数
3. 测试模型连接和权限
4. 检查系统资源和依赖

### 性能调优
1. 监控处理时间和资源使用
2. 调整分块和批处理参数
3. 选择合适的模型和策略
4. 优化文本预处理流程

## 更新日志

- **v0.1.0**: 初始版本，支持基本的嵌入生成功能
- 支持BGE-M3和E5模型
- 实现智能文本分块
- 集成到LangGraph工作流
- 提供完整的测试和文档
