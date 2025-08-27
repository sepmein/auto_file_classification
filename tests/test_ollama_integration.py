"""
测试Ollama集成 - Step 2 Ollama阅读和分类
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from ods.parsers.ollama_reader import OllamaReader
from ods.classifiers.ollama_classifier import OllamaClassifier
from ods.core.enhanced_workflow import EnhancedWorkflow


class TestOllamaIntegration:
    """测试Ollama集成"""

    @pytest.fixture
    def ollama_config(self):
        """Ollama配置"""
        return {
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "qwen3",
                "reader_model": "qwen3",
                "classifier_model": "qwen2.5:7b",
                "timeout": 120,
                "max_retries": 3,
                "enable_reader": True,
                "enable_insights": True,
                "context_window": 4096,
            },
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
    def ollama_reader(self, ollama_config):
        """创建Ollama阅读器"""
        with patch("ods.parsers.ollama_reader.requests"):
            reader = OllamaReader(ollama_config)
            return reader

    @pytest.fixture
    def ollama_classifier(self, ollama_config):
        """创建Ollama分类器"""
        with patch("ods.classifiers.ollama_classifier.requests"), patch(
            "ods.classifiers.enhanced_classifier.DocumentClassifier"
        ), patch("ods.classifiers.enhanced_classifier.LLMClassifier"), patch(
            "ods.classifiers.enhanced_classifier.RetrievalAgent"
        ), patch(
            "ods.classifiers.enhanced_classifier.EnhancedRuleEngine"
        ):

            classifier = OllamaClassifier(ollama_config)

            # Mock components
            classifier.base_classifier = Mock()
            classifier.llm_classifier = Mock()
            classifier.retrieval_agent = Mock()
            classifier.rule_engine = Mock()

            return classifier

    def test_ollama_reader_initialization(self, ollama_reader):
        """测试Ollama阅读器初始化"""
        assert ollama_reader.model == "qwen3"
        assert ollama_reader.base_url == "http://localhost:11434"
        assert ollama_reader.enable_summary is True
        assert ollama_reader.enable_keywords is True
        assert ollama_reader.max_summary_length == 200
        assert ollama_reader.max_keywords == 10

    def test_ollama_classifier_initialization(self, ollama_classifier):
        """测试Ollama分类器初始化"""
        assert ollama_classifier.model == "qwen2.5:7b"
        assert ollama_classifier.base_url == "http://localhost:11434"
        assert "主类别" in ollama_classifier.taxonomies
        assert "文档类型" in ollama_classifier.taxonomies
        assert "敏感级别" in ollama_classifier.taxonomies

    @patch("ods.parsers.ollama_reader.requests.post")
    def test_ollama_reader_read_document(self, mock_post, ollama_reader):
        """测试Ollama阅读器文档处理"""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """{
            "document_type": "发票",
            "main_topic": "财务发票",
            "summary": "这是一份财务发票文档",
            "key_points": ["发票金额", "付款日期"],
            "keywords": ["发票", "财务", "付款"],
            "sentiment": "中性",
            "complexity": "简单",
            "language": "中文",
            "confidence": 0.9
        }"""
        }

        mock_post.return_value = mock_response

        # Test document reading
        file_path = "/path/to/invoice.pdf"
        raw_content = "发票内容：金额1000元，日期2024-01-01"

        result = ollama_reader.read_document(file_path, raw_content)

        assert result["ollama_processed"] is True
        assert "enhanced_content" in result
        assert result["enhanced_content"]["document_type"] == "发票"
        assert result["enhanced_content"]["main_topic"] == "财务发票"
        assert result["enhanced_content"]["summary"] == "这是一份财务发票文档"
        assert "发票" in result["enhanced_content"]["keywords"]

    @patch("ods.classifiers.ollama_classifier.requests.post")
    def test_ollama_classifier_classify(self, mock_post, ollama_classifier):
        """测试Ollama分类器文档分类"""
        # Mock Ollama response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """{
            "tags": ["财务", "发票"],
            "confidence_scores": [0.9, 0.8],
            "primary_tag": "财务",
            "reasoning": "这是财务相关的发票文档",
            "confidence_score": 0.85,
            "taxonomy_breakdown": {
                "主类别": ["财务"],
                "文档类型": ["发票"],
                "敏感级别": ["公开"]
            }
        }"""
        }

        mock_post.return_value = mock_response

        # Mock enhanced classifier
        ollama_classifier.rule_engine.apply_post_classification_rules.return_value = {
            "tags": ["财务", "发票"],
            "primary_tag": "财务",
            "confidence_score": 0.85,
            "status": "auto_classified",
            "needs_review": False,
        }

        # Test classification
        document_data = {
            "file_path": "/path/to/invoice.pdf",
            "text_content": "发票内容",
            "ollama_content": {"document_type": "发票", "main_topic": "财务发票"},
        }

        result = ollama_classifier.classify_document(document_data)

        assert result["ollama_processed"] is True
        assert "财务" in result["tags"]
        assert "发票" in result["tags"]
        assert result["primary_tag"] == "财务"
        assert result["confidence_score"] == 0.85

    def test_ollama_classifier_fallback(self, ollama_classifier):
        """测试Ollama分类器回退机制"""
        # Mock Ollama failure
        ollama_classifier._call_ollama = Mock(return_value=None)

        # Mock enhanced classifier as fallback
        with patch.object(
            ollama_classifier.enhanced_classifier,
            "classify_document",
            return_value={
                "tags": ["其他"],
                "primary_tag": "其他",
                "confidence_score": 0.5,
                "status": "auto_classified",
                "needs_review": False,
            },
        ):
            document_data = {
                "file_path": "/path/to/unknown.pdf",
                "text_content": "未知内容",
            }

            result = ollama_classifier.classify_document(document_data)

            # Should fallback to enhanced classifier
            assert result["primary_tag"] == "其他"

    def test_ollama_reader_fallback(self, ollama_reader):
        """测试Ollama阅读器回退机制"""
        # Mock Ollama failure
        ollama_reader._call_ollama = Mock(return_value=None)

        file_path = "/path/to/document.pdf"
        raw_content = "原始文档内容"

        result = ollama_reader.read_document(file_path, raw_content)

        # Should provide fallback result
        assert result["ollama_processed"] is False
        assert "enhanced_content" in result
        assert result["original_content"] == raw_content

    def test_batch_classification(self, ollama_classifier):
        """测试批量分类"""
        # Mock single classification
        ollama_classifier.classify_document = Mock(
            return_value={
                "tags": ["财务"],
                "primary_tag": "财务",
                "confidence_score": 0.9,
                "status": "auto_classified",
                "needs_review": False,
            }
        )

        documents = [
            {"file_path": "/path/to/doc1.pdf", "text_content": "content1"},
            {"file_path": "/path/to/doc2.pdf", "text_content": "content2"},
        ]

        results = ollama_classifier.batch_classify(documents)

        assert len(results) == 2
        assert all("primary_tag" in result for result in results)

    def test_classifier_comparison(self, ollama_classifier):
        """测试分类器比较"""
        # Mock both classifiers
        with patch.object(
            ollama_classifier,
            "classify_document",
            return_value={
                "tags": ["财务", "发票"],
                "primary_tag": "财务",
                "confidence_score": 0.9,
            },
        ), patch.object(
            ollama_classifier.enhanced_classifier,
            "classify_document",
            return_value={
                "tags": ["财务"],
                "primary_tag": "财务",
                "confidence_score": 0.8,
            },
        ):
            document_data = {"file_path": "/test.pdf", "text_content": "test"}

            comparison = ollama_classifier.compare_with_enhanced(document_data)

            assert "ollama_result" in comparison
            assert "enhanced_result" in comparison
            assert "comparison" in comparison

            comp = comparison["comparison"]
            assert comp["ollama_tags"] == ["财务", "发票"]
            assert comp["enhanced_tags"] == ["财务"]
            assert comp["ollama_confidence"] == 0.9
            assert comp["enhanced_confidence"] == 0.8

    def test_ollama_prompt_building(self, ollama_classifier):
        """测试Ollama提示词构建"""
        document_data = {
            "file_path": "/path/to/test.pdf",
            "text_content": "测试文档内容",
            "ollama_content": {"document_type": "报告", "main_topic": "测试主题"},
        }

        similar_docs = [{"filename": "doc1.pdf", "tags": ["工作", "报告"]}]

        prompt = ollama_classifier._build_classification_prompt(document_data)

        # Check prompt content
        assert "文档分类专家" in prompt
        assert "主类别: 工作, 个人, 财务, 其他" in prompt
        assert "文档类型: 报告, 合同, 发票, 照片" in prompt
        assert "敏感级别: 公开, 内部, 机密" in prompt
        assert "test.pdf" in prompt
        assert "测试文档内容" in prompt

    def test_enhanced_workflow_initialization(self, ollama_config):
        """测试增强工作流初始化"""
        with patch("ods.core.enhanced_workflow.DocumentParser") as mock_parser, patch(
            "ods.core.enhanced_workflow.OllamaReader"
        ) as mock_reader, patch(
            "ods.core.enhanced_workflow.Embedder"
        ) as mock_embedder, patch(
            "ods.core.enhanced_workflow.EnhancedClassifier"
        ) as mock_enhanced_classifier, patch(
            "ods.core.enhanced_workflow.OllamaClassifier"
        ) as mock_ollama_classifier, patch(
            "ods.core.enhanced_workflow.PathPlanner"
        ) as mock_planner, patch(
            "ods.core.enhanced_workflow.Renamer"
        ) as mock_renamer, patch(
            "ods.core.enhanced_workflow.EnhancedRuleEngine"
        ) as mock_rule_engine, patch(
            "ods.core.enhanced_workflow.FileMover"
        ) as mock_mover, patch(
            "ods.core.enhanced_workflow.IndexUpdater"
        ) as mock_updater:

            # Mock Ollama availability
            with patch("ods.core.enhanced_workflow.requests") as mock_requests:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_requests.get.return_value = mock_response

                workflow = EnhancedWorkflow(ollama_config)

                assert workflow.ollama_reader is not None
                assert workflow.ollama_classifier is not None

                summary = workflow.get_workflow_summary()
                assert summary["ollama_reader_enabled"] is True
                assert summary["ollama_classifier_enabled"] is True
                assert summary["workflow_type"] == "enhanced"

    def test_workflow_without_ollama(self, ollama_config):
        """测试没有Ollama时的增强工作流"""
        # Disable Ollama
        ollama_config["ollama"]["enable_reader"] = False

        with patch("ods.core.enhanced_workflow.DocumentParser") as mock_parser, patch(
            "ods.core.enhanced_workflow.OllamaReader"
        ) as mock_reader, patch(
            "ods.core.enhanced_workflow.Embedder"
        ) as mock_embedder, patch(
            "ods.core.enhanced_workflow.EnhancedClassifier"
        ) as mock_enhanced_classifier, patch(
            "ods.core.enhanced_workflow.OllamaClassifier"
        ) as mock_ollama_classifier, patch(
            "ods.core.enhanced_workflow.PathPlanner"
        ) as mock_planner, patch(
            "ods.core.enhanced_workflow.Renamer"
        ) as mock_renamer, patch(
            "ods.core.enhanced_workflow.EnhancedRuleEngine"
        ) as mock_rule_engine, patch(
            "ods.core.enhanced_workflow.FileMover"
        ) as mock_mover, patch(
            "ods.core.enhanced_workflow.IndexUpdater"
        ) as mock_updater:

            # Mock Ollama unavailability
            with patch("ods.core.enhanced_workflow.requests") as mock_requests:
                mock_requests.get.side_effect = Exception("Connection failed")

                workflow = EnhancedWorkflow(ollama_config)

                assert workflow.ollama_reader is None
                assert workflow.ollama_classifier is None

                summary = workflow.get_workflow_summary()
                assert summary["ollama_reader_enabled"] is False
                assert summary["ollama_classifier_enabled"] is False

    def test_ollama_reader_insights(self, ollama_reader):
        """测试Ollama阅读器洞察提取"""
        with patch.object(ollama_reader, "_call_ollama") as mock_call:
            mock_call.return_value = """{
                "entities": ["张三", "李四"],
                "relationships": ["合作关系"],
                "action_items": ["完成任务"],
                "important_dates": ["2024-01-01"],
                "numbers_and_amounts": ["1000元"]
            }"""

            content = "张三和李四合作项目，金额1000元，截止日期2024-01-01"
            insights = ollama_reader.extract_document_insights(content)

            assert "entities" in insights
            assert "张三" in insights["entities"]
            assert "李四" in insights["entities"]
            assert "relationships" in insights
            assert "action_items" in insights
            assert "important_dates" in insights
            assert "numbers_and_amounts" in insights


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
