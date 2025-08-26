"""
分类模块演示脚本
展示如何使用分类器进行智能文档分类
"""

import sys
from pathlib import Path
import logging
import yaml

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ods.classifiers.classifier import DocumentClassifier
from ods.classifiers.retrieval_agent import RetrievalAgent
from ods.classifiers.llm_classifier import LLMClassifier
from ods.classifiers.rule_checker import RuleChecker


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_config():
    """加载配置"""
    config_path = project_root / "config" / "rules.yaml"

    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return None


def demo_retrieval_agent():
    """演示检索代理"""
    print("\n=== 检索代理演示 ===")

    # 配置示例
    _ = {
        "database": {"vector_db_path": ".ods/demo_vector_db"},
        "collection_name": "demo_documents",
        "top_k": 3,
        "similarity_threshold": 0.7,
    }

    try:
        # 注意：这里需要实际的ChromaDB依赖
        print("检索代理功能演示:")
        print("  - 向量数据库连接和集合管理")
        print("  - 文档添加和检索")
        print("  - 相似文档搜索")
        print("  - 类别示例获取")
        print("\n注意: 实际使用需要安装 chromadb 依赖")

    except Exception as e:
        print(f"检索代理演示失败: {e}")


def demo_llm_classifier():
    """演示LLM分类器"""
    print("\n=== LLM分类器演示 ===")

    # 配置示例
    _ = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "your-api-key-here",
            "temperature": 0.1,
            "max_tokens": 1000,
        },
        "classification": {
            "categories": ["工作", "个人", "财务", "其他"],
            "confidence_threshold": 0.8,
            "review_threshold": 0.6,
            "max_tags": 3,
        },
    }

    print("LLM分类器功能演示:")
    print("  - 支持多种LLM提供商 (OpenAI, Anthropic, Ollama)")
    print("  - 智能提示模板和响应解析")
    print("  - 置信度评估和人工复核标记")
    print("  - 备用分类策略")
    print("\n注意: 实际使用需要设置有效的API密钥")


def demo_rule_checker():
    """演示规则检查器"""
    print("\n=== 规则检查器演示 ===")

    config = {
        "rules": {
            "rules_file": "config/rules.yaml",
            "enable_rules": True,
            "strict_mode": False,
        }
    }

    try:
        rule_checker = RuleChecker(config)

        print("规则检查器功能演示:")
        print("  - 文件扩展名规则")
        print("  - 文件名关键词规则")
        print("  - 内容关键词规则")
        print("  - 文件大小规则")
        print("  - 自定义规则")

        # 添加示例规则
        rule_checker.add_rule("file_extension", ".pdf", "文档", 1)
        rule_checker.add_rule("file_name", "发票", "财务", 2)
        rule_checker.add_rule("content_keywords", "合同", "工作", 3)

        # 获取规则摘要
        rules_summary = rule_checker.get_rules_summary()
        print(f"\n当前规则统计: {rules_summary}")

    except Exception as e:
        print(f"规则检查器演示失败: {e}")


def demo_document_classifier():
    """演示文档分类器"""
    print("\n=== 文档分类器演示 ===")

    config = {
        "classification": {
            "categories": ["工作", "个人", "财务", "其他"],
            "confidence_threshold": 0.8,
            "review_threshold": 0.6,
            "max_tags": 3,
        },
        "database": {"vector_db_path": ".ods/demo_vector_db"},
    }

    try:
        # 模拟分类器（避免依赖问题）
        print("文档分类器功能演示:")
        print("  - 整合检索代理、LLM分类器和规则检查器")
        print("  - 完整的分类流水线")
        print("  - 批量文档处理")
        print("  - 分类结果管理和更新")
        print("  - 统计信息和导出功能")

        # 模拟分类结果
        sample_results = [
            {
                "file_path": "/demo/doc1.pdf",
                "primary_category": "工作",
                "confidence_score": 0.95,
                "needs_review": False,
            },
            {
                "file_path": "/demo/doc2.pdf",
                "primary_category": "财务",
                "confidence_score": 0.88,
                "needs_review": False,
            },
            {
                "file_path": "/demo/doc3.pdf",
                "primary_category": "个人",
                "confidence_score": 0.65,
                "needs_review": True,
            },
        ]

        print("\n示例分类结果:")
        for result in sample_results:
            status = "✓ 自动分类" if not result["needs_review"] else "⚠ 需要复核"
            print(
                f"  {result['file_path']} -> {result['primary_category']} "
                f"(置信度: {result['confidence_score']:.2f}) {status}"
            )

    except Exception as e:
        print(f"文档分类器演示失败: {e}")


def demo_classification_workflow():
    """演示分类工作流"""
    print("\n=== 分类工作流演示 ===")

    print("完整的文档分类工作流:")
    print("  1. 文档解析 -> 提取文本内容和元数据")
    print("  2. 嵌入生成 -> 将文本转换为向量表示")
    print("  3. 相似检索 -> 在向量数据库中查找相似文档")
    print("  4. LLM分类 -> 基于内容和相似文档进行智能分类")
    print("  5. 规则检查 -> 应用用户定义的分类规则")
    print("  6. 结果存储 -> 将分类结果保存到向量数据库")
    print("  7. 文件移动 -> 根据分类结果组织文件结构")

    print("\n工作流特点:")
    print("  - 基于LangGraph的节点化设计")
    print("  - 支持并行处理和错误恢复")
    print("  - 可配置的分类策略和规则")
    print("  - 完整的审计和回滚机制")


def demo_advanced_features():
    """演示高级功能"""
    print("\n=== 高级功能演示 ===")

    print("高级分类功能:")
    print("  - 多标签分类支持")
    print("  - 置信度阈值配置")
    print("  - 人工复核工作流")
    print("  - 分类结果导出和导入")
    print("  - 规则动态管理")
    print("  - 性能监控和优化")

    print("\n扩展性设计:")
    print("  - 支持新的LLM提供商")
    print("  - 可插拔的规则引擎")
    print("  - 自定义分类算法")
    print("  - 多语言支持")


def demo_integration():
    """演示系统集成"""
    print("\n=== 系统集成演示 ===")

    print("与其他模块的集成:")
    print("  - 嵌入模块: 提供文档向量表示")
    print("  - 解析模块: 提取文档内容")
    print("  - 存储模块: 管理文件组织和索引")
    print("  - 规则模块: 应用分类策略")
    print("  - 工作流引擎: 协调整个分类流程")

    print("\n外部系统集成:")
    print("  - 文件监控系统")
    print("  - 内容管理系统")
    print("  - 工作流自动化平台")
    print("  - 报告和分析系统")


def main():
    """主函数"""
    print("基于LLM和向量数据库的自动文档分类系统")
    print("分类判定模块演示")
    print("=" * 60)

    setup_logging()

    # 加载配置
    config = load_config()
    if config:
        print(f"配置文件加载成功: {len(config)} 个配置项")
    else:
        print("使用默认配置")

    try:
        # 演示各个组件
        demo_retrieval_agent()
        demo_llm_classifier()
        demo_rule_checker()
        demo_document_classifier()
        demo_classification_workflow()
        demo_advanced_features()
        demo_integration()

        print("\n=== 演示完成 ===")
        print("\n下一步:")
        print("1. 安装必要的依赖包 (chromadb, openai, anthropic)")
        print("2. 配置LLM API密钥和参数")
        print("3. 设置向量数据库路径")
        print("4. 运行测试验证功能")
        print("5. 集成到实际工作流中")

        print("\n依赖安装命令:")
        print("  pip install chromadb openai anthropic pyyaml")
        print("  pip install sentence-transformers torch")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        logging.error(f"演示错误: {e}", exc_info=True)


if __name__ == "__main__":
    main()
