#!/usr/bin/env python3
"""
路径规划模块演示脚本
演示如何使用PathPlanner进行文件路径规划
"""

import sys
import os
from pathlib import Path
import logging
import yaml
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ods.path_planner.path_planner import PathPlanner


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_config():
    """加载配置"""
    config_file = project_root / "config" / "rules.yaml"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def demo_basic_path_planning():
    """演示基本路径规划"""
    print("\n=== 基本路径规划演示 ===")

    config = {
        "path_planning": {
            "base_path": "demo_output",
            "default_categories": ["工作", "个人", "财务", "其他"],
            "multi_label_strategy": "primary_with_links",
            "path_template": "{category}/{year}/{month}",
            "conflict_resolution": "suffix",
            "max_path_length": 260,
            "special_paths": {
                "uncategorized": "待整理",
                "needs_review": "待审核",
                "important": "重要文件",
                "archive": "归档",
            },
        },
        "classification": {"review_threshold": 0.6},
    }

    planner = PathPlanner(config)

    # 测试用例
    test_cases = [
        {
            "name": "工作文档",
            "classification": {
                "primary_category": "工作",
                "confidence_score": 0.9,
                "tags": ["工作", "项目A"],
            },
            "original_path": "/documents/项目计划书.pdf",
            "metadata": {"file_size": 1024000, "file_type": "pdf", "author": "张三"},
        },
        {
            "name": "财务文档",
            "classification": {
                "primary_category": "财务",
                "confidence_score": 0.85,
                "tags": ["财务", "发票"],
            },
            "original_path": "/documents/发票.pdf",
            "metadata": {"file_size": 512000, "file_type": "pdf", "amount": 1000},
        },
        {
            "name": "低置信度文档",
            "classification": {
                "primary_category": "其他",
                "confidence_score": 0.5,  # 低于阈值
                "tags": ["其他"],
            },
            "original_path": "/documents/未知文档.pdf",
            "metadata": {"file_size": 256000, "file_type": "pdf"},
        },
    ]

    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        print(f"原始路径: {case['original_path']}")
        print(f"分类结果: {case['classification']['primary_category']}")
        print(f"置信度: {case['classification']['confidence_score']}")

        result = planner.plan_file_path(
            case["classification"], case["original_path"], case["metadata"]
        )

        print(f"规划状态: {result['status']}")
        print(f"主路径: {result['primary_path']}")
        print(f"链接路径数量: {len(result['link_paths'])}")

        if result["conflict_info"]["has_conflict"]:
            print(f"冲突信息: {result['conflict_info']}")


def demo_path_conflicts():
    """演示路径冲突处理"""
    print("\n=== 路径冲突处理演示 ===")

    config = {
        "path_planning": {
            "base_path": "demo_output",
            "default_categories": ["工作", "个人", "财务", "其他"],
            "conflict_resolution": "suffix",
            "max_path_length": 260,
        }
    }

    planner = PathPlanner(config)

    # 创建测试文件
    test_dir = Path("demo_output/工作")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_file = test_dir / "document.pdf"
    test_file.write_text("test content")

    try:
        # 测试冲突解决
        target_path = str(test_file)
        original_path = "/test/document.pdf"

        conflict_info = planner._check_path_conflicts(target_path, original_path)

        print(f"目标路径: {target_path}")
        print(f"冲突检测: {conflict_info['has_conflict']}")
        print(f"冲突类型: {conflict_info['conflict_type']}")
        print(f"解决方式: {conflict_info['resolution']}")
        print(f"建议路径: {conflict_info['suggested_path']}")

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()


def demo_directory_structure():
    """演示目录结构创建"""
    print("\n=== 目录结构创建演示 ===")

    config = {
        "path_planning": {
            "base_path": "demo_output",
            "default_categories": ["工作", "个人", "财务", "其他"],
        }
    }

    planner = PathPlanner(config)

    path_plan = {
        "primary_path": "demo_output/工作/2024/01/document.pdf",
        "link_paths": [
            {"link_path": "demo_output/项目A/链接/document.pdf"},
            {"link_path": "demo_output/重要文件/链接/document.pdf"},
        ],
    }

    result = planner.create_directory_structure(path_plan)

    print(f"目录创建结果: {result}")
    print(f"主目录存在: {Path('demo_output/工作/2024/01').exists()}")
    print(f"链接目录存在: {Path('demo_output/项目A/链接').exists()}")
    print(f"重要文件目录存在: {Path('demo_output/重要文件/链接').exists()}")


def demo_path_validation():
    """演示路径规划验证"""
    print("\n=== 路径规划验证演示 ===")

    config = {"path_planning": {"base_path": "demo_output", "max_path_length": 260}}

    planner = PathPlanner(config)

    # 有效的路径规划
    valid_plan = {
        "original_path": "/test/document.pdf",
        "primary_path": "demo_output/工作/document.pdf",
        "status": "planned",
    }

    validation_result = planner.validate_path_plan(valid_plan)
    print(f"有效规划验证: {validation_result['is_valid']}")
    print(f"错误数量: {len(validation_result['errors'])}")
    print(f"警告数量: {len(validation_result['warnings'])}")

    # 无效的路径规划
    invalid_plan = {
        "original_path": "/test/document.pdf"
        # 缺少必要字段
    }

    validation_result = planner.validate_path_plan(invalid_plan)
    print(f"无效规划验证: {validation_result['is_valid']}")
    print(f"错误: {validation_result['errors']}")


def demo_statistics():
    """演示统计信息获取"""
    print("\n=== 统计信息演示 ===")

    config = {
        "path_planning": {
            "base_path": "demo_output",
            "default_categories": ["工作", "个人", "财务", "其他"],
            "multi_label_strategy": "primary_with_links",
            "path_template": "{category}/{year}/{month}",
            "max_path_length": 260,
            "special_paths": {"uncategorized": "待整理", "needs_review": "待审核"},
        }
    }

    planner = PathPlanner(config)

    stats = planner.get_path_statistics()

    print("路径规划器统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def demo_template_variables():
    """演示模板变量处理"""
    print("\n=== 模板变量处理演示 ===")

    config = {
        "path_planning": {
            "base_path": "demo_output",
            "path_template": "{category}/{year}/{month}/{author}",
        }
    }

    planner = PathPlanner(config)

    category = "工作"
    metadata = {"author": "张三", "project": "项目A", "department": "技术部"}

    variables = planner._get_template_variables(category, metadata)

    print("模板变量:")
    for key, value in variables.items():
        print(f"  {key}: {value}")

    # 应用模板
    template = "{category}/{year}/{month}/{author}"
    result = planner._apply_path_template(template, variables)
    print(f"模板应用结果: {result}")


def main():
    """主函数"""
    print("基于LLM和向量数据库的自动文档分类系统")
    print("路径规划模块演示")
    print("=" * 60)

    setup_logging()

    config = load_config()
    if config:
        print(f"配置文件加载成功: {len(config)} 个配置项")
    else:
        print("使用默认配置")

    try:
        demo_basic_path_planning()
        demo_path_conflicts()
        demo_directory_structure()
        demo_path_validation()
        demo_statistics()
        demo_template_variables()

        print("\n=== 演示完成 ===")
        print("\n下一步:")
        print("1. 配置路径规划参数")
        print("2. 设置类别映射规则")
        print("3. 测试路径冲突处理")
        print("4. 集成到实际工作流中")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        logging.error(f"演示错误: {e}", exc_info=True)

    finally:
        # 清理演示目录
        if Path("demo_output").exists():
            import shutil

            shutil.rmtree("demo_output")


if __name__ == "__main__":
    main()
