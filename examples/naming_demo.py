#!/usr/bin/env python3
"""
命名生成模块演示脚本
演示如何使用Renamer进行文件名生成
"""

import sys
import os
from pathlib import Path
import logging
import yaml
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ods.naming.renamer import Renamer


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


def demo_basic_naming():
    """演示基本命名生成"""
    print("\n=== 基本命名生成演示 ===")

    config = {
        "naming": {
            "default_template": "{{category}}-{{title}}-{{date}}.{{ext}}",
            "max_filename_length": 200,
            "enable_llm_title": True,
            "title_max_length": 50,
            "conflict_resolution": "suffix",
            "invalid_chars": '[<>:"/\\\\|?*]',
            "replacement_char": "_",
            "templates_file": "demo_naming_templates.yaml",
        }
    }

    renamer = Renamer(config)

    # 测试用例
    test_cases = [
        {
            "name": "工作文档",
            "path_plan": {
                "original_path": "/documents/项目计划书.pdf",
                "primary_path": "demo_output/工作/document.pdf",
                "category": "工作",
            },
            "document_data": {
                "file_path": "/documents/项目计划书.pdf",
                "text_content": "项目计划书\n\n这是一个重要的项目计划文档，包含了详细的项目计划和执行方案。",
                "summary": "项目计划文档",
                "metadata": {"author": "张三", "project": "项目A"},
            },
            "classification_result": {
                "primary_category": "工作",
                "confidence_score": 0.9,
                "tags": ["工作", "项目A"],
            },
        },
        {
            "name": "财务文档",
            "path_plan": {
                "original_path": "/documents/发票.pdf",
                "primary_path": "demo_output/财务/document.pdf",
                "category": "财务",
            },
            "document_data": {
                "file_path": "/documents/发票.pdf",
                "text_content": "发票\n\n发票号码：INV-2024-001\n金额：1000元",
                "summary": "发票文档",
                "metadata": {"amount": 1000, "invoice_number": "INV-2024-001"},
            },
            "classification_result": {
                "primary_category": "财务",
                "confidence_score": 0.85,
                "tags": ["财务", "发票"],
            },
        },
        {
            "name": "个人文档",
            "path_plan": {
                "original_path": "/documents/个人笔记.txt",
                "primary_path": "demo_output/个人/document.txt",
                "category": "个人",
            },
            "document_data": {
                "file_path": "/documents/个人笔记.txt",
                "text_content": "今天的学习笔记\n\n学习了Python编程的基础知识...",
                "summary": "学习笔记",
                "metadata": {"topic": "Python学习"},
            },
            "classification_result": {
                "primary_category": "个人",
                "confidence_score": 0.8,
                "tags": ["个人", "学习"],
            },
        },
    ]

    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        print(f"原始文件名: {Path(case['path_plan']['original_path']).name}")
        print(f"分类结果: {case['classification_result']['primary_category']}")

        result = renamer.generate_filename(
            case["path_plan"], case["document_data"], case["classification_result"]
        )

        print(f"生成状态: {result['status']}")
        print(f"新文件名: {result['new_filename']}")
        print(f"使用模板: {result['template_used']}")
        print(f"新路径: {result['new_path']}")

        if result["conflict_info"]["has_conflict"]:
            print(f"冲突信息: {result['conflict_info']}")


def demo_template_selection():
    """演示模板选择"""
    print("\n=== 模板选择演示 ===")

    config = {
        "naming": {
            "default_template": "{{category}}-{{title}}-{{date}}.{{ext}}",
            "templates_file": "demo_naming_templates.yaml",
        }
    }

    renamer = Renamer(config)

    # 添加自定义模板
    renamer.add_naming_template("工作", "工作-{{title}}-{{date}}.{{ext}}")
    renamer.add_naming_template("财务", "财务-{{title}}-{{date}}.{{ext}}")
    renamer.add_naming_template("pdf", "{{category}}-{{title}}.pdf")

    test_cases = [
        {
            "category": "工作",
            "document_info": {"ext": "pdf", "title": "项目计划书", "date": "20240101"},
        },
        {
            "category": "财务",
            "document_info": {"ext": "pdf", "title": "发票", "date": "20240101"},
        },
        {
            "category": "其他",
            "document_info": {"ext": "pdf", "title": "文档", "date": "20240101"},
        },
    ]

    for case in test_cases:
        template = renamer._select_naming_template(
            case["category"], case["document_info"]
        )
        print(f"类别: {case['category']} -> 模板: {template}")


def demo_filename_cleaning():
    """演示文件名清理"""
    print("\n=== 文件名清理演示 ===")

    config = {"naming": {"invalid_chars": '[<>:"/\\\\|?*]', "replacement_char": "_"}}

    renamer = Renamer(config)

    test_filenames = [
        "正常文件名.pdf",
        "文件<名>:*.pdf",
        "包含/路径\\的文件名.txt",
        "  文件名前后有空格  .pdf",
        "",
        "   ",
    ]

    for filename in test_filenames:
        cleaned = renamer._clean_filename(filename)
        print(f"原始: '{filename}' -> 清理后: '{cleaned}'")


def demo_filename_truncation():
    """演示文件名截断"""
    print("\n=== 文件名截断演示 ===")

    config = {"naming": {"max_filename_length": 50}}

    renamer = Renamer(config)

    test_filenames = [
        "正常长度的文件名.pdf",
        "这是一个非常长的文件名，超过了最大长度限制，需要被截断.pdf",
        "短文件名.txt",
        "a" * 100 + ".pdf",  # 超长文件名
    ]

    for filename in test_filenames:
        truncated = renamer._truncate_filename(filename)
        print(f"原始长度: {len(filename)} -> 截断后长度: {len(truncated)}")
        print(f"原始: '{filename}'")
        print(f"截断后: '{truncated}'")
        print()


def demo_conflict_resolution():
    """演示冲突解决"""
    print("\n=== 冲突解决演示 ===")

    config = {"naming": {"conflict_resolution": "suffix"}}

    renamer = Renamer(config)

    # 创建测试文件
    test_dir = Path("demo_output/工作")
    test_dir.mkdir(parents=True, exist_ok=True)

    test_file = test_dir / "document.pdf"
    test_file.write_text("test content")

    try:
        # 测试后缀冲突解决
        path = str(test_file)
        resolved_path = renamer._resolve_filename_conflict_with_suffix(path)

        print(f"原始路径: {path}")
        print(f"解决后路径: {resolved_path}")
        print(f"是否不同: {path != resolved_path}")

        # 测试时间戳冲突解决
        timestamp_path = renamer._resolve_filename_conflict_with_timestamp(path)
        print(f"时间戳解决路径: {timestamp_path}")

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()


def demo_jinja2_templates():
    """演示Jinja2模板"""
    print("\n=== Jinja2模板演示 ===")

    config = {
        "naming": {
            "default_template": '{{category}}-{{title|truncate(20)}}-{{date|strftime("%Y%m%d")}}.{{ext}}'
        }
    }

    renamer = Renamer(config)

    template = '{{category}}-{{title|truncate(10)}}-{{date|strftime("%Y%m%d")}}.{{ext}}'
    document_info = {
        "category": "工作",
        "title": "这是一个很长的标题，需要被截断",
        "date": "2024-01-01",
        "ext": "pdf",
    }

    result = renamer._apply_naming_template(template, document_info)
    print(f"模板: {template}")
    print(f"变量: {document_info}")
    print(f"结果: {result}")


def demo_template_management():
    """演示模板管理"""
    print("\n=== 模板管理演示 ===")

    config = {"naming": {"templates_file": "demo_naming_templates.yaml"}}

    renamer = Renamer(config)

    # 添加模板
    templates_to_add = {
        "工作": "工作-{{title}}-{{date}}.{{ext}}",
        "财务": "财务-{{title}}-{{date}}.{{ext}}",
        "个人": "个人-{{title}}-{{date}}.{{ext}}",
        "pdf": "{{category}}-{{title}}.pdf",
    }

    for category, template in templates_to_add.items():
        success = renamer.add_naming_template(category, template)
        print(f"添加模板 '{category}': {'成功' if success else '失败'}")

    # 获取所有模板
    all_templates = renamer.get_naming_templates()
    print(f"\n当前模板数量: {len(all_templates)}")
    for category, template in all_templates.items():
        print(f"  {category}: {template}")

    # 移除模板
    success = renamer.remove_naming_template("工作")
    print(f"\n移除模板 '工作': {'成功' if success else '失败'}")

    # 验证移除
    all_templates = renamer.get_naming_templates()
    print(f"移除后模板数量: {len(all_templates)}")


def demo_validation():
    """演示验证功能"""
    print("\n=== 验证功能演示 ===")

    config = {"naming": {"max_filename_length": 200, "invalid_chars": '[<>:"/\\\\|?*]'}}

    renamer = Renamer(config)

    # 有效的命名结果
    valid_result = {
        "original_path": "/test/document.pdf",
        "new_path": "demo_output/工作/document.pdf",
        "new_filename": "工作-项目计划书-20240101.pdf",
        "status": "generated",
    }

    validation_result = renamer.validate_naming_result(valid_result)
    print(f"有效结果验证: {validation_result['is_valid']}")
    print(f"错误: {validation_result['errors']}")
    print(f"警告: {validation_result['warnings']}")

    # 无效的命名结果
    invalid_result = {
        "original_path": "/test/document.pdf",
        "new_filename": "文件<名>:*.pdf",  # 包含无效字符
        "status": "generated",
    }

    validation_result = renamer.validate_naming_result(invalid_result)
    print(f"\n无效结果验证: {validation_result['is_valid']}")
    print(f"错误: {validation_result['errors']}")
    print(f"警告: {validation_result['warnings']}")


def demo_statistics():
    """演示统计信息"""
    print("\n=== 统计信息演示 ===")

    config = {
        "naming": {
            "default_template": "{{category}}-{{title}}-{{date}}.{{ext}}",
            "max_filename_length": 200,
            "enable_llm_title": True,
            "title_max_length": 50,
            "conflict_resolution": "suffix",
            "invalid_chars": '[<>:"/\\\\|?*]',
            "replacement_char": "_",
        }
    }

    renamer = Renamer(config)

    # 添加一些模板
    renamer.add_naming_template("工作", "工作-{{title}}-{{date}}.{{ext}}")
    renamer.add_naming_template("财务", "财务-{{title}}-{{date}}.{{ext}}")

    stats = renamer.get_naming_statistics()

    print("命名生成器统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """主函数"""
    print("基于LLM和向量数据库的自动文档分类系统")
    print("命名生成模块演示")
    print("=" * 60)

    setup_logging()

    config = load_config()
    if config:
        print(f"配置文件加载成功: {len(config)} 个配置项")
    else:
        print("使用默认配置")

    try:
        demo_basic_naming()
        demo_template_selection()
        demo_filename_cleaning()
        demo_filename_truncation()
        demo_conflict_resolution()
        demo_jinja2_templates()
        demo_template_management()
        demo_validation()
        demo_statistics()

        print("\n=== 演示完成 ===")
        print("\n下一步:")
        print("1. 配置命名模板")
        print("2. 设置文件名规则")
        print("3. 测试冲突处理")
        print("4. 集成到实际工作流中")

    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        logging.error(f"演示错误: {e}", exc_info=True)

    finally:
        # 清理演示文件
        if Path("demo_naming_templates.yaml").exists():
            Path("demo_naming_templates.yaml").unlink()
        if Path("demo_output").exists():
            import shutil

            shutil.rmtree("demo_output")


if __name__ == "__main__":
    main()
