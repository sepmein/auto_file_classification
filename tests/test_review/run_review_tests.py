#!/usr/bin/env python3
"""
Review功能测试运行器

运行所有review相关的单元测试
"""

import sys
import os
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.test_review.test_review_manager import TestReviewManager
from tests.test_review.test_interactive_reviewer import TestInteractiveReviewer
from tests.test_review.test_reclassification_workflow import (
    TestReclassificationWorkflow,
)
from tests.test_review.test_database_review import TestDatabaseReview
from tests.test_review.test_cli_review import TestCLIReview


def run_all_review_tests():
    """运行所有review相关的测试"""

    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加所有测试类
    test_classes = [
        TestReviewManager,
        TestInteractiveReviewer,
        TestReclassificationWorkflow,
        TestDatabaseReview,
        TestCLIReview,
    ]

    for test_class in test_classes:
        test_suite.addTest(unittest.makeSuite(test_class))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)

    # 返回测试结果
    return result.wasSuccessful()


def run_specific_test(test_class_name, test_method_name=None):
    """运行指定的测试"""

    test_classes = {
        "ReviewManager": TestReviewManager,
        "InteractiveReviewer": TestInteractiveReviewer,
        "ReclassificationWorkflow": TestReclassificationWorkflow,
        "DatabaseReview": TestDatabaseReview,
        "CLIReview": TestCLIReview,
    }

    if test_class_name not in test_classes:
        print(f"❌ 未知的测试类: {test_class_name}")
        print(f"可用的测试类: {list(test_classes.keys())}")
        return False

    test_class = test_classes[test_class_name]

    if test_method_name:
        # 运行指定方法
        suite = unittest.TestSuite()
        suite.addTest(test_class(test_method_name))
    else:
        # 运行整个类
        suite = unittest.makeSuite(test_class)

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    return result.wasSuccessful()


def show_test_summary():
    """显示测试摘要"""

    print("\n" + "=" * 60)
    print("📋 Review功能测试摘要")
    print("=" * 60)

    test_info = {
        "TestReviewManager": {
            "description": "审核管理器核心功能测试",
            "tests": [
                "创建审核会话",
                "获取待审核文件",
                "记录审核决策",
                "获取审核统计",
                "结束审核会话",
                "优先级计算",
            ],
        },
        "TestInteractiveReviewer": {
            "description": "交互式审核界面测试",
            "tests": [
                "显示文件信息",
                "获取用户决策",
                "批量操作处理",
                "记录审核决策",
                "会话总结显示",
            ],
        },
        "TestReclassificationWorkflow": {
            "description": "重新分类工作流测试",
            "tests": [
                "重新分类文件",
                "批量重新分类",
                "路径规划和移动",
                "索引更新",
                "错误处理",
            ],
        },
        "TestDatabaseReview": {
            "description": "数据库review功能测试",
            "tests": [
                "创建审核会话",
                "获取待审核文件",
                "记录审核操作",
                "更新审核状态",
                "获取会话统计",
            ],
        },
        "TestCLIReview": {
            "description": "CLI review命令测试",
            "tests": [
                "review命令基本功能",
                "review-stats命令",
                "参数处理",
                "错误处理",
                "帮助信息",
            ],
        },
    }

    total_tests = sum(len(info["tests"]) for info in test_info.values())

    print(f"🎯 总测试类数: {len(test_info)}")
    print(f"🧪 总测试用例数: {total_tests}")
    print()

    for class_name, info in test_info.items():
        print(f"📁 {class_name}")
        print(f"   {info['description']}")
        print(f"   包含测试: {len(info['tests'])} 个")
        for i, test in enumerate(info["tests"], 1):
            print(f"     {i}. {test}")
        print()

    print("🚀 使用方法:")
    print("   python run_review_tests.py                    # 运行所有测试")
    print("   python run_review_tests.py ReviewManager     # 运行指定测试类")
    print(
        "   python run_review_tests.py ReviewManager test_create_review_session  # 运行指定测试方法"
    )


def main():
    """主函数"""

    if len(sys.argv) == 1:
        # 运行所有测试
        print("🚀 开始运行所有Review功能测试...")
        success = run_all_review_tests()

    elif len(sys.argv) == 2:
        # 运行指定测试类
        test_class = sys.argv[1]
        print(f"🎯 运行测试类: {test_class}")
        success = run_specific_test(test_class)

    elif len(sys.argv) == 3:
        # 运行指定测试方法
        test_class = sys.argv[1]
        test_method = sys.argv[2]
        print(f"🎯 运行测试方法: {test_class}.{test_method}")
        success = run_specific_test(test_class, test_method)

    else:
        # 显示使用说明
        show_test_summary()
        return 0

    # 显示结果
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有测试通过！Review功能运行正常")
        return 0
    else:
        print("❌ 部分测试失败，请检查代码和配置")
        return 1


if __name__ == "__main__":
    exit(main())
