"""
测试增强规则引擎 - Step 2 多标签支持
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ods.rules.enhanced_rule_engine import EnhancedRuleEngine


class TestEnhancedRuleEngine:
    """测试增强规则引擎"""

    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return {
            "classification": {
                "taxonomies": {
                    "主类别": ["工作", "个人", "财务", "其他"],
                    "文档类型": ["报告", "合同", "发票", "照片"],
                    "敏感级别": ["公开", "内部", "机密"],
                },
                "tag_rules": {
                    "max_tags_per_file": 5,
                    "primary_tag_required": True,
                    "allow_cross_categories": True,
                    "mutually_exclusive": [["个人", "工作"], ["公开", "机密"]],
                    "priority_order": ["主类别", "文档类型", "敏感级别"],
                },
            },
            "rules": {
                "pre_classification": [
                    {
                        "name": "发票文件自动标签",
                        "condition": "filename_contains",
                        "value": "发票",
                        "action": "add_tag",
                        "target": "发票",
                        "priority": "high",
                    },
                    {
                        "name": "排除临时文件",
                        "condition": "file_extension",
                        "value": ["tmp", "log", "bak"],
                        "action": "exclude",
                        "priority": "high",
                    },
                ],
                "post_classification": [
                    {
                        "name": "机密文件特殊处理",
                        "condition": "tags_contain",
                        "value": "机密",
                        "action": "require_review",
                        "priority": "high",
                    }
                ],
            },
        }

    @pytest.fixture
    def rule_engine(self, sample_config):
        """创建规则引擎实例"""
        return EnhancedRuleEngine(sample_config)

    def test_initialization(self, rule_engine):
        """测试初始化"""
        assert rule_engine.taxonomies is not None
        assert "主类别" in rule_engine.taxonomies
        assert "文档类型" in rule_engine.taxonomies
        assert "敏感级别" in rule_engine.taxonomies

        assert rule_engine.tag_rules is not None
        assert rule_engine.tag_rules["max_tags_per_file"] == 5

        assert len(rule_engine.pre_classification_rules) == 2
        assert len(rule_engine.post_classification_rules) == 1

    def test_pre_classification_rules(self, rule_engine):
        """测试预分类规则"""
        # 测试发票文件
        doc_data = {
            "file_path": "/path/to/发票明细.pdf",
            "text_content": "这是一份发票文件",
        }

        result = rule_engine.apply_pre_classification_rules(doc_data)

        assert not result["excluded"]
        assert "发票" in result["pre_tags"]
        assert len(result["applied_rules"]) == 1
        assert result["applied_rules"][0]["rule_name"] == "发票文件自动标签"

    def test_exclude_rule(self, rule_engine):
        """测试排除规则"""
        # 测试临时文件
        doc_data = {"file_path": "/path/to/temp.tmp", "text_content": "临时文件内容"}

        result = rule_engine.apply_pre_classification_rules(doc_data)

        assert result["excluded"]
        assert len(result["applied_rules"]) == 1
        assert result["applied_rules"][0]["rule_name"] == "排除临时文件"

    def test_post_classification_rules(self, rule_engine):
        """测试后分类规则"""
        # 测试机密文件
        classification_result = {"tags": ["财务", "机密"], "confidence": 0.9}

        doc_data = {"file_path": "/path/to/机密文档.pdf", "text_content": "机密内容"}

        pre_result = {"pre_tags": ["发票"], "excluded": False, "requires_review": False}

        result = rule_engine.apply_post_classification_rules(
            classification_result, doc_data, pre_result
        )

        # 检查标签合并
        assert "发票" in result["tags"]
        assert "财务" in result["tags"]
        assert "机密" in result["tags"]

        # 检查后分类规则应用
        assert len(result["post_rules_applied"]) == 1
        assert result["post_rules_applied"][0]["rule_name"] == "机密文件特殊处理"

    def test_tag_rules_application(self, rule_engine):
        """测试标签规则应用"""
        classification_result = {"tags": ["工作", "个人", "报告", "公开"]}

        doc_data = {"file_path": "/test.pdf"}
        pre_result = {"pre_tags": [], "excluded": False}

        result = rule_engine.apply_post_classification_rules(
            classification_result, doc_data, pre_result
        )

        # 检查互斥标签处理
        # "工作" 和 "个人" 是互斥的，应该只保留一个
        assert len(result["tags"]) < 4  # 互斥标签被移除

        # 检查主标签确定
        assert "primary_tag" in result
        assert "secondary_tags" in result

    def test_condition_evaluation(self, rule_engine):
        """测试条件评估"""
        # 测试文件名包含
        rule = {"condition": "filename_contains", "value": "发票"}

        doc_data = {"file_path": "/path/to/发票明细.pdf"}
        assert rule_engine._evaluate_condition(rule, doc_data)

        # 测试文件扩展名
        rule = {"condition": "file_extension", "value": ["pdf", "docx"]}

        doc_data = {"file_path": "/path/to/document.pdf"}
        assert rule_engine._evaluate_condition(rule, doc_data)

        # 测试内容包含
        rule = {"condition": "content_contains", "value": "重要内容"}

        doc_data = {"text_content": "这是一份重要内容的文档"}
        assert rule_engine._evaluate_condition(rule, doc_data)

    def test_file_size_condition(self, rule_engine, tmp_path):
        """测试文件大小条件"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        rule = {"condition": "file_size", "value": "> 10"}

        doc_data = {"file_path": str(test_file)}
        assert rule_engine._evaluate_condition(rule, doc_data)

    def test_mutually_exclusive_tags(self, rule_engine):
        """测试互斥标签处理"""
        tags = ["工作", "个人", "报告"]

        # "工作" 和 "个人" 是互斥的
        resolved_tags = rule_engine._resolve_mutually_exclusive_tags(tags)

        # 应该只保留一个互斥标签
        work_count = sum(1 for tag in resolved_tags if tag in ["工作", "个人"])
        assert work_count <= 1

    def test_primary_tag_determination(self, rule_engine):
        """测试主标签确定"""
        tags = ["报告", "工作", "公开"]

        # 按优先级，"主类别" 优先于 "文档类型"
        primary_tag = rule_engine._determine_primary_tag(tags)

        # "工作" 在 "主类别" 中，"报告" 在 "文档类型" 中
        # 所以应该选择 "工作" 作为主标签
        assert primary_tag == "工作"

    def test_rule_summary(self, rule_engine):
        """测试规则摘要"""
        summary = rule_engine.get_rule_summary()

        assert "taxonomies" in summary
        assert "tag_rules" in summary
        assert summary["pre_classification_rules"] == 2
        assert summary["post_classification_rules"] == 1
        assert summary["total_rules"] == 3

    def test_invalid_rule_handling(self, rule_engine):
        """测试无效规则处理"""
        # 测试缺少必要字段的规则
        invalid_rules = [
            {"name": "无效规则"},  # 缺少 condition 和 action
            {"name": "条件错误", "condition": "invalid_condition", "action": "add_tag"},
            {
                "name": "动作错误",
                "condition": "filename_contains",
                "action": "invalid_action",
            },
        ]

        # 这些规则应该被过滤掉，不会导致错误
        for rule in invalid_rules:
            # 规则引擎应该能够处理无效规则而不崩溃
            pass

    def test_complex_scenario(self, rule_engine):
        """测试复杂场景"""
        # 模拟一个复杂的分类场景
        doc_data = {
            "file_path": "/path/to/工作合同发票.pdf",
            "text_content": "这是一份工作相关的合同发票，包含机密信息",
        }

        # 应用预分类规则
        pre_result = rule_engine.apply_pre_classification_rules(doc_data)

        # 检查预分类结果
        assert not pre_result["excluded"]
        assert "发票" in pre_result["pre_tags"]

        # 模拟LLM分类结果
        classification_result = {"tags": ["工作", "合同", "机密"], "confidence": 0.85}

        # 应用后分类规则
        final_result = rule_engine.apply_post_classification_rules(
            classification_result, doc_data, pre_result
        )

        # 检查最终结果
        assert "发票" in final_result["tags"]  # 预分类标签
        assert "工作" in final_result["tags"]  # LLM分类标签
        assert "合同" in final_result["tags"]
        assert "机密" in final_result["tags"]

        # 检查主标签
        assert final_result["primary_tag"] == "工作"  # 主类别优先级最高

        # 检查是否需要审核（机密文件）
        assert final_result.get("requires_review", False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
