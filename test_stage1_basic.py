#!/usr/bin/env python3
"""
Stage 1 MVP 基本功能测试

快速验证所有主要组件是否能正常工作
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试所有必要的导入"""
    print("🔍 测试模块导入...")

    try:
        from ods.core.config import Config

        print("✅ Config导入成功")

        from ods.parsers.document_parser import DocumentParser

        print("✅ DocumentParser导入成功")

        from ods.embeddings.embedder import Embedder
        from ods.embeddings.text_processor import TextProcessor
        from ods.embeddings.models import EmbeddingModelFactory

        print("✅ Embeddings模块导入成功")

        from ods.classifiers.classifier import DocumentClassifier

        print("✅ DocumentClassifier导入成功")

        from ods.path_planner.path_planner import PathPlanner

        print("✅ PathPlanner导入成功")

        from ods.naming.renamer import Renamer

        print("✅ Renamer导入成功")

        from ods.rules.rule_engine import RuleEngine

        print("✅ RuleEngine导入成功")

        from ods.storage.file_mover import FileMover
        from ods.storage.index_updater import IndexUpdater

        print("✅ Storage模块导入成功")

        from ods.core.workflow import DocumentClassificationWorkflow

        print("✅ DocumentClassificationWorkflow导入成功")

        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")

    try:
        # 创建临时工作空间
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)

        # 创建测试配置
        config_data = {
            "llm": {"provider": "mock", "model": "test-model"},
            "embedding": {
                "type": "local",
                "model_name": "BAAI/bge-m3",
                "device": "cpu",
            },
            "classification": {
                "categories": ["工作", "个人", "财务", "其他"],
                "confidence_threshold": 0.8,
                "review_threshold": 0.6,
            },
            "file": {
                "source_directory": str(workspace / "source"),
                "target_directory": str(workspace / "target"),
                "supported_extensions": [".txt", ".pdf", ".docx"],
            },
            "path_planning": {
                "base_path": str(workspace / "target"),
                "path_template": "{category}",
            },
            "naming": {"default_template": "{{category}}-{{original_name}}.{{ext}}"},
            "system": {"dry_run": True, "temp_directory": str(workspace / "temp")},
        }

        # 创建目录
        (workspace / "source").mkdir()
        (workspace / "target").mkdir()
        (workspace / "temp").mkdir()

        # 创建测试文件
        test_file = workspace / "source" / "test_document.txt"
        test_file.write_text(
            "这是一份工作项目的测试文档，包含项目信息和业务数据。", encoding="utf-8"
        )

        # 测试文档解析器
        from ods.parsers.document_parser import DocumentParser

        parser = DocumentParser(config_data)
        parse_result = parser.parse(test_file)
        print(f"✅ 文档解析: {parse_result.success}")

        # 测试文本处理器
        from ods.embeddings.text_processor import TextProcessor

        text_processor = TextProcessor(config_data)
        processed_text = text_processor.process_text(
            "这是一个测试文档，包含工作相关内容。"
        )
        print(f"✅ 文本处理: 生成{len(processed_text.chunks)}个文本块")

        # 测试路径规划器
        from ods.path_planner.path_planner import PathPlanner

        path_planner = PathPlanner(config_data)
        classification_result = {"primary_category": "工作", "confidence_score": 0.9}
        path_plan = path_planner.plan_file_path(
            classification_result, str(test_file), {"file_type": "txt"}
        )
        print(f"✅ 路径规划: {path_plan['status']}")

        # 测试命名生成器
        from ods.naming.renamer import Renamer

        renamer = Renamer(config_data)
        document_data = {
            "file_path": str(test_file),
            "text_content": "测试内容",
            "metadata": {},
        }
        naming_result = renamer.generate_filename(
            path_plan, document_data, classification_result
        )
        print(f"✅ 命名生成: {naming_result['status']}")

        # 测试规则引擎
        from ods.rules.rule_engine import RuleEngine

        rule_engine = RuleEngine(config_data)
        rules_result = rule_engine.apply_rules(classification_result, document_data)
        print(f"✅ 规则引擎: 应用了{len(rules_result.get('rules_applied', []))}条规则")

        # 测试文件移动器（dry run模式）
        from ods.storage.file_mover import FileMover

        file_mover = FileMover(config_data)
        # 在dry run模式下测试
        move_result = file_mover.move_file(path_plan, naming_result)
        print(f"✅ 文件移动器测试完成")

        # 清理
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_import():
    """测试CLI模块导入"""
    print("\n🖥️  测试CLI模块...")

    try:
        from ods.cli import main

        print("✅ CLI模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ CLI导入失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 Stage 1 MVP 基本功能测试")
    print("=" * 50)

    success = True

    # 测试导入
    if not test_imports():
        success = False

    # 测试基本功能
    if not test_basic_functionality():
        success = False

    # 测试CLI
    if not test_cli_import():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 所有基本测试通过！Stage 1 MVP 准备就绪")
        print("\n📝 使用说明:")
        print("1. 运行 'python -m ods init' 初始化系统")
        print("2. 运行 'python -m ods apply <目录>' 开始分类文档")
        print("3. 运行 'python -m ods info' 查看系统信息")
    else:
        print("❌ 部分测试失败，请检查相关模块")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
