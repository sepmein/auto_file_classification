# 文件审核功能文档

## 概述

Phase 2 实现了完整的文件审核功能，允许用户对自动分类结果进行人工审核和修正。该功能包括：

- 交互式审核界面
- 批量审核操作
- 审核会话管理
- 重新分类工作流
- 审核统计和报告

## 功能特性

### 1. 自动审核触发

当系统对文件分类的置信度低于阈值时，会自动标记文件为"需要审核"状态：

```bash
# 运行文件分类
ods apply

# 系统会显示需要审核的文件数量
📊 处理结果:
总文件数: 25
成功处理: 20
需要审核: 5  # 这5个文件需要人工审核
处理失败: 0

⚠️  有 5 个文件需要人工审核
💡 使用 'ods review' 命令处理这些文件
```

### 2. 交互式审核界面

#### 单文件审核模式（默认）

```bash
# 启动审核界面
ods review

# 或指定最大审核文件数
ods review --max-files 20

# 或指定用户ID
ods review --user-id john_doe
```

审核界面会显示：

- 文件基本信息（名称、大小、当前分类）
- 审核优先级（⭐ 高 ⚠️ 中 📝 低）
- 交互式操作菜单

#### 批量审核模式

```bash
# 启用批量审核模式
ods review --batch

# 批量模式支持：
# - 批量批准所有文件
# - 批量拒绝所有文件
# - 应用分类模板到多个文件
# - 切换到逐个审核
```

### 3. 审核操作选项

#### 单文件审核

```
📄 文件 1/5
==================================================
📁 文件: report.pdf
📊 大小: 2.34 MB
🏷️  当前分类: 其他
🕒 分类时间: 2024-01-15 14:30:00
⭐ 优先级: 高 (2.8)

请选择操作:
1. ✅ 批准当前分类
2. ✏️  修改分类
3. 🚫 拒绝/标记为问题
4. ⏭️  跳过此文件
5. 🛑 退出审核
```

#### 批量审核

```
批量操作选项:
1. ✅ 批量批准所有文件（保持当前分类）
2. 🚫 批量拒绝所有文件
3. 📝 应用分类模板
4. 🔄 切换到逐个审核模式
5. ❌ 取消批量审核
```

### 4. 审核统计

查看审核会话统计：

```bash
# 查看全局审核统计
ods review-stats

# 查看特定会话的统计
ods review-stats --session-id review_12345678

# 显示详细统计信息
ods review-stats --detailed
```

### 5. 重新分类工作流

当用户修改分类时，系统会自动：

1. 更新数据库中的分类结果
2. 重新规划文件路径
3. 移动文件到新位置（如果需要）
4. 更新向量索引和LlamaIndex
5. 记录重新分类操作

## 配置说明

### 审核阈值配置

在 `config/rules.yaml` 中配置审核阈值：

```yaml
classification:
  confidence_threshold:
    auto: 0.85      # 自动分类阈值
    review: 0.6     # 需要审核的阈值
    min: 0.3        # 最低置信度
```

### 标签体系配置

配置多标签体系：

```yaml
classification:
  taxonomies:
    主类别:
      - "工作"
      - "个人"
      - "财务"
      - "其他"
    文档类型:
      - "报告"
      - "合同"
      - "发票"
      - "照片"
    敏感级别:
      - "公开"
      - "内部"
      - "机密"
```

## 数据库表结构

### review_sessions 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| session_id | TEXT | 会话唯一标识 |
| user_id | TEXT | 用户ID |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| total_files | INTEGER | 总文件数 |
| reviewed_files | INTEGER | 已审核文件数 |
| status | TEXT | 会话状态 |

### review_records 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| session_id | TEXT | 会话ID |
| file_id | INTEGER | 文件ID |
| original_category | TEXT | 原始分类 |
| original_tags | TEXT | 原始标签 |
| user_category | TEXT | 用户选择分类 |
| user_tags | TEXT | 用户选择标签 |
| review_action | TEXT | 审核动作 |
| review_reason | TEXT | 审核理由 |
| processing_time | REAL | 处理时间 |

## 使用示例

### 基本审核流程

```bash
# 1. 运行文件分类
ods apply

# 2. 如果有需要审核的文件，启动审核界面
ods review

# 3. 在审核界面中选择操作
# 选择 2 修改分类，然后按照提示选择新的分类

# 4. 系统会自动重新分类并移动文件
✅ 重新分类完成!
📁 文件已移动: old/path/file.pdf -> new/path/file.pdf

# 5. 查看审核统计
ods review-stats
```

### 批量审核示例

```bash
# 启用批量审核模式
ods review --batch --max-files 50

# 在批量界面中选择应用模板
# 系统会显示可选的分类模板
# 选择模板后应用到所有文件

📊 批量处理完成: 45/50 个文件
✅ 已处理: report_Q1.pdf
✅ 已处理: contract_001.docx
...
```

### 高级配置示例

```yaml
# rules.yaml 中的高级配置
classification:
  taxonomies:
    主类别: ["工作", "个人", "财务"]
    文档类型: ["报告", "合同", "发票"]
    敏感级别: ["公开", "内部", "机密"]

  confidence_threshold:
    auto: 0.9      # 高置信度自动处理
    review: 0.7    # 中等置信度需要审核
    min: 0.5       # 低置信度标记为不确定

rules:
  pre_classification:
    - name: "高优先级文件"
      condition: "file_extension"
      value: ["pdf", "docx"]
      action: "set_confidence"
      target: "0.9"  # 提高PDF和Word文件的置信度

  post_classification:
    - name: "机密文件审核"
      condition: "tags_contain"
      value: "机密"
      action: "require_review"
```

## 注意事项

### 1. 权限要求

- 确保用户有读写文件系统的权限
- 审核过程中会修改文件位置，请备份重要文件

### 2. 性能考虑

- 大量文件审核时建议使用批量模式
- 审核会话会保存在数据库中，可随时查询

### 3. 数据一致性

- 系统会自动维护文件状态和数据库的一致性
- 审核操作都会记录到操作日志中

### 4. 错误处理

- 如果审核过程中出现错误，系统会记录错误信息
- 可以查看日志文件获取详细信息
- 审核操作支持回滚（通过数据库记录）

## 故障排除

### 常见问题

1. **无法启动审核界面**
   - 检查 Python 环境和依赖包
   - 确认数据库连接正常

2. **审核统计显示异常**
   - 检查数据库表结构是否正确
   - 确认审核会话ID格式

3. **文件重新分类失败**
   - 检查文件权限
   - 确认目标路径存在且可写

### 日志位置

审核相关的日志保存在：

- 主日志：`.ods/ods.log`
- 数据库操作日志：通过 `ods review-stats` 查看

## 扩展功能

### 自定义审核规则

可以通过修改 `config/rules.yaml` 中的规则来自定义审核行为：

```yaml
rules:
  pre_classification:
    - name: "重要文件优先审核"
      condition: "filename_contains"
      value: "重要"
      action: "require_review"
```

### 集成到自动化流程

审核功能可以集成到 CI/CD 流程中：

```bash
#!/bin/bash
# 自动分类和审核脚本

ods apply
if [ $(ods review-stats | grep "pending_reviews" | cut -d: -f2) -gt 0 ]; then
    echo "有文件需要审核，请运行: ods review"
    exit 1
fi
echo "所有文件已自动分类完成"
```

这个文档提供了完整的使用指南，帮助用户充分利用 Phase 2 的审核功能。
