# Review功能完整文档

## 📋 目录

- [概述](#-概述)
- [功能特性](#-功能特性)
- [架构设计](#-架构设计)
- [核心组件](#-核心组件)
- [使用方法](#-使用方法)
- [测试套件](#-测试套件)
- [API文档](#-api文档)
- [配置说明](#-配置说明)
- [故障排除](#-故障排除)
- [性能优化](#-性能优化)
- [贡献指南](#-贡献指南)

---

## 🎯 概述

Review功能是自动文档分类系统的重要组成部分，为用户提供了智能的文件审核和管理能力。该功能允许用户对系统自动分类的结果进行人工审核、修改和确认，确保分类结果的准确性和可靠性。

### 🎯 主要目标

- **提升分类准确性**: 通过人工审核纠正自动分类的错误
- **用户控制权**: 给予用户对文件分类的最终决定权
- **学习改进**: 记录用户反馈用于改进未来分类
- **操作透明性**: 提供完整的审核历史和统计信息

### 📊 业务价值

- **质量保证**: 确保重要文件的正确分类
- **用户满意度**: 满足用户对分类结果的控制需求
- **系统改进**: 通过用户反馈持续优化分类算法
- **合规要求**: 满足某些行业的审计和合规需求

---

## ✨ 功能特性

### 🔍 核心功能

#### 1. 智能审核队列

- **自动标记**: 系统根据置信度自动标记需要审核的文件
- **优先级排序**: 基于文件重要性、时间等因素进行智能排序
- **批量处理**: 支持批量审核提高效率

#### 2. 交互式审核界面

- **直观显示**: 清晰展示文件信息、当前分类和置信度
- **灵活操作**: 支持批准、修改、拒绝等多种操作
- **实时反馈**: 即时显示操作结果和统计信息

#### 3. 重新分类工作流

- **智能路径规划**: 自动计算新的存储路径
- **文件移动**: 安全地移动文件到新位置
- **索引更新**: 同步更新向量索引和元数据
- **操作回滚**: 支持失败时的自动回滚

#### 4. 审核统计与分析

- **实时统计**: 提供审核会话和操作的详细统计
- **历史记录**: 保存完整的审核历史
- **性能指标**: 跟踪审核效率和准确性

### 🔧 高级特性

#### 批量操作

- **模板应用**: 将审核决策应用到多个相似文件
- **智能推荐**: 基于历史决策推荐分类选项
- **一键应用**: 快速应用预设的分类规则

#### 数据持久化

- **SQLite集成**: 使用本地数据库存储审核数据
- **事务安全**: 保证数据操作的原子性和一致性
- **备份恢复**: 支持审核数据的备份和恢复

#### 扩展性设计

- **插件架构**: 支持自定义审核规则和界面
- **API接口**: 提供RESTful API供第三方集成
- **事件驱动**: 支持审核事件的订阅和处理

---

## 🏗️ 架构设计

### 📦 系统架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Review Manager  │    │   Database      │
│                 │    │                  │    │                 │
│ • review        │◄──►│ • Session Mgmt   │◄──►│ • review_sessions│
│ • review-stats  │    │ • File Queue     │    │ • review_records│
└─────────────────┘    │ • Statistics     │    └─────────────────┘
                       └──────────────────┘             ▲
                              ▲                        │
                              │                        │
                       ┌──────────────────┐           │
                       │ Interactive      │           │
                       │ Reviewer         │           │
                       │                  │           │
                       │ • UI Display     │           │
                       │ • User Input     │           │
                       │ • Decision Logic │           │
                       └──────────────────┘           │
                              ▲                        │
                              │                        │
                       ┌──────────────────┐           │
                       │ Reclassification │           │
                       │ Workflow         │           │
                       │                  │           │
                       │ • Path Planning  │           │
                       │ • File Movement  │           │
                       │ • Index Update   │           │
                       └──────────────────┘           ▼
                                            ┌──────────────────┐
                                            │   File System    │
                                            │   & Index        │
                                            └──────────────────┘
```

### 🔄 数据流图

```
用户输入 → CLI命令 → 审核管理器 → 数据库查询 → 文件队列
    ↓                                              ↓
审核界面 ← 用户决策 ← 决策处理 ← 重新分类 ← 路径规划 ← 文件移动
    ↓                                              ↓
统计更新 → 数据库存储 → 索引更新 → 操作日志 → 用户反馈
```

### 🗂️ 模块结构

```
ods/review/
├── __init__.py                    # 模块初始化
├── review_manager.py             # 审核管理器
├── interactive_reviewer.py       # 交互式审核界面
├── reclassification_workflow.py  # 重新分类工作流
└── __pycache__/                  # 字节码缓存

tests/test_review/
├── __init__.py
├── test_review_manager.py
├── test_interactive_reviewer.py
├── test_reclassification_workflow.py
├── test_database_review.py
├── test_cli_review.py
├── run_review_tests.py
├── test_coverage.py
└── README.md
```

---

## 🔧 核心组件

### 1. ReviewManager (审核管理器)

#### 功能职责

- 管理审核会话的生命周期
- 维护待审核文件的队列
- 计算审核优先级
- 记录审核决策和统计信息

#### 核心方法

```python
class ReviewManager:
    def create_review_session(self, user_id=None) -> str
    def get_files_for_review(self, limit=20) -> List[Dict[str, Any]]
    def record_review_decision(self, session_id, file_id, ...) -> bool
    def get_review_statistics(self, session_id=None) -> Dict[str, Any]
    def end_review_session(self, session_id) -> bool
```

#### 配置参数

```yaml
classification:
  confidence_threshold:
    auto: 0.85      # 自动通过阈值
    review: 0.6     # 需要审核阈值
    min: 0.3        # 最小接受阈值
```

### 2. InteractiveReviewer (交互式审核界面)

#### 功能职责

- 提供命令行用户界面
- 处理用户输入和决策
- 显示文件信息和选项
- 支持批量操作

#### 核心方法

```python
class InteractiveReviewer:
    def start_review_session(self, user_id=None) -> str
    def run_interactive_review(self, session_id, max_files=10, batch_mode=False)
    def get_pending_reviews_count(self) -> int
    def _display_file_info(self, file_info)
    def _get_user_decision(self, file_info) -> Dict[str, Any]
```

#### 用户界面流程

```
显示文件信息 → 展示当前分类 → 获取用户决策 → 处理决策 → 显示结果
     ↓                                                            ↓
批量模式选择 ← 模板应用 ← 决策验证 ← 输入验证 ← 错误处理 ← 退出确认
```

### 3. ReclassificationWorkflow (重新分类工作流)

#### 功能职责

- 执行文件的重新分类
- 计算新的存储路径
- 移动文件到新位置
- 更新相关索引

#### 核心方法

```python
class ReclassificationWorkflow:
    def reclassify_file(self, file_path, new_category, new_tags, user_id=None) -> Dict[str, Any]
    def reclassify_from_review_records(self, session_id) -> Dict[str, Any]
    def _replan_file_path(self, file_path, new_category, new_tags, file_info) -> Optional[Dict[str, Any]]
    def _execute_file_move(self, path_plan, file_info) -> Dict[str, Any]
```

#### 工作流步骤

1. **验证文件**: 检查文件存在性和权限
2. **路径规划**: 计算新的存储路径
3. **冲突检查**: 检查目标位置是否存在冲突
4. **文件移动**: 执行实际的文件移动操作
5. **索引更新**: 更新向量索引和元数据
6. **日志记录**: 记录操作历史

### 4. Database层扩展

#### 新增表结构

```sql
-- 审核会话表
CREATE TABLE review_sessions (
    id INTEGER PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    total_files INTEGER DEFAULT 0,
    reviewed_files INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- 审核记录表
CREATE TABLE review_records (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    original_category TEXT,
    original_tags TEXT,
    original_confidence REAL,
    user_category TEXT,
    user_tags TEXT,
    user_confidence REAL,
    review_action TEXT NOT NULL,
    review_reason TEXT,
    processing_time REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES review_sessions(session_id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
```

#### 数据关系图

```
review_sessions (1) ──── (N) review_records
       │                           │
       │                           │
       └───────────── (1) files ───┘
```

---

## 🚀 使用方法

### 1. 基本使用流程

#### 启动审核会话

```bash
# 启动审核界面
ods review

# 指定用户ID
ods review --user-id john_doe

# 批量审核模式
ods review --batch --max-files 20
```

#### 查看审核统计

```bash
# 查看全局统计
ods review-stats

# 查看特定会话统计
ods review-stats --session-id review_12345678

# 显示详细统计
ods review-stats --detailed
```

### 2. 审核界面操作

#### 文件信息显示

```
📄 文件: /path/to/document.pdf
📏 大小: 2.05 MB
📂 当前分类: 工作
🏷️ 标签: 报告, 重要
🎯 置信度: 0.75
⏰ 分类时间: 2024-01-15 14:30:00
```

#### 用户决策选项

```
请选择操作:
1. ✅ 批准当前分类
2. ✏️  修改分类
3. 🚫 拒绝/标记为问题
4. ⏭️  跳过此文件
5. 🛑 退出审核
```

#### 修改分类流程

```
📝 修改分类
------------------------------
可选的主类别:
1. 工作
2. 个人
3. 财务

选择主类别 (1-3): 3

🏷️ 选择标签 (可多选，输入数字用逗号分隔，输入0结束)
文档类型:
1. 报告
2. 合同
3. 发票

选择标签: 3,0

确认修改分类为: 财务[发票] (y/n): y
```

### 3. 批量操作模式

#### 模板创建

```
📝 选择分类模板
可选的主类别:
1. 工作
2. 个人
3. 财务

选择主类别 (1-3): 1
选择标签: 1,0

模板已创建: 工作[报告]
```

#### 批量应用

```
🔄 批量审核模式
您可以对多个文件应用相同的操作

文件列表:
1. document1.pdf - 工作[报告] (置信度: 0.72)
2. document2.pdf - 工作[合同] (置信度: 0.68)
3. document3.pdf - 个人[日记] (置信度: 0.65)

选择操作:
1. ✅ 全部批准
2. ✏️  应用模板到全部
3. 🔄 逐个处理
4. 🛑 退出批量模式
```

### 4. 高级用法

#### 编程式使用

```python
from ods.review.review_manager import ReviewManager
from ods.review.interactive_reviewer import InteractiveReviewer

# 初始化配置
config = {
    "database": {"path": "data/audit.db"},
    "classification": {
        "taxonomies": {...},
        "confidence_threshold": {...}
    }
}

# 创建审核管理器
manager = ReviewManager(config)

# 创建审核会话
session_id = manager.create_review_session("user123")

# 获取待审核文件
files = manager.get_files_for_review(limit=10)

# 记录审核决策
success = manager.record_review_decision(
    session_id=session_id,
    file_id=files[0]["id"],
    original_category="工作",
    original_tags=["报告"],
    user_category="财务",
    user_tags=["发票"],
    review_action="corrected"
)

# 获取统计信息
stats = manager.get_review_statistics(session_id)
```

#### API集成

```python
from ods.review.reclassification_workflow import ReclassificationWorkflow

# 创建重新分类工作流
workflow = ReclassificationWorkflow(config)

# 重新分类文件
result = workflow.reclassify_file(
    file_path="/path/to/document.pdf",
    new_category="财务",
    new_tags=["发票"],
    user_id="user123"
)

if result["success"]:
    print(f"文件已移动: {result['old_path']} -> {result['new_path']}")
else:
    print(f"重新分类失败: {result['error']}")
```

---

## 🧪 测试套件

### 测试覆盖范围

#### 单元测试文件

| 测试文件 | 目标模块 | 测试数量 | 覆盖率 |
|---------|---------|---------|-------|
| `test_review_manager.py` | ReviewManager | 15+ | 95% |
| `test_interactive_reviewer.py` | InteractiveReviewer | 12+ | 90% |
| `test_reclassification_workflow.py` | ReclassificationWorkflow | 10+ | 92% |
| `test_database_review.py` | Database扩展 | 8+ | 88% |
| `test_cli_review.py` | CLI命令 | 6+ | 85% |

#### 测试类型分布

- **功能测试**: 验证核心业务逻辑 (60%)
- **边界测试**: 测试极限条件和异常输入 (20%)
- **错误测试**: 验证错误处理和恢复机制 (15%)
- **集成测试**: 测试组件间交互 (5%)

### 运行测试

#### 基础运行

```bash
# 运行所有Review测试
python tests/test_review/run_review_tests.py

# 运行特定测试类
python tests/test_review/run_review_tests.py ReviewManager

# 运行特定测试方法
python tests/test_review/run_review_tests.py ReviewManager test_create_review_session
```

#### 高级选项

```bash
# 生成测试报告
python -m pytest tests/test_review/ --html=report.html --self-contained-html

# 运行覆盖率分析
python tests/test_review/test_coverage.py

# 运行性能测试
python -m pytest tests/test_review/ --durations=10
```

### 测试质量指标

#### 代码覆盖率目标

```yaml
coverage_targets:
  ReviewManager: 95%
  InteractiveReviewer: 90%
  ReclassificationWorkflow: 92%
  Database扩展: 88%
  CLI命令: 85%
  整体覆盖率: 90%
```

#### 性能基准

```yaml
performance_baselines:
  test_execution_time: "< 30秒"
  memory_usage: "< 100MB"
  database_operations: "< 100次/测试"
```

---

## 📚 API文档

### ReviewManager API

#### `create_review_session(user_id=None) -> str`

创建新的审核会话。

**参数:**

- `user_id` (str, optional): 用户ID

**返回值:**

- `str`: 唯一会话ID，格式为 `review_xxxxxxxx`

**示例:**

```python
session_id = manager.create_review_session("user123")
# 返回: "review_a1b2c3d4"
```

#### `get_files_for_review(limit=20) -> List[Dict[str, Any]]`

获取待审核文件列表。

**参数:**

- `limit` (int): 最大返回文件数量，默认20

**返回值:**

- `List[Dict[str, Any]]`: 文件信息字典列表

**文件信息结构:**

```python
{
    "id": 1,
    "file_path": "/path/to/file.pdf",
    "category": "工作",
    "tags": ["报告"],
    "last_classified": "2024-01-15T10:30:00",
    "file_size": 2048000,
    "file_extension": ".pdf",
    "review_priority": 2.5
}
```

#### `record_review_decision(...) -> bool`

记录审核决策。

**参数:**

- `session_id` (str): 会话ID
- `file_id` (int): 文件ID
- `original_category` (str): 原始分类
- `original_tags` (List[str]): 原始标签
- `user_category` (str): 用户选择的分类
- `user_tags` (List[str]): 用户选择的标签
- `review_action` (str): 审核动作 ('approved', 'corrected', 'rejected')
- `review_reason` (str, optional): 审核理由
- `processing_time` (float, optional): 处理时间

**返回值:**

- `bool`: 操作是否成功

### InteractiveReviewer API

#### `run_interactive_review(session_id, max_files=10, batch_mode=False)`

运行交互式审核流程。

**参数:**

- `session_id` (str): 审核会话ID
- `max_files` (int): 最大审核文件数量
- `batch_mode` (bool): 是否启用批量模式

**交互流程:**

1. 显示欢迎信息和会话统计
2. 逐个或批量处理文件
3. 获取用户决策
4. 执行重新分类（如果需要）
5. 显示操作结果和统计

### ReclassificationWorkflow API

#### `reclassify_file(file_path, new_category, new_tags, user_id=None) -> Dict[str, Any]`

重新分类单个文件。

**参数:**

- `file_path` (str): 文件路径
- `new_category` (str): 新分类
- `new_tags` (List[str]): 新标签列表
- `user_id` (str, optional): 用户ID

**返回值:**

```python
{
    "success": True,
    "file_path": "/path/to/file.pdf",
    "old_category": "工作",
    "new_category": "财务",
    "old_tags": ["报告"],
    "new_tags": ["发票"],
    "path_changed": True,
    "old_path": "/old/path/file.pdf",
    "new_path": "/new/path/file.pdf",
    "processing_time": 1.23
}
```

#### `reclassify_from_review_records(session_id) -> Dict[str, Any]`

根据审核记录批量重新分类。

**参数:**

- `session_id` (str): 审核会话ID

**返回值:**

```python
{
    "success": True,
    "total_files": 5,
    "successful_reclassifications": 4,
    "failed_reclassifications": 1,
    "results": [...]  # 详细结果列表
}
```

---

## ⚙️ 配置说明

### 核心配置

#### 分类配置

```yaml
classification:
  # 置信度阈值
  confidence_threshold:
    auto: 0.85      # 自动通过阈值
    review: 0.6     # 需要审核阈值
    min: 0.3        # 最小接受阈值

  # 标签规则
  tag_rules:
    max_tags_per_file: 5
    primary_tag_required: true

  # 分类体系
  taxonomies:
    主类别:
      工作: []
      个人: []
      财务: []
    文档类型:
      报告: []
      合同: []
      发票: []
```

#### 数据库配置

```yaml
database:
  path: "data/audit.db"  # 数据库文件路径
  backup_enabled: true   # 是否启用备份
  backup_interval: 24    # 备份间隔（小时）
```

#### Review功能配置

```yaml
review:
  # 会话配置
  session:
    max_files_per_session: 100    # 单个会话最大文件数
    session_timeout: 3600         # 会话超时时间（秒）
    auto_save_interval: 60        # 自动保存间隔（秒）

  # 界面配置
  interface:
    show_file_preview: true       # 显示文件预览
    show_confidence_score: true   # 显示置信度分数
    enable_batch_mode: true       # 启用批量模式

  # 性能配置
  performance:
    max_concurrent_operations: 3  # 最大并发操作数
    operation_timeout: 300        # 操作超时时间（秒）
```

### 环境变量

```bash
# 数据库配置
export ODS_DATABASE_PATH="data/audit.db"

# 日志配置
export ODS_LOG_LEVEL="INFO"
export ODS_LOG_FILE="logs/review.log"

# 性能配置
export ODS_MAX_WORKERS="4"
export ODS_MEMORY_LIMIT="512MB"
```

### 配置文件位置

1. **全局配置**: `~/.ods/config.yaml`
2. **项目配置**: `config/config.yaml`
3. **用户配置**: `config/user_config.yaml`
4. **环境配置**: 通过环境变量覆盖

---

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接问题

**问题**: `Database connection failed`

**解决方案**:

```bash
# 检查数据库文件权限
ls -la data/audit.db

# 修复权限
chmod 644 data/audit.db

# 检查磁盘空间
df -h

# 重建数据库
ods init --force
```

#### 2. 审核会话无法创建

**问题**: `Failed to create review session`

**原因**:

- 数据库空间不足
- 并发访问冲突
- 配置错误

**解决方案**:

```python
# 检查数据库状态
from ods.core.database import Database
db = Database(config)
db.check_health()

# 清理过期会话
db.cleanup_expired_sessions()

# 检查配置
import yaml
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)
print(config['database'])
```

#### 3. 文件移动失败

**问题**: `File movement failed: Permission denied`

**解决方案**:

```bash
# 检查文件权限
ls -la /path/to/file.pdf

# 检查目标目录权限
ls -ld /target/directory/

# 修复权限
chmod 755 /target/directory/
chmod 644 /path/to/file.pdf

# 检查磁盘配额
quota -v
```

#### 4. 审核界面显示异常

**问题**: `Unicode encoding error in review interface`

**解决方案**:

```bash
# 设置正确的编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# 检查终端支持
locale -a | grep UTF-8

# 更新系统编码
sudo locale-gen en_US.UTF-8
sudo update-locale LANG=en_US.UTF-8
```

### 性能问题

#### 慢查询优化

```python
# 启用查询分析
import sqlite3
conn = sqlite3.connect('data/audit.db')
conn.execute('PRAGMA query_only = ON;')

# 分析慢查询
cursor = conn.cursor()
cursor.execute('EXPLAIN QUERY PLAN SELECT * FROM review_records WHERE session_id = ?', ('session_123',))
print(cursor.fetchall())
```

#### 内存优化

```python
# 监控内存使用
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

# 启用垃圾回收
import gc
gc.collect()
```

### 日志分析

#### 查看错误日志

```bash
# 查看最近的错误
tail -f logs/review.log | grep ERROR

# 分析错误模式
grep "ERROR" logs/review.log | cut -d' ' -f1 | sort | uniq -c | sort -nr

# 查看特定会话的日志
grep "session_12345678" logs/review.log
```

#### 调试模式

```python
import logging

# 启用调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debug.log'),
        logging.StreamHandler()
    ]
)

# 跟踪特定操作
logger = logging.getLogger('ods.review')
logger.debug("Starting review session creation")
```

---

## ⚡ 性能优化

### 数据库优化

#### 索引优化

```sql
-- 创建复合索引
CREATE INDEX idx_review_records_session_file
ON review_records (session_id, file_id);

-- 创建时间索引
CREATE INDEX idx_review_sessions_start_time
ON review_sessions (start_time);

-- 优化查询性能
CREATE INDEX idx_files_category_tags
ON files (category, tags);
```

#### 查询优化

```python
# 使用参数化查询
def get_files_by_category(self, category, limit=100):
    query = """
    SELECT * FROM files
    WHERE category = ?
    ORDER BY last_modified DESC
    LIMIT ?
    """
    return self.execute_query(query, (category, limit))

# 使用批量操作
def bulk_update_files(self, updates):
    with self.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            UPDATE files
            SET category = ?, tags = ?
            WHERE id = ?
        """, updates)
        conn.commit()
```

### 内存优化

#### 大文件处理

```python
def process_large_file(self, file_path):
    """处理大文件的优化策略"""
    file_size = os.path.getsize(file_path)

    if file_size > 100 * 1024 * 1024:  # 100MB
        # 使用流式处理
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                self.process_chunk(chunk)
    else:
        # 直接处理
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.process_content(content)
```

#### 缓存策略

```python
from functools import lru_cache
import pickle

class ReviewCache:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self._cache = {}

    @lru_cache(maxsize=100)
    def get_file_info(self, file_path):
        """缓存文件信息"""
        if file_path in self._cache:
            return self._cache[file_path]

        info = self._get_file_info_from_db(file_path)
        self._cache[file_path] = info
        return info

    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
        self.get_file_info.cache_clear()
```

### 并发优化

#### 异步处理

```python
import asyncio
import aiofiles

async def process_files_async(self, file_paths):
    """异步处理多个文件"""
    tasks = []
    for file_path in file_paths:
        task = asyncio.create_task(self.process_single_file(file_path))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def process_single_file(self, file_path):
    """处理单个文件的异步版本"""
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
        return await self.analyze_content_async(content)
```

#### 线程池优化

```python
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class ReviewProcessor:
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.executor = ThreadPoolExecutor(max_workers=self.cpu_count)

    def process_batch(self, files):
        """批量处理文件"""
        futures = []
        for file_info in files:
            future = self.executor.submit(self.process_file, file_info)
            futures.append(future)

        results = []
        for future in futures:
            try:
                result = future.result(timeout=300)  # 5分钟超时
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        return results
```

### 监控和调优

#### 性能监控

```python
import time
from contextlib import contextmanager

@contextmanager
def performance_monitor(operation_name):
    """性能监控上下文管理器"""
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss

    try:
        yield
    finally:
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        duration = end_time - start_time
        memory_delta = end_memory - start_memory

        logger.info(f"{operation_name} completed in {duration:.2f}s, "
                   f"memory delta: {memory_delta / 1024 / 1024:.2f}MB")

# 使用示例
with performance_monitor("file_reclassification"):
    workflow.reclassify_file(file_path, new_category, new_tags)
```

#### 自动调优

```python
class PerformanceTuner:
    def __init__(self):
        self.metrics = {}

    def tune_batch_size(self):
        """自动调整批处理大小"""
        system_memory = psutil.virtual_memory().available
        cpu_count = multiprocessing.cpu_count()

        # 根据系统资源调整批处理大小
        if system_memory > 8 * 1024 * 1024 * 1024:  # 8GB
            return min(100, cpu_count * 10)
        elif system_memory > 4 * 1024 * 1024 * 1024:  # 4GB
            return min(50, cpu_count * 5)
        else:
            return min(20, cpu_count * 2)

    def optimize_query(self, query_type):
        """优化查询策略"""
        if query_type == "large_dataset":
            return {
                "use_index": True,
                "batch_size": self.tune_batch_size(),
                "cache_results": True
            }
        elif query_type == "real_time":
            return {
                "use_index": False,
                "batch_size": 1,
                "cache_results": False
            }
```

---

## 🤝 贡献指南

### 开发环境设置

#### 环境要求

```yaml
python: ">=3.8"
dependencies:
  - pytest>=7.0.0
  - pytest-cov>=4.0.0
  - black>=22.0.0
  - flake8>=5.0.0
  - mypy>=1.0.0
```

#### 安装开发环境

```bash
# 克隆项目
git clone https://github.com/your-org/auto-file-classification.git
cd auto-file-classification

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .
pip install -r requirements-dev.txt

# 安装预提交钩子
pre-commit install
```

### 代码规范

#### 代码风格

```python
# 使用Black格式化代码
black ods/review/ tests/test_review/

# 使用Flake8检查代码质量
flake8 ods/review/ tests/test_review/

# 使用MyPy进行类型检查
mypy ods/review/ tests/test_review/
```

#### 命名约定

```python
# 类名：PascalCase
class ReviewManager:
    pass

# 方法名：snake_case
def create_review_session(self, user_id=None):
    pass

# 常量：UPPER_SNAKE_CASE
MAX_FILES_PER_SESSION = 100

# 私有方法：以单下划线开头
def _calculate_priority(self, file_info):
    pass
```

### 开发流程

#### 1. 创建功能分支

```bash
# 创建功能分支
git checkout -b feature/enhanced-review-ui

# 定期同步主分支
git fetch origin
git rebase origin/main
```

#### 2. 编写代码

```python
# 实现新功能
def enhanced_review_display(self, file_info):
    """增强的审核显示功能"""
    # 实现代码
    pass

# 添加相应的测试
def test_enhanced_review_display(self):
    """测试增强的审核显示"""
    # 测试代码
    pass
```

#### 3. 编写测试

```python
import unittest
from unittest.mock import Mock, patch

class TestEnhancedReviewDisplay(unittest.TestCase):
    def setUp(self):
        self.reviewer = InteractiveReviewer(config)

    def test_display_with_preview(self):
        """测试带预览的显示功能"""
        file_info = {
            "file_path": "/test/document.pdf",
            "content_preview": "This is a test document...",
            "category": "工作"
        }

        with patch("builtins.print") as mock_print:
            self.reviewer.enhanced_review_display(file_info)

        # 验证预览内容被显示
        calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("预览" in call for call in calls))
```

#### 4. 运行测试

```bash
# 运行所有测试
python tests/test_review/run_review_tests.py

# 运行特定测试
python tests/test_review/run_review_tests.py ReviewManager

# 生成覆盖率报告
python -m pytest tests/test_review/ --cov=ods.review --cov-report=html
```

#### 5. 提交代码

```bash
# 添加文件
git add .

# 提交更改
git commit -m "feat: 添加增强的审核显示功能

- 新增enhanced_review_display方法
- 支持文件内容预览
- 添加相应的单元测试
- 更新文档"

# 推送分支
git push origin feature/enhanced-review-ui
```

### 测试策略

#### 单元测试原则

1. **单一职责**: 每个测试只验证一个功能点
2. **独立性**: 测试之间相互独立，不依赖执行顺序
3. **可重复性**: 测试结果稳定，不受外部环境影响
4. **快速执行**: 测试运行时间控制在合理范围内

#### 测试覆盖要求

- **核心业务逻辑**: >95%
- **错误处理路径**: >90%
- **边界条件**: >85%
- **用户界面**: >80%

#### Mock使用指南

```python
# 正确的Mock使用
@patch('ods.review.review_manager.Database')
def test_review_manager_init(self, mock_db_class):
    """测试ReviewManager初始化"""
    mock_db_instance = Mock()
    mock_db_class.return_value = mock_db_instance

    manager = ReviewManager(self.config)

    # 验证类被正确实例化
    mock_db_class.assert_called_once_with(self.config)
    self.assertEqual(manager.database, mock_db_instance)

# 避免过度Mock
def test_review_decision_logic(self):
    """测试审核决策逻辑（使用真实对象）"""
    manager = ReviewManager(self.config)

    # 只mock外部依赖
    with patch.object(manager, '_get_file_path_by_id', return_value='/test/file.pdf'):
        result = manager.record_review_decision(...)

    # 验证业务逻辑
    self.assertTrue(result)
```

### 文档更新

#### 更新API文档

```python
def enhanced_review_display(self, file_info, show_preview=True):
    """
    增强的审核显示功能。

    Args:
        file_info (dict): 文件信息字典
        show_preview (bool): 是否显示内容预览

    Returns:
        None

    Raises:
        ValueError: 当file_info格式不正确时

    Example:
        >>> reviewer.enhanced_review_display(file_info)
        📄 文件: /path/to/document.pdf
        📝 预览: This is the content preview...
        📂 分类: 工作
    """
    if not isinstance(file_info, dict):
        raise ValueError("file_info must be a dictionary")

    # 实现代码
    pass
```

#### 更新用户文档

```markdown
### 增强的审核显示

新版本的审核界面现在支持文件内容预览功能：

```bash
ods review --preview
```

此功能可以：

- 显示文件的前几行内容
- 高亮显示关键信息
- 支持不同文件格式的预览

```

### 代码审查清单

#### 功能实现

- [ ] 功能需求是否完全实现
- [ ] 代码是否遵循项目规范
- [ ] 是否有足够的错误处理
- [ ] 性能是否满足要求

#### 测试覆盖

- [ ] 单元测试覆盖率 >90%
- [ ] 边界条件测试完整
- [ ] 错误场景测试充分
- [ ] 集成测试通过

#### 文档更新

- [ ] API文档更新
- [ ] 用户文档更新
- [ ] 代码注释完整
- [ ] 变更日志更新

#### 兼容性

- [ ] 向后兼容性检查
- [ ] 依赖版本兼容
- [ ] 数据库迁移脚本
- [ ] 配置兼容性

### 发布流程

#### 1. 版本管理

```bash
# 更新版本号
# 编辑 setup.py 或 pyproject.toml
version = "1.2.0"

# 更新变更日志
# 编辑 CHANGELOG.md
## [1.2.0] - 2024-01-15
### 新增
- 增强的审核显示功能
- 文件内容预览支持
### 修复
- 修复审核界面编码问题
```

#### 2. 发布准备

```bash
# 运行完整测试套件
python tests/test_review/run_review_tests.py
python -m pytest tests/ --cov --cov-report=html

# 构建文档
cd docs
make html

# 检查代码质量
black --check .
flake8 .
mypy .
```

#### 3. 创建发布

```bash
# 创建发布标签
git tag -a v1.2.0 -m "Release version 1.2.0"

# 推送标签
git push origin v1.2.0

# 创建GitHub Release
# 在GitHub界面创建Release，附上变更日志
```

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- **项目主页**: <https://github.com/your-org/auto-file-classification>
- **问题反馈**: <https://github.com/your-org/auto-file-classification/issues>
- **邮件列表**: <project-maintainers@example.com>
- **文档站点**: <https://docs.example.com/auto-file-classification/>

---

*最后更新: 2024-01-15* | *版本: 1.1.0* | *维护者: AI Assistant*
