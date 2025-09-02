"""
Review功能测试覆盖率分析

分析测试覆盖的代码路径和功能点
"""

import inspect
from pathlib import Path


def analyze_test_coverage():
    """分析测试覆盖率"""

    # 分析各个模块的测试覆盖情况
    modules_to_analyze = {
        "ods/review/review_manager.py": {
            "class": "ReviewManager",
            "test_file": "tests/test_review/test_review_manager.py",
            "test_class": "TestReviewManager"
        },
        "ods/review/interactive_reviewer.py": {
            "class": "InteractiveReviewer",
            "test_file": "tests/test_review/test_interactive_reviewer.py",
            "test_class": "TestInteractiveReviewer"
        },
        "ods/review/reclassification_workflow.py": {
            "class": "ReclassificationWorkflow",
            "test_file": "tests/test_review/test_reclassification_workflow.py",
            "test_class": "TestReclassificationWorkflow"
        },
        "ods/core/database.py": {
            "class": "Database",
            "test_file": "tests/test_review/test_database_review.py",
            "test_class": "TestDatabaseReview"
        },
        "ods/cli.py": {
            "functions": ["review", "review_stats"],
            "test_file": "tests/test_review/test_cli_review.py",
            "test_class": "TestCLIReview"
        }
    }

    print("📊 Review功能测试覆盖率分析")
    print("=" * 60)

    total_methods = 0
    total_tests = 0

    for module_path, info in modules_to_analyze.items():
        print(f"\n📁 模块: {module_path}")

        try:
            # 分析源代码
            source_methods = analyze_source_methods(module_path, info)
            print(f"   📝 源代码方法数: {len(source_methods)}")

            # 分析测试代码
            test_methods = analyze_test_methods(info["test_file"], info["test_class"])
            print(f"   🧪 测试方法数: {len(test_methods)}")

            # 计算覆盖率
            coverage = calculate_coverage(source_methods, test_methods)
            print(".1f"
            # 详细分析
            print(f"   📋 覆盖的方法: {len(coverage['covered'])}")
            if coverage["missed"]:
                print(f"   ⚠️  未覆盖的方法: {len(coverage['missed'])}")
                for method in coverage["missed"][:5]:  # 只显示前5个
                    print(f"      - {method}")
                if len(coverage["missed"]) > 5:
                    print(f"      ... 还有 {len(coverage['missed']) - 5} 个")

            total_methods += len(source_methods)
            total_tests += len(test_methods)

        except Exception as e:
            print(f"   ❌ 分析失败: {e}")

    print(f"\n{'='*60}")
    print(f"📈 总体统计:")
    print(f"   📝 总源代码方法数: {total_methods}")
    print(f"   🧪 总测试方法数: {total_tests}")
    if total_methods > 0:
        overall_coverage = (total_tests / total_methods) * 100
        print(".1f"        print(f"   🎯 测试建议: {'良好' if overall_coverage >= 80 else '需要改进'}")


def analyze_source_methods(module_path, info):
    """分析源代码中的方法"""

    try:
        # 动态导入模块
        module_parts = module_path.replace(".py", "").split("/")
        module_name = ".".join(module_parts)

        # 特殊处理cli模块
        if "cli" in module_path:
            import ods.cli as cli_module
            module = cli_module
        else:
            module = __import__(module_name, fromlist=[module_parts[-1]])

        methods = []

        if "class" in info:
            # 类方法
            cls = getattr(module, info["class"])
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not name.startswith("_") or name == "__init__":
                    methods.append(name)
        elif "functions" in info:
            # 独立函数
            for func_name in info["functions"]:
                if hasattr(module, func_name):
                    methods.append(func_name)

        return methods

    except Exception as e:
        print(f"分析源代码失败 {module_path}: {e}")
        return []


def analyze_test_methods(test_file, test_class):
    """分析测试代码中的方法"""

    try:
        # 动态导入测试模块
        test_module_path = test_file.replace(".py", "").replace("/", ".")
        test_module = __import__(test_module_path, fromlist=[test_file.split("/")[-1]])

        # 获取测试类
        cls = getattr(test_module, test_class)

        # 获取所有测试方法
        test_methods = []
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("test_"):
                test_methods.append(name)

        return test_methods

    except Exception as e:
        print(f"分析测试代码失败 {test_file}: {e}")
        return []


def calculate_coverage(source_methods, test_methods):
    """计算测试覆盖率"""

    # 提取被测试的方法名（去掉test_前缀）
    tested_methods = set()
    for test_method in test_methods:
        if test_method.startswith("test_"):
            # 简单的启发式方法名匹配
            method_name = test_method[5:]  # 去掉test_

            # 处理驼峰命名
            if "_" in method_name:
                parts = method_name.split("_")
                method_name = parts[0] + "".join(word.capitalize() for word in parts[1:])

            tested_methods.add(method_name)

            # 也添加原始的蛇形命名
            tested_methods.add(method_name.replace("_", ""))

    # 计算覆盖情况
    covered = []
    missed = []

    for method in source_methods:
        if method in tested_methods or any(method in test for test in tested_methods):
            covered.append(method)
        else:
            missed.append(method)

    coverage_rate = (len(covered) / len(source_methods)) * 100 if source_methods else 0

    return {
        "covered": covered,
        "missed": missed,
        "rate": coverage_rate
    }


def show_test_quality_guidelines():
    """显示测试质量指南"""

    print("\n" + "="*60)
    print("📚 Review功能测试质量指南")
    print("="*60)

    guidelines = {
        "单元测试原则": [
            "✅ 每个公共方法都有对应的测试",
            "✅ 测试边界条件和异常情况",
            "✅ 使用mock隔离外部依赖",
            "✅ 测试数据验证和错误处理"
        ],
        "测试覆盖率目标": [
            "🎯 核心业务逻辑: >90%",
            "🎯 错误处理路径: >80%",
            "🎯 用户界面交互: >85%",
            "🎯 数据访问层: >95%"
        ],
        "测试类型建议": [
            "🧪 功能测试 - 验证核心功能正常工作",
            "🧪 边界测试 - 测试极限值和边界条件",
            "🧪 错误测试 - 验证错误处理和异常恢复",
            "🧪 集成测试 - 测试组件间的交互",
            "🧪 性能测试 - 验证大规模数据处理"
        ],
        "测试数据管理": [
            "📊 使用内存数据库进行单元测试",
            "📊 准备多样化的测试数据",
            "📊 测试数据清理和隔离",
            "📊 避免测试间的相互影响"
        ]
    }

    for category, items in guidelines.items():
        print(f"\n{category}:")
        for item in items:
            print(f"   {item}")


def main():
    """主函数"""

    print("🔍 开始Review功能测试覆盖率分析...\n")

    analyze_test_coverage()
    show_test_quality_guidelines()

    print("\n" + "="*60)
    print("💡 改进建议:")
    print("   1. 定期运行测试确保功能稳定性")
    print("   2. 添加更多边界条件和异常情况测试")
    print("   3. 考虑添加性能测试和压力测试")
    print("   4. 建立CI/CD流水线自动化测试执行")
    print("   5. 使用覆盖率工具生成详细报告")


if __name__ == "__main__":
    main()
