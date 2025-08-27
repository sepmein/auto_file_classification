"""
测试增强分类器 - Step 2 多标签支持
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ods.classifiers.enhanced_classifier import EnhancedClassifier


class TestEnhancedClassifier:
    """测试增强分类器"""

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
                "confidence_threshold": {"auto": 0.85, "review": 0.6, "min": 0.3},
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
                    }
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
    def enhanced_classifier(self, sample_config):
        """创建增强分类器实例"""
        with patch("ods.classifiers.enhanced_classifier.DocumentClassifier"), patch(
            "ods.classifiers.enhanced_classifier.LLMClassifier"
        ), patch("ods.classifiers.enhanced_classifier.RetrievalAgent"), patch(
            "ods.classifiers.enhanced_classifier.EnhancedRuleEngine"
        ):

            classifier = EnhancedClassifier(sample_config)

            # Mock the components
            classifier.base_classifier = Mock()
            classifier.llm_classifier = Mock()
            classifier.retrieval_agent = Mock()
            classifier.rule_engine = Mock()

            return classifier

    def test_initialization(self, enhanced_classifier):
        """测试初始化"""
        assert enhanced_classifier.taxonomies is not None
        assert "主类别" in enhanced_classifier.taxonomies
        assert "文档类型" in enhanced_classifier.taxonomies
        assert "敏感级别" in enhanced_classifier.taxonomies

        assert enhanced_classifier.confidence_thresholds is not None
        assert enhanced_classifier.confidence_thresholds["auto"] == 0.85
        assert enhanced_classifier.confidence_thresholds["review"] == 0.6

    def test_classification_status_determination(self, enhanced_classifier):
        """测试分类状态确定"""
        # 高置信度 - 自动分类
        result = {"confidence_score": 0.9}
        status = enhanced_classifier._determine_classification_status(result)
        assert status["status"] == "auto_classified"
        assert not status["needs_review"]

        # 中等置信度 - 需要审核
        result = {"confidence_score": 0.7}
        status = enhanced_classifier._determine_classification_status(result)
        assert status["status"] == "needs_review"
        assert status["needs_review"]

        # 低置信度 - 不确定
        result = {"confidence_score": 0.4}
        status = enhanced_classifier._determine_classification_status(result)
        assert status["status"] == "uncertain"
        assert status["needs_review"]

    def test_sensitive_tag_review(self, enhanced_classifier):
        """测试敏感标签审核"""
        # 机密文件需要审核
        result = {"confidence_score": 0.9, "tags": ["财务", "机密"]}
        status = enhanced_classifier._determine_classification_status(result)
        assert status["status"] == "needs_review"
        assert status["needs_review"]
        assert "包含敏感标签" in status["review_reason"]

    def test_confidence_level_calculation(self, enhanced_classifier):
        """测试置信度等级计算"""
        assert enhanced_classifier._get_confidence_level(0.95) == "very_high"
        assert enhanced_classifier._get_confidence_level(0.85) == "high"
        assert enhanced_classifier._get_confidence_level(0.75) == "medium"
        assert enhanced_classifier._get_confidence_level(0.65) == "low"
        assert enhanced_classifier._get_confidence_level(0.45) == "very_low"

    def test_prompt_building(self, enhanced_classifier):
        """测试提示词构建"""
        doc_data = {
            "file_path": "/path/to/test.pdf",
            "text_content": "这是一份测试文档",
            "file_size": "1024",
        }

        similar_docs = [
            {"filename": "doc1.pdf", "tags": ["工作", "报告"]},
            {"filename": "doc2.pdf", "tags": ["财务", "发票"]},
        ]

        prompt = enhanced_classifier._build_classification_prompt(
            doc_data, similar_docs
        )

        # 检查提示词内容
        assert "文档分类助手" in prompt
        assert "主类别: 工作, 个人, 财务, 其他" in prompt
        assert "文档类型: 报告, 合同, 发票, 照片" in prompt
        assert "敏感级别: 公开, 内部, 机密" in prompt
        assert "test.pdf" in prompt
        assert "相似文档示例" in prompt

    def test_llm_response_parsing(self, enhanced_classifier):
        """测试LLM响应解析"""
        # 有效的JSON响应
        valid_response = """{
            "tags": ["工作", "报告"],
            "confidence_scores": [0.9, 0.8],
            "reasoning": "这是一份工作报告",
            "primary_tag": "工作"
        }"""

        result = enhanced_classifier._parse_llm_response(valid_response)

        assert result["tags"] == ["工作", "报告"]
        assert result["confidence_scores"] == [0.9, 0.8]
        assert result["reasoning"] == "这是一份工作报告"
        assert result["primary_tag"] == "工作"
        assert abs(result["confidence_score"] - 0.85) < 0.001  # 平均值，允许浮点误差

        # 无效响应
        invalid_response = "这不是JSON格式"
        result = enhanced_classifier._parse_llm_response(invalid_response)

        assert result["tags"] == []
        assert result["confidence_score"] == 0.0
        assert "响应解析失败" in result["reasoning"]

    def test_result_validation(self, enhanced_classifier):
        """测试结果验证"""
        # 有效结果
        valid_result = {
            "tags": ["工作", "报告"],
            "primary_tag": "工作",
            "confidence_score": 0.9,
        }

        validation = enhanced_classifier.validate_classification_result(valid_result)
        assert validation["is_valid"]
        assert len(validation["errors"]) == 0

        # 无效结果 - 缺少字段
        invalid_result = {"tags": ["工作"]}

        validation = enhanced_classifier.validate_classification_result(invalid_result)
        assert not validation["is_valid"]
        assert len(validation["errors"]) > 0

        # 无效结果 - 标签不在预定义体系中
        invalid_result = {
            "tags": ["未知标签"],
            "primary_tag": "未知标签",
            "confidence_score": 0.9,
        }

        validation = enhanced_classifier.validate_classification_result(invalid_result)
        assert validation["is_valid"]  # 标签无效只是警告，不是错误
        assert len(validation["warnings"]) > 0

    def test_classification_summary(self, enhanced_classifier):
        """测试分类摘要"""
        summary = enhanced_classifier.get_classification_summary()

        assert "taxonomies" in summary
        assert "confidence_thresholds" in summary
        assert "tag_rules" in summary
        assert "components" in summary

        assert summary["components"]["base_classifier"] == "DocumentClassifier"
        assert summary["components"]["llm_classifier"] == "LLMClassifier"
        assert summary["components"]["rule_engine"] == "EnhancedRuleEngine"

    @patch("ods.classifiers.enhanced_classifier.EnhancedRuleEngine")
    def test_full_classification_flow(self, mock_rule_engine, enhanced_classifier):
        """测试完整分类流程"""
        # Mock rule engine responses
        enhanced_classifier.rule_engine.apply_pre_classification_rules.return_value = {
            "pre_tags": ["发票"],
            "excluded": False,
            "requires_review": False,
        }

        enhanced_classifier.rule_engine.apply_post_classification_rules.return_value = {
            "tags": ["财务", "发票"],
            "primary_tag": "财务",
            "confidence_score": 0.9,
        }

        # Mock retrieval agent
        enhanced_classifier.retrieval_agent.get_document_embedding.return_value = {
            "success": True,
            "embedding": [0.1, 0.2, 0.3],
        }

        enhanced_classifier.retrieval_agent.find_similar_documents.return_value = [
            {"filename": "doc1.pdf", "tags": ["财务", "发票"]}
        ]

        # Mock LLM classifier
        enhanced_classifier.llm_classifier.classify_with_prompt.return_value = """{
            "tags": ["财务", "发票"],
            "confidence_scores": [0.9, 0.8],
            "reasoning": "这是一份发票",
            "primary_tag": "财务"
        }"""

        # Test classification
        doc_data = {"file_path": "/path/to/发票.pdf", "text_content": "这是一份发票"}

        result = enhanced_classifier.classify_document(doc_data)

        # Verify result
        assert result["status"] == "auto_classified"
        assert not result["needs_review"]
        assert "财务" in result["tags"]
        assert "发票" in result["tags"]
        assert result["primary_tag"] == "财务"
        assert result["confidence_score"] == 0.9

        # Verify process was called
        enhanced_classifier.rule_engine.apply_pre_classification_rules.assert_called_once()
        enhanced_classifier.rule_engine.apply_post_classification_rules.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
