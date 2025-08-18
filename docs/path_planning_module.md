# 路径规划模块 (PathPlanner)

## 概述

路径规划模块是自动文档分类系统的核心组件之一，负责根据分类结果和配置规则为文件确定合适的存储路径。该模块支持多标签分类、路径冲突处理、目录结构创建等功能。

## 功能特性

### 核心功能
- **智能路径规划**: 根据分类结果自动确定文件存储路径
- **多标签支持**: 处理一个文件属于多个类别的情况
- **路径冲突处理**: 自动检测和解决文件路径冲突
- **目录结构创建**: 自动创建必要的目录结构
- **模板化路径**: 支持使用模板定义路径结构
- **特殊路径处理**: 处理未分类、待审核等特殊情况的路径

### 高级功能
- **路径长度限制**: 确保路径长度符合系统限制
- **类别映射**: 支持自定义类别到路径的映射规则
- **路径验证**: 验证生成的路径规划结果
- **统计信息**: 提供路径规划的统计信息

## 架构设计

### 类结构
```
PathPlanner
├── 配置管理
│   ├── 基础路径配置
│   ├── 类别映射配置
│   ├── 特殊路径配置
│   └── 冲突解决配置
├── 路径规划
│   ├── 主路径确定
│   ├── 链接路径规划
│   ├── 模板变量处理
│   └── 路径模板应用
├── 冲突处理
│   ├── 路径冲突检测
│   ├── 后缀冲突解决
│   ├── 时间戳冲突解决
│   └── 长路径处理
└── 辅助功能
    ├── 目录结构创建
    ├── 路径验证
    └── 统计信息
```

### 工作流程
1. **接收输入**: 分类结果、原始路径、文件元数据
2. **路径规划**: 根据分类结果确定主存储路径
3. **多标签处理**: 为次要标签创建链接路径
4. **冲突检查**: 检测并解决路径冲突
5. **结果输出**: 返回完整的路径规划结果

## 配置说明

### 基础配置
```yaml
path_planning:
  base_path: "OneDrive/分类"                    # 基础路径
  default_categories: ["工作", "个人", "财务", "其他"]  # 默认类别
  multi_label_strategy: "primary_with_links"    # 多标签策略
  path_template: "{category}/{year}/{month}"    # 路径模板
  conflict_resolution: "suffix"                 # 冲突解决方式
  max_path_length: 260                          # 最大路径长度
```

### 类别映射配置
```yaml
# config/category_mapping.yaml
工作: "工作文档"
个人: "个人文档"
财务: "财务文档"
项目A: "项目/项目A"
客户A: "客户/客户A"
```

### 特殊路径配置
```yaml
special_paths:
  uncategorized: "待整理"
  needs_review: "待审核"
  important: "重要文件"
  archive: "归档"
```

## API 参考

### 主要方法

#### `plan_file_path(classification_result, original_path, file_metadata)`
规划文件路径的主要方法。

**参数:**
- `classification_result` (Dict): 分类结果
  - `primary_category` (str): 主类别
  - `confidence_score` (float): 置信度
  - `tags` (List[str]): 标签列表
- `original_path` (str): 原始文件路径
- `file_metadata` (Dict): 文件元数据

**返回:**
- `Dict`: 路径规划结果
  ```python
  {
      'original_path': str,
      'primary_path': str,
      'link_paths': List[Dict],
      'conflict_info': Dict,
      'category': str,
      'tags': List[str],
      'confidence_score': float,
      'planning_time': str,
      'status': str
  }
  ```

#### `create_directory_structure(path_plan)`
创建目录结构。

**参数:**
- `path_plan` (Dict): 路径规划结果

**返回:**
- `bool`: 创建是否成功

#### `validate_path_plan(path_plan)`
验证路径规划结果。

**参数:**
- `path_plan` (Dict): 路径规划结果

**返回:**
- `Dict`: 验证结果
  ```python
  {
      'is_valid': bool,
      'errors': List[str],
      'warnings': List[str]
  }
  ```

### 内部方法

#### `_determine_primary_path(category, original_path, metadata)`
确定主存储路径。

#### `_plan_link_paths(tags, primary_category, primary_path)`
规划链接路径（多标签情况）。

#### `_check_path_conflicts(target_path, original_path)`
检查路径冲突。

#### `_resolve_conflict_with_suffix(path)`
通过添加后缀解决冲突。

#### `_resolve_conflict_with_timestamp(path)`
通过添加时间戳解决冲突。

## 使用示例

### 基本使用
```python
from ods.path_planner.path_planner import PathPlanner

# 创建路径规划器
config = {
    'path_planning': {
        'base_path': 'OneDrive/分类',
        'default_categories': ['工作', '个人', '财务', '其他'],
        'path_template': '{category}/{year}/{month}'
    }
}
planner = PathPlanner(config)

# 规划文件路径
classification_result = {
    'primary_category': '工作',
    'confidence_score': 0.9,
    'tags': ['工作', '项目A']
}

path_plan = planner.plan_file_path(
    classification_result,
    '/documents/项目计划书.pdf',
    {'file_size': 1024000, 'author': '张三'}
)

print(f"主路径: {path_plan['primary_path']}")
print(f"链接路径: {path_plan['link_paths']}")
```

### 多标签处理
```python
# 处理多标签情况
classification_result = {
    'primary_category': '工作',
    'confidence_score': 0.9,
    'tags': ['工作', '项目A', '重要']
}

path_plan = planner.plan_file_path(
    classification_result,
    '/documents/重要项目文档.pdf',
    {}
)

# 主文件存储在 '工作' 类别下
# 在 '项目A' 和 '重要' 类别下创建软链接
for link_info in path_plan['link_paths']:
    print(f"链接: {link_info['link_path']} -> {link_info['source_path']}")
```

### 冲突处理
```python
# 检查冲突信息
if path_plan['conflict_info']['has_conflict']:
    print(f"冲突类型: {path_plan['conflict_info']['conflict_type']}")
    print(f"解决方式: {path_plan['conflict_info']['resolution']}")
    print(f"建议路径: {path_plan['conflict_info']['suggested_path']}")
```

## 路径模板

### 模板变量
- `{category}`: 文件类别
- `{year}`: 年份
- `{month}`: 月份
- `{day}`: 日期
- `{date}`: 日期（YYYYMMDD格式）
- `{timestamp}`: 时间戳
- 自定义元数据变量

### 模板示例
```yaml
# 按类别和日期组织
path_template: "{category}/{year}/{month}"

# 按类别和作者组织
path_template: "{category}/{author}"

# 按类别、项目和日期组织
path_template: "{category}/{project}/{year}/{month}"
```

## 冲突解决策略

### 后缀策略
当文件已存在时，在文件名后添加数字后缀：
- `document.pdf` → `document_1.pdf`
- `document_1.pdf` → `document_2.pdf`

### 时间戳策略
当文件已存在时，在文件名中添加时间戳：
- `document.pdf` → `document_143022.pdf`

### 长路径处理
当路径超过系统限制时，自动截断文件名：
- 保留扩展名
- 截断文件名部分
- 确保路径长度在限制内

## 错误处理

### 常见错误
1. **路径过长**: 自动截断处理
2. **权限不足**: 记录错误并返回错误状态
3. **磁盘空间不足**: 记录错误并返回错误状态
4. **无效路径**: 验证失败并返回错误信息

### 错误状态
- `planned`: 规划成功
- `needs_review`: 需要人工审核
- `error`: 发生错误

## 性能优化

### 优化策略
1. **缓存类别映射**: 避免重复读取配置文件
2. **批量目录创建**: 一次性创建多个目录
3. **路径验证优化**: 减少不必要的文件系统操作
4. **模板预编译**: 预编译常用的路径模板

### 性能指标
- 路径规划时间: < 10ms
- 目录创建时间: < 100ms
- 内存使用: < 10MB

## 测试

### 单元测试
```bash
# 运行路径规划器测试
pytest tests/test_path_planner.py -v
```

### 测试覆盖
- 基本路径规划功能
- 多标签处理
- 冲突解决
- 路径验证
- 错误处理

## 扩展点

### 自定义路径策略
可以通过继承 `PathPlanner` 类来实现自定义的路径规划策略：

```python
class CustomPathPlanner(PathPlanner):
    def _determine_primary_path(self, category, original_path, metadata):
        # 自定义路径确定逻辑
        pass
```

### 自定义冲突解决
可以实现自定义的冲突解决策略：

```python
def custom_conflict_resolution(self, path):
    # 自定义冲突解决逻辑
    pass
```

## 最佳实践

### 配置建议
1. **合理设置基础路径**: 确保路径符合系统规范
2. **配置类别映射**: 为常用类别设置明确的路径映射
3. **设置路径模板**: 使用有意义的路径结构
4. **配置冲突解决**: 选择合适的冲突解决策略

### 使用建议
1. **定期验证路径**: 定期检查生成的路径是否合理
2. **监控冲突情况**: 关注路径冲突的频率和类型
3. **优化模板设计**: 根据实际使用情况优化路径模板
4. **备份重要配置**: 定期备份类别映射和配置信息

## 故障排除

### 常见问题

#### 路径创建失败
**问题**: 无法创建目录结构
**解决**: 检查权限设置和磁盘空间

#### 路径过长
**问题**: 生成的路径超过系统限制
**解决**: 调整路径模板或增加路径长度限制

#### 类别映射不生效
**问题**: 自定义类别映射没有生效
**解决**: 检查配置文件格式和路径

### 调试技巧
1. **启用详细日志**: 设置日志级别为 DEBUG
2. **检查配置**: 验证配置文件格式和内容
3. **测试路径**: 使用小规模测试验证路径规划
4. **监控性能**: 关注路径规划的性能指标

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本路径规划功能
- 支持多标签处理
- 支持路径冲突解决

### 计划功能
- 支持更复杂的路径模板
- 支持路径规划历史记录
- 支持路径规划性能优化
- 支持更多冲突解决策略
