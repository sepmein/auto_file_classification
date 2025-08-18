# 索引更新器模块 (IndexUpdater)

## 概述

索引更新器模块是自动文档分类系统的核心组件之一，负责在文件成功分类移动后更新系统的内部索引、日志和知识库。该模块为未来的检索和推理提供支持，并记录完整的操作审计信息。

## 主要功能

### 1. 向量库更新
- 将新文档的嵌入向量及其分类标签写入 ChromaDB 向量数据库
- 支持类别中心向量的维护和更新
- 确保新文档成为"已归类知识库"的一部分

### 2. LlamaIndex 知识库更新
- 使用 LlamaIndex 将新文档内容及元数据添加到索引
- 在索引中标记文档所属类别/标签
- 支持高效的文档检索和查询

### 3. 审计日志记录
- 将文件处理结果记录到 SQLite 数据库
- 包含完整的操作信息：文件路径、分类结果、处理时间等
- 支持操作追踪和回滚

### 4. 文件状态管理
- 更新文件状态标记，避免重复处理
- 支持多轮分类和重新分类
- 标记需要人工审核的文件

### 5. 回滚和恢复
- 支持基于操作ID的回滚操作
- 提供完整的审计追踪
- 确保系统状态的一致性

## 架构设计

### 核心组件

```
IndexUpdater
├── DatabaseManager (SQLite)
│   ├── AuditLogger (审计日志)
│   └── StatusTracker (状态跟踪)
├── VectorStoreManager (ChromaDB)
│   └── EmbeddingIndexer (向量索引)
├── LlamaIndexManager (LlamaIndex)
│   └── KnowledgeBaseIndexer (知识库索引)
└── RollbackManager (回滚管理)
    └── OperationTracker (操作追踪)
```

### 数据流

1. **输入阶段**: 接收文件移动结果、文档数据、分类结果
2. **并行处理**: 同时更新向量库、知识库、审计日志
3. **状态同步**: 更新文件状态和系统统计
4. **输出阶段**: 返回操作结果和统计信息

## 配置说明

### 数据库配置

```yaml
database:
  sqlite_path: "data/audit.db"          # SQLite数据库路径
  audit_table: "file_operations"        # 审计日志表名
  status_table: "file_status"           # 文件状态表名
```

### 向量存储配置

```yaml
vector_store:
  chroma_path: "data/chroma_db"         # ChromaDB存储路径
  collection_name: "documents"          # 集合名称
  similarity_threshold: 0.8             # 相似度阈值
  max_results: 10                       # 最大检索结果数
```

### LlamaIndex配置

```yaml
llama_index:
  enable: true                          # 是否启用LlamaIndex
  index_path: "data/llama_index"        # 索引存储路径
  chunk_size: 1000                      # 文档分块大小
  chunk_overlap: 200                    # 分块重叠大小
  similarity_top_k: 5                   # 相似度检索top-k
```

## API 参考

### 主要方法

#### `update_indexes(move_result, document_data, classification_result, processing_time)`

更新所有索引和日志。

**参数:**
- `move_result` (Dict): 文件移动结果
- `document_data` (Dict): 文档数据（包含文本、嵌入向量、元数据）
- `classification_result` (Dict): 分类结果
- `processing_time` (float): 处理时间（秒）

**返回:**
```python
{
    'operation_id': str,           # 操作唯一ID
    'success': bool,               # 整体成功状态
    'results': {                   # 各子操作结果
        'vector_update': {...},
        'llama_update': {...},
        'audit_log': {...},
        'status_update': {...}
    },
    'timestamp': str               # 操作时间戳
}
```

#### `get_audit_records(file_path=None, category=None, limit=100)`

查询审计记录。

**参数:**
- `file_path` (str, optional): 文件路径过滤
- `category` (str, optional): 类别过滤
- `limit` (int): 返回记录数量限制

**返回:** 审计记录列表

#### `get_file_status(file_path)`

获取文件状态。

**参数:**
- `file_path` (str): 文件路径

**返回:** 文件状态字典或None

#### `get_files_needing_review()`

获取需要审核的文件列表。

**返回:** 需要审核的文件列表

#### `get_statistics()`

获取系统统计信息。

**返回:**
```python
{
    'total_operations': int,           # 总操作数
    'successful_operations': int,      # 成功操作数
    'success_rate': float,             # 成功率
    'total_files': int,                # 总文件数
    'files_needing_review': int,       # 需要审核的文件数
    'category_distribution': Dict      # 分类分布
}
```

#### `rollback_operation(operation_id)`

回滚指定操作。

**参数:**
- `operation_id` (str): 操作ID

**返回:** 回滚结果字典

## 使用示例

### 基本使用

```python
from ods.storage.index_updater import IndexUpdater

# 初始化
config = {
    'database': {
        'sqlite_path': 'data/audit.db',
        'audit_table': 'file_operations',
        'status_table': 'file_status'
    },
    'vector_store': {
        'chroma_path': 'data/chroma_db',
        'collection_name': 'documents'
    },
    'llama_index': {
        'enable': True,
        'index_path': 'data/llama_index'
    }
}

index_updater = IndexUpdater(config)

# 更新索引
move_result = {
    'moved': True,
    'original_path': '/path/to/file.pdf',
    'primary_target_path': '/new/path/file.pdf'
}

document_data = {
    'text_content': '文档内容...',
    'embedding': [0.1, 0.2, 0.3, ...],
    'metadata': {'file_type': 'pdf', 'size': 1024}
}

classification_result = {
    'primary_category': '工作',
    'confidence_score': 0.9,
    'tags': ['工作', '项目A']
}

result = index_updater.update_indexes(
    move_result, document_data, classification_result, 1.5
)
```

### 查询审计记录

```python
# 查询所有记录
all_records = index_updater.get_audit_records(limit=50)

# 按类别查询
work_records = index_updater.get_audit_records(category='工作')

# 按文件查询
file_records = index_updater.get_audit_records(
    file_path='/path/to/file.pdf'
)
```

### 文件状态管理

```python
# 获取文件状态
status = index_updater.get_file_status('/path/to/file.pdf')
if status:
    print(f"类别: {status['category']}")
    print(f"状态: {status['status']}")
    print(f"需要审核: {status['needs_review']}")

# 获取需要审核的文件
review_files = index_updater.get_files_needing_review()
for file_info in review_files:
    print(f"需要审核: {file_info['file_path']}")
```

### 统计信息

```python
# 获取系统统计
stats = index_updater.get_statistics()
print(f"总操作数: {stats['total_operations']}")
print(f"成功率: {stats['success_rate']:.2%}")
print(f"分类分布: {stats['category_distribution']}")
```

### 操作回滚

```python
# 回滚操作
rollback_result = index_updater.rollback_operation("operation-id-123")
if rollback_result['success']:
    print("回滚成功")
else:
    print(f"回滚失败: {rollback_result.get('reason', '未知错误')}")
```

## 数据库模式

### 审计日志表 (file_operations)

```sql
CREATE TABLE file_operations (
    id TEXT PRIMARY KEY,                    -- 操作唯一ID
    file_path TEXT NOT NULL,                -- 文件路径
    old_path TEXT,                          -- 原路径
    new_path TEXT,                          -- 新路径
    old_filename TEXT,                      -- 原文件名
    new_filename TEXT,                      -- 新文件名
    category TEXT,                          -- 分类类别
    tags TEXT,                              -- 标签列表 (JSON)
    confidence_score REAL,                  -- 置信度
    rules_applied TEXT,                     -- 应用的规则 (JSON)
    processing_time REAL,                   -- 处理时间
    operator TEXT,                          -- 操作者
    status TEXT,                            -- 操作状态
    error_message TEXT,                     -- 错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 文件状态表 (file_status)

```sql
CREATE TABLE file_status (
    file_path TEXT PRIMARY KEY,             -- 文件路径
    file_hash TEXT,                         -- 文件哈希
    last_modified TIMESTAMP,                -- 最后修改时间
    last_classified TIMESTAMP,              -- 最后分类时间
    category TEXT,                          -- 分类类别
    tags TEXT,                              -- 标签列表 (JSON)
    status TEXT,                            -- 文件状态
    needs_review BOOLEAN DEFAULT FALSE,     -- 是否需要审核
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 错误处理

### 常见错误类型

1. **数据库连接错误**
   - 原因: 数据库文件权限问题或路径不存在
   - 处理: 自动创建数据库目录和文件

2. **向量库更新失败**
   - 原因: ChromaDB服务不可用或嵌入向量缺失
   - 处理: 记录错误并继续其他操作

3. **LlamaIndex更新失败**
   - 原因: 索引损坏或存储空间不足
   - 处理: 禁用LlamaIndex功能并记录警告

4. **文件状态更新失败**
   - 原因: 文件不存在或权限不足
   - 处理: 跳过状态更新并记录错误

### 错误恢复策略

1. **部分失败处理**: 即使某个子操作失败，其他操作仍会继续执行
2. **重试机制**: 对于临时性错误，支持自动重试
3. **降级处理**: 在关键组件不可用时，使用简化模式
4. **错误报告**: 详细的错误信息和上下文记录

## 性能优化

### 批量操作

```python
# 批量更新多个文件
for file_data in file_batch:
    index_updater.update_indexes(
        file_data['move_result'],
        file_data['document_data'],
        file_data['classification_result'],
        file_data['processing_time']
    )
```

### 异步处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_update_indexes(index_updater, file_data_list):
    with ThreadPoolExecutor() as executor:
        tasks = [
            executor.submit(
                index_updater.update_indexes,
                data['move_result'],
                data['document_data'],
                data['classification_result'],
                data['processing_time']
            )
            for data in file_data_list
        ]
        results = await asyncio.gather(*[asyncio.wrap_future(task) for task in tasks])
    return results
```

### 缓存优化

- 数据库连接池复用
- 向量库批量写入
- 索引增量更新

## 监控和维护

### 健康检查

```python
def check_index_updater_health(index_updater):
    """检查索引更新器健康状态"""
    try:
        # 检查数据库连接
        stats = index_updater.get_statistics()
        
        # 检查向量库连接
        # 检查LlamaIndex状态
        
        return {
            'status': 'healthy',
            'database': 'ok',
            'vector_store': 'ok',
            'llama_index': 'ok'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
```

### 定期维护

1. **数据库清理**: 定期清理过期的审计记录
2. **索引重建**: 定期重建LlamaIndex以优化性能
3. **统计更新**: 定期更新系统统计信息
4. **备份恢复**: 定期备份数据库和索引文件

## 扩展点

### 自定义审计处理器

```python
class CustomAuditHandler:
    def handle_audit_record(self, record):
        # 自定义审计记录处理逻辑
        pass

# 集成到IndexUpdater
index_updater.custom_audit_handler = CustomAuditHandler()
```

### 自定义向量存储

```python
class CustomVectorStore:
    def add_document(self, embedding, metadata):
        # 自定义向量存储逻辑
        pass

# 替换默认向量存储
index_updater.vector_store = CustomVectorStore()
```

### 自定义知识库索引

```python
class CustomKnowledgeIndex:
    def add_document(self, document):
        # 自定义知识库索引逻辑
        pass

# 替换默认知识库索引
index_updater.knowledge_index = CustomKnowledgeIndex()
```

## 最佳实践

### 1. 配置管理
- 使用环境变量管理敏感配置
- 定期备份配置文件
- 使用配置验证确保正确性

### 2. 错误处理
- 实现完善的错误日志记录
- 提供有意义的错误消息
- 支持错误恢复和重试

### 3. 性能优化
- 使用批量操作减少数据库访问
- 实现适当的缓存策略
- 监控系统资源使用情况

### 4. 安全性
- 验证输入数据的完整性
- 使用参数化查询防止SQL注入
- 限制数据库访问权限

### 5. 可维护性
- 编写清晰的代码注释
- 实现完整的单元测试
- 提供详细的文档说明

## 故障排除

### 常见问题

1. **数据库锁定错误**
   - 解决方案: 检查是否有其他进程占用数据库文件

2. **向量库性能问题**
   - 解决方案: 调整ChromaDB配置参数，增加内存分配

3. **索引更新缓慢**
   - 解决方案: 使用批量更新，优化数据库索引

4. **内存使用过高**
   - 解决方案: 调整批处理大小，增加垃圾回收频率

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.getLogger('ods.storage.index_updater').setLevel(logging.DEBUG)
   ```

2. **性能分析**
   ```python
   import time
   start_time = time.time()
   result = index_updater.update_indexes(...)
   print(f"耗时: {time.time() - start_time:.2f}秒")
   ```

3. **数据库查询调试**
   ```python
   # 直接查询数据库
   import sqlite3
   conn = sqlite3.connect('data/audit.db')
   cursor = conn.execute("SELECT * FROM file_operations LIMIT 5")
   for row in cursor.fetchall():
       print(row)
   ```

## 总结

索引更新器模块是自动文档分类系统的重要组成部分，提供了完整的索引管理、审计追踪和状态维护功能。通过合理配置和使用，可以确保系统的可靠性、可维护性和可扩展性。
