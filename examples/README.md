# 示例代码说明

本目录包含自动文档分类系统的各种使用示例。

## 示例文件说明

### 1. classification_demo.py

演示如何使用分类器对文档进行分类，包括：

- 基础分类功能
- 多标签分类
- 置信度阈值设置
- 分类结果展示

### 2. embedding_demo.py

演示如何使用嵌入模型处理文档，包括：

- 文档向量化
- 相似度计算
- 向量存储操作
- 语义搜索示例

### 3. index_updater_demo.py

演示如何更新和维护文档索引，包括：

- 索引创建和更新
- 增量索引维护
- 索引查询和检索
- 性能优化示例

### 4. naming_demo.py

演示如何使用命名生成器重命名文件，包括：

- 模板化命名
- 智能标题生成
- 冲突解决
- 批量重命名

### 5. path_planning_demo.py

演示如何使用路径规划器组织文件结构，包括：

- 路径模板应用
- 多标签路径规划
- 冲突解决策略
- 目录结构创建

## 运行示例

```bash
# 运行分类演示
python examples/classification_demo.py

# 运行嵌入演示
python examples/embedding_demo.py

# 运行索引更新演示
python examples/index_updater_demo.py

# 运行命名演示
python examples/naming_demo.py

# 运行路径规划演示
python examples/path_planning_demo.py
```

## 注意事项

1. 运行示例前请确保已安装所有依赖
2. 某些示例可能需要配置LLM服务（如Ollama）
3. 示例中的文件路径请根据实际情况调整
4. 建议先在测试环境中运行示例
