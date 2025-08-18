# 命名生成模块 (Renamer)

## 概述

命名生成模块是自动文档分类系统的重要组成部分，负责根据文档内容、分类结果和配置模板生成有意义的文件名。该模块支持基于内容的标题提取、模板化命名、冲突处理等功能。

## 功能特性

### 核心功能
- **智能命名生成**: 根据文档内容和分类结果生成有意义的文件名
- **标题提取**: 从文档内容中自动提取标题
- **LLM标题生成**: 使用大语言模型生成文档标题
- **模板化命名**: 支持使用Jinja2模板定义命名规则
- **文件名清理**: 自动清理文件名中的无效字符
- **冲突处理**: 自动检测和解决文件名冲突

### 高级功能
- **多模板支持**: 支持按类别和文件类型使用不同模板
- **文件名截断**: 自动处理过长的文件名
- **模板管理**: 支持动态添加、删除和修改命名模板
- **验证功能**: 验证生成的命名结果
- **统计信息**: 提供命名生成的统计信息

## 架构设计

### 类结构
```
Renamer
├── 配置管理
│   ├── 命名模板配置
│   ├── 文件名限制配置
│   ├── 冲突解决配置
│   └── 字符处理配置
├── 命名生成
│   ├── 文档信息提取
│   ├── 标题提取和生成
│   ├── 模板选择和应用
│   └── 文件名清理和截断
├── 冲突处理
│   ├── 文件名冲突检测
│   ├── 后缀冲突解决
│   ├── 时间戳冲突解决
│   └── 路径构建
└── 辅助功能
    ├── 模板管理
    ├── 结果验证
    └── 统计信息
```

### 工作流程
1. **接收输入**: 路径规划结果、文档数据、分类结果
2. **信息提取**: 提取文档信息和元数据
3. **标题处理**: 提取或生成文档标题
4. **模板应用**: 选择合适的模板并应用
5. **文件名处理**: 清理和截断文件名
6. **冲突检查**: 检测并解决文件名冲突
7. **结果输出**: 返回命名生成结果

## 配置说明

### 基础配置
```yaml
naming:
  default_template: "{{category}}-{{title}}-{{date}}.{{ext}}"  # 默认模板
  max_filename_length: 200                                    # 最大文件名长度
  enable_llm_title: true                                      # 启用LLM标题生成
  title_max_length: 50                                        # 标题最大长度
  conflict_resolution: "suffix"                               # 冲突解决方式
  invalid_chars: "[<>:\"/\\\\|?*]"                           # 无效字符模式
  replacement_char: "_"                                       # 替换字符
  templates_file: "config/naming_templates.yaml"             # 模板文件
```

### 命名模板配置
```yaml
# config/naming_templates.yaml
default: "{{category}}-{{title}}-{{date}}.{{ext}}"

# 工作相关模板
工作: "工作-{{title}}-{{date}}.{{ext}}"
个人: "个人-{{title}}-{{date}}.{{ext}}"
财务: "财务-{{title}}-{{date}}.{{ext}}"

# 文件类型模板
pdf: "{{category}}-{{title}}.pdf"
doc: "{{category}}-{{title}}.doc"
docx: "{{category}}-{{title}}.docx"

# 特殊模板
重要: "重要-{{title}}-{{date}}.{{ext}}"
归档: "归档-{{title}}-{{date}}.{{ext}}"
```

## API 参考

### 主要方法

#### `generate_filename(path_plan, document_data, classification_result)`
生成文件名的主要方法。

**参数:**
- `path_plan` (Dict): 路径规划结果
  - `original_path` (str): 原始路径
  - `primary_path` (str): 主路径
  - `category` (str): 类别
- `document_data` (Dict): 文档数据
  - `file_path` (str): 文件路径
  - `text_content` (str): 文本内容
  - `summary` (str): 摘要
  - `metadata` (Dict): 元数据
- `classification_result` (Dict): 分类结果
  - `primary_category` (str): 主类别
  - `confidence_score` (float): 置信度
  - `tags` (List[str]): 标签列表

**返回:**
- `Dict`: 命名生成结果
  ```python
  {
      'original_path': str,
      'new_path': str,
      'original_filename': str,
      'new_filename': str,
      'template_used': str,
      'document_info': Dict,
      'conflict_info': Dict,
      'naming_time': str,
      'status': str
  }
  ```

#### `add_naming_template(category, template)`
添加命名模板。

**参数:**
- `category` (str): 类别或文件类型
- `template` (str): 模板字符串

**返回:**
- `bool`: 添加是否成功

#### `remove_naming_template(category)`
移除命名模板。

**参数:**
- `category` (str): 类别或文件类型

**返回:**
- `bool`: 移除是否成功

#### `get_naming_templates()`
获取所有命名模板。

**返回:**
- `Dict`: 模板字典

#### `validate_naming_result(naming_result)`
验证命名结果。

**参数:**
- `naming_result` (Dict): 命名结果

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

#### `_extract_document_info(document_data, classification_result)`
提取文档信息。

#### `_extract_title_from_content(content)`
从内容中提取标题。

#### `_generate_title_with_llm(document_data)`
使用LLM生成标题。

#### `_select_naming_template(category, document_info)`
选择命名模板。

#### `_apply_naming_template(template, document_info)`
应用命名模板。

#### `_clean_filename(filename)`
清理文件名。

#### `_truncate_filename(filename)`
截断文件名。

## 使用示例

### 基本使用
```python
from ods.naming.renamer import Renamer

# 创建命名生成器
config = {
    'naming': {
        'default_template': '{{category}}-{{title}}-{{date}}.{{ext}}',
        'max_filename_length': 200,
        'enable_llm_title': True
    }
}
renamer = Renamer(config)

# 生成文件名
path_plan = {
    'original_path': '/documents/项目计划书.pdf',
    'primary_path': 'OneDrive/分类/工作/document.pdf',
    'category': '工作'
}

document_data = {
    'file_path': '/documents/项目计划书.pdf',
    'text_content': '项目计划书\n\n这是一个重要的项目计划文档...',
    'summary': '项目计划文档',
    'metadata': {'author': '张三'}
}

classification_result = {
    'primary_category': '工作',
    'confidence_score': 0.9,
    'tags': ['工作', '项目A']
}

result = renamer.generate_filename(path_plan, document_data, classification_result)

print(f"原始文件名: {result['original_filename']}")
print(f"新文件名: {result['new_filename']}")
print(f"使用模板: {result['template_used']}")
```

### 模板管理
```python
# 添加自定义模板
renamer.add_naming_template('工作', '工作-{{title}}-{{date}}.{{ext}}')
renamer.add_naming_template('财务', '财务-{{title}}-{{date}}.{{ext}}')

# 获取所有模板
templates = renamer.get_naming_templates()
for category, template in templates.items():
    print(f"{category}: {template}")

# 移除模板
renamer.remove_naming_template('工作')
```

### 冲突处理
```python
# 检查冲突信息
if result['conflict_info']['has_conflict']:
    print(f"冲突类型: {result['conflict_info']['conflict_type']}")
    print(f"解决方式: {result['conflict_info']['resolution']}")
    print(f"最终路径: {result['conflict_info']['final_path']}")
```

## 模板系统

### Jinja2模板语法
支持Jinja2模板语法，包括变量、过滤器、条件语句等：

```python
# 基本变量
template = "{{category}}-{{title}}-{{date}}.{{ext}}"

# 使用过滤器
template = "{{category}}-{{title|truncate(20)}}-{{date|strftime('%Y%m%d')}}.{{ext}}"

# 条件语句
template = "{% if category == '重要' %}重要-{% endif %}{{title}}-{{date}}.{{ext}}"
```

### 内置过滤器
- `strftime(format)`: 格式化日期
- `truncate(length)`: 截断字符串
- `clean_filename`: 清理文件名

### 模板变量
- `{{category}}`: 文件类别
- `{{title}}`: 文档标题
- `{{date}}`: 当前日期
- `{{time}}`: 当前时间
- `{{timestamp}}`: 时间戳
- `{{year}}`: 年份
- `{{month}}`: 月份
- `{{day}}`: 日期
- `{{ext}}`: 文件扩展名
- `{{original_name}}`: 原始文件名
- 自定义元数据变量

## 标题处理

### 标题提取策略
1. **第一行提取**: 从文档第一行提取标题
2. **长度检查**: 确保标题长度适中（5-100字符）
3. **字符检查**: 过滤包含特殊字符的行
4. **LLM生成**: 如果无法提取，使用LLM生成标题

### LLM标题生成
当无法从内容中提取标题时，使用LLM生成：
- 分析文档内容
- 生成简洁的标题
- 确保标题长度在限制内
- 处理生成失败的情况

## 冲突解决策略

### 后缀策略
当文件名已存在时，添加数字后缀：
- `document.pdf` → `document_1.pdf`
- `document_1.pdf` → `document_2.pdf`

### 时间戳策略
当文件名已存在时，添加时间戳：
- `document.pdf` → `document_143022.pdf`

### 长文件名处理
当文件名超过长度限制时：
- 保留文件扩展名
- 截断文件名部分
- 添加省略号表示截断

## 错误处理

### 常见错误
1. **模板语法错误**: 记录错误并使用默认模板
2. **文件名过长**: 自动截断处理
3. **无效字符**: 自动替换为安全字符
4. **LLM生成失败**: 使用默认标题

### 错误状态
- `generated`: 生成成功
- `error`: 发生错误

## 性能优化

### 优化策略
1. **模板缓存**: 缓存编译后的Jinja2模板
2. **标题缓存**: 缓存已生成的标题
3. **批量处理**: 支持批量生成文件名
4. **异步处理**: 支持异步LLM调用

### 性能指标
- 文件名生成时间: < 50ms
- 模板应用时间: < 10ms
- 内存使用: < 5MB

## 测试

### 单元测试
```bash
# 运行命名生成器测试
pytest tests/test_renamer.py -v
```

### 测试覆盖
- 基本命名生成功能
- 模板应用
- 文件名清理
- 冲突解决
- 错误处理

## 扩展点

### 自定义标题提取
可以通过继承 `Renamer` 类来实现自定义的标题提取策略：

```python
class CustomRenamer(Renamer):
    def _extract_title_from_content(self, content):
        # 自定义标题提取逻辑
        pass
```

### 自定义模板引擎
可以实现自定义的模板引擎：

```python
def custom_template_engine(self, template, variables):
    # 自定义模板处理逻辑
    pass
```

## 最佳实践

### 配置建议
1. **合理设置文件名长度**: 考虑系统限制和可读性
2. **设计有意义的模板**: 使用清晰的命名模式
3. **配置冲突解决**: 选择合适的冲突解决策略
4. **设置字符替换**: 配置安全的字符替换规则

### 使用建议
1. **定期检查模板**: 确保模板符合命名规范
2. **监控冲突情况**: 关注文件名冲突的频率
3. **优化标题生成**: 根据实际使用情况调整标题提取策略
4. **备份模板配置**: 定期备份重要的命名模板

## 故障排除

### 常见问题

#### 模板应用失败
**问题**: Jinja2模板应用失败
**解决**: 检查模板语法和变量定义

#### 文件名过长
**问题**: 生成的文件名超过长度限制
**解决**: 调整模板或增加长度限制

#### 标题生成失败
**问题**: LLM标题生成失败
**解决**: 检查LLM配置和网络连接

#### 冲突解决不生效
**问题**: 文件名冲突解决策略不生效
**解决**: 检查冲突解决配置和文件系统权限

### 调试技巧
1. **启用详细日志**: 设置日志级别为 DEBUG
2. **检查模板**: 验证模板语法和变量
3. **测试标题提取**: 使用小规模测试验证标题提取
4. **监控性能**: 关注命名生成的性能指标

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本命名生成功能
- 支持Jinja2模板系统
- 支持文件名冲突解决

### 计划功能
- 支持更复杂的模板语法
- 支持命名历史记录
- 支持命名生成性能优化
- 支持更多标题提取策略
