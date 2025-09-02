#!/usr/bin/env python3
"""
测试审核功能的基本功能

运行此脚本验证review功能的各个组件是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")

    try:
        from ods.review.review_manager import ReviewManager
        from ods.review.interactive_reviewer import InteractiveReviewer
        from ods.review.reclassification_workflow import ReclassificationWorkflow
        from ods.core.database import Database

        print("✅ 所有review模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_database_tables():
    """测试数据库表创建"""
    print("\n🔍 测试数据库表创建...")

    try:
        from ods.core.database import Database
        from ods.core.config import Config

        config = Config()
        db = Database(config.get_config_dict())

        # 检查review相关表是否存在
        query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('review_sessions', 'review_records')
        """
        result = db.execute_query(query)

        if len(result) >= 2:
            print("✅ Review数据库表创建成功")
            return True
        else:
            print(f"❌ 缺少review表，当前表: {[row['name'] for row in result]}")
            return False

    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


def test_review_manager():
    """测试ReviewManager基本功能"""
    print("\n🔍 测试ReviewManager...")

    try:
        from ods.review.review_manager import ReviewManager
        from ods.core.config import Config

        config = Config()
        manager = ReviewManager(config.get_config_dict())

        # 测试创建会话
        session_id = manager.create_review_session("test_user")
        print(f"✅ 审核会话创建成功: {session_id}")

        # 测试获取统计
        stats = manager.get_review_statistics()
        print(f"✅ 审核统计获取成功: {stats}")

        return True

    except Exception as e:
        print(f"❌ ReviewManager测试失败: {e}")
        return False


def test_config_validation():
    """测试配置文件结构"""
    print("\n🔍 测试配置文件...")

    try:
        from ods.core.config import Config

        config = Config()
        config_dict = config.get_config_dict()

        # 检查必需的配置项
        required_sections = [
            "classification.taxonomies",
            "classification.confidence_threshold",
            "classification.tag_rules",
        ]

        missing_sections = []
        for section in required_sections:
            keys = section.split(".")
            current = config_dict
            try:
                for key in keys:
                    current = current[key]
            except KeyError:
                missing_sections.append(section)

        if not missing_sections:
            print("✅ 配置文件结构完整")
            return True
        else:
            print(f"❌ 配置文件缺少部分: {missing_sections}")
            return False

    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试Review功能")
    print("=" * 50)

    tests = [
        ("模块导入", test_imports),
        ("数据库表", test_database_tables),
        ("ReviewManager", test_review_manager),
        ("配置文件", test_config_validation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 运行测试: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ 测试失败: {test_name}")

    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！Review功能已准备就绪")
        print("\n💡 使用方法:")
        print("   1. 运行文件分类: python -m ods apply")
        print("   2. 启动审核界面: python -m ods review")
        print("   3. 查看审核统计: python -m ods review-stats")
    else:
        print("⚠️  部分测试失败，请检查配置和依赖")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
