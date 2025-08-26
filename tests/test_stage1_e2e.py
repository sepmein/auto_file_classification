"""
Stage 1 MVP 端到端测试

测试整个 Stage 1 文档分类流程的完整功能
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import yaml
import json

from ods.core.config import Config
from ods.core.workflow import DocumentClassificationWorkflow
from ods.parsers.document_parser import DocumentParser
from ods.embeddings.embedder import Embedder
from ods.classifiers.classifier import DocumentClassifier
from ods.path_planner.path_planner import PathPlanner
from ods.naming.renamer import Renamer
from ods.rules.rule_engine import RuleEngine
from ods.storage.file_mover import FileMover
from ods.storage.index_updater import IndexUpdater


class TestStage1EndToEnd:
    """Stage 1 MVP 端到端测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)

        # 创建目录结构
        (workspace / "source").mkdir()
        (workspace / "target").mkdir()
        (workspace / "config").mkdir()
        (workspace / "data").mkdir()

        # 创建测试文件
        test_files = {
            "source/工作报告.txt": "这是一份工作项目的季度报告，包含了项目进展和业务数据。",
            "source/发票_202310.pdf": "发票\n金额：1000元\n税务编号：123456\n公司财务报销单据",
            "source/个人日记.txt": "今天是个美好的日子，和家人一起旅行，拍了很多照片。",
            "source/合同文件.docx": "合同条款\n甲方：ABC公司\n乙方：XYZ公司\n工作协议内容",
            "source/unknown.txt": "这是一些无法明确分类的内容",
        }

        for file_path, content in test_files.items():
            full_path = workspace / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        yield workspace

        # 清理
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def test_config(self, temp_workspace):
        """创建测试配置"""
        config_data = {
            "llm": {"provider": "mock", "model": "test-model", "temperature": 0.1},
            "embedding": {
                "type": "mock",
                "model_name": "test-embedding",
                "device": "cpu",
            },
            "database": {
                "type": "sqlite",
                "path": str(temp_workspace / "data" / "test.db"),
                "sqlite_path": str(temp_workspace / "data" / "audit.db"),
            },
            "vector_store": {
                "chroma_path": str(temp_workspace / "data" / "chroma"),
                "collection_name": "test_documents",
            },
            "classification": {
                "categories": ["工作", "个人", "财务", "其他"],
                "confidence_threshold": 0.8,
                "review_threshold": 0.6,
            },
            "file": {
                "source_directory": str(temp_workspace / "source"),
                "target_directory": str(temp_workspace / "target"),
                "supported_extensions": [".txt", ".pdf", ".docx"],
            },
            "path_planning": {
                "base_path": str(temp_workspace / "target"),
                "path_template": "{category}",
            },
            "naming": {
                "default_template": "{{category}}-{{original_name}}.{{ext}}",
                "max_filename_length": 200,
            },
            "system": {
                "dry_run": False,
                "temp_directory": str(temp_workspace / "temp"),
            },
        }

        # 保存配置文件
        config_file = temp_workspace / "config.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)

        return config_data, str(config_file)

    def test_individual_components(self, test_config, temp_workspace):
        """测试各个组件的基本功能"""
        config_data, config_file = test_config

        # 测试文档解析器
        parser = DocumentParser(config_data)
        parse_result = parser.parse(temp_workspace / "source/工作报告.txt")
        assert parse_result.success
        assert "工作项目" in parse_result.content.text

        # 测试配置管理
        config = Config(config_file)
        assert config.classification.categories == ["工作", "个人", "财务", "其他"]

        # 测试路径规划器（无需嵌入/分类结果）
        path_planner = PathPlanner(config_data)
        classification_result = {"primary_category": "工作", "confidence_score": 0.9}
        path_plan = path_planner.plan_file_path(
            classification_result,
            str(temp_workspace / "source/工作报告.txt"),
            {"file_type": "txt"},
        )
        assert path_plan["status"] == "planned"
        assert "工作" in path_plan["primary_path"]

        # 测试命名生成器
        renamer = Renamer(config_data)
        naming_result = renamer.generate_filename(
            path_plan,
            {
                "file_path": str(temp_workspace / "source/工作报告.txt"),
                "text_content": "测试内容",
            },
            classification_result,
        )
        assert naming_result["status"] == "generated"
        assert "工作" in naming_result["new_filename"]

        # 测试规则引擎
        rule_engine = RuleEngine(config_data)
        rules_result = rule_engine.apply_rules(
            classification_result,
            {
                "file_path": str(temp_workspace / "source/工作报告.txt"),
                "text_content": "这是一份工作项目的季度报告",
            },
        )
        assert "rules_applied" in rules_result

    @patch("ods.embeddings.models.LocalEmbeddingModel")
    @patch("ods.classifiers.classifier.LLMClassifier")
    @patch("ods.classifiers.classifier.RuleChecker")
    def test_mock_embedding_and_classification(
        self, mock_rule_checker, mock_llm, mock_embedding, test_config, temp_workspace
    ):
        """测试嵌入和分类功能（使用模拟）"""
        config_data, config_file = test_config

        # 设置模拟嵌入模型
        mock_embedding_instance = Mock()
        mock_embedding_instance.is_available.return_value = True
        mock_embedding_instance.encode.return_value = [0.1] * 1024  # 模拟1024维向量
        mock_embedding_instance.get_dimension.return_value = 1024
        mock_embedding_instance.get_model_info.return_value = {
            "type": "mock",
            "dimension": 1024,
        }
        mock_embedding.return_value = mock_embedding_instance

        # 设置模拟LLM分类器
        mock_llm_instance = Mock()
        mock_llm_instance.classify_document.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_llm.return_value = mock_llm_instance

        # 设置模拟规则检查器
        mock_rule_checker_instance = Mock()
        mock_rule_checker_instance.apply_rules.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_rule_checker.return_value = mock_rule_checker_instance

        # 测试嵌入生成器
        embedder = Embedder(config_data)
        document_data = {
            "file_path": str(temp_workspace / "source/工作报告.txt"),
            "text_content": "这是一份工作项目的季度报告，包含了项目进展和业务数据。",
            "metadata": {},
        }

        embedding_result = embedder.process_document(document_data)
        assert embedding_result["status"] == "success"
        assert embedding_result["embedding_dimension"] == 1024
        assert len(embedding_result["embedding"]) == 1024

        # 测试分类器
        classifier = DocumentClassifier(config_data)
        document_data["embedding"] = embedding_result["embedding"]
        classification_result = classifier.classify_document(document_data)
        assert classification_result["primary_category"] == "工作"
        assert classification_result["confidence_score"] == 0.85

    @patch("ods.embeddings.models.LocalEmbeddingModel")
    @patch("ods.classifiers.classifier.LLMClassifier")
    @patch("ods.classifiers.classifier.RuleChecker")
    @patch("ods.storage.file_mover.FileMover.move_file")
    @patch("ods.core.workflow.DocumentClassifier")
    @patch("ods.core.workflow.Embedder")
    @patch("ods.core.workflow.RuleEngine")
    def test_complete_workflow(
        self,
        mock_rule_engine,
        mock_embedder,
        mock_classifier,
        mock_move_file,
        mock_rule_checker,
        mock_llm,
        mock_embedding,
        test_config,
        temp_workspace,
    ):
        """测试完整的工作流程"""
        config_data, config_file = test_config

        # 设置模拟嵌入模型
        mock_embedding_instance = Mock()
        mock_embedding_instance.is_available.return_value = True
        mock_embedding_instance.encode.return_value = [0.1] * 1024
        mock_embedding_instance.get_dimension.return_value = 1024
        mock_embedding_instance.get_model_info.return_value = {
            "type": "mock",
            "dimension": 1024,
        }
        mock_embedding.return_value = mock_embedding_instance

        # 设置模拟LLM分类器
        mock_llm_instance = Mock()
        mock_llm_instance.classify_document.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_llm.return_value = mock_llm_instance

        # 设置模拟规则检查器
        mock_rule_checker_instance = Mock()
        mock_rule_checker_instance.apply_rules.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_rule_checker.return_value = mock_rule_checker_instance

        # 设置模拟嵌入器
        mock_embedder_instance = Mock()
        mock_embedder_instance.process_document.return_value = {
            "status": "success",
            "embedding": [0.1] * 1024,
            "summary": "工作项目季度报告",
            "keywords": ["工作", "项目", "报告"],
            "embedding_metadata": {"dimension": 1024},
        }
        mock_embedder.return_value = mock_embedder_instance

        # 设置模拟规则引擎
        mock_rule_engine_instance = Mock()
        mock_rule_engine_instance.apply_rules.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_rule_engine.return_value = mock_rule_engine_instance

        # 设置模拟分类器
        mock_classifier_instance = Mock()
        mock_classifier_instance.classify_document.return_value = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "reasoning": "文档内容涉及工作项目",
            "classification_timestamp": "2023-01-01T00:00:00",
        }
        mock_classifier.return_value = mock_classifier_instance

        # 设置模拟文件移动
        mock_move_file.return_value = {
            "old_path": str(temp_workspace / "source/工作报告.txt"),
            "primary_target_path": str(
                temp_workspace / "target/工作/工作-工作报告.txt"
            ),
            "moved": True,
            "link_creations": [],
            "errors": [],
        }

        # 创建工作流
        workflow = DocumentClassificationWorkflow(config_data)

        # 处理文件
        test_file = temp_workspace / "source/工作报告.txt"
        result = workflow.process_file(test_file)

        # 验证结果
        assert result["parse_success"] == True
        assert result["embedding_success"] == True
        assert result["classify_success"] == True
        assert result["plan_success"] == True
        assert result["naming_success"] == True
        assert result["rules_success"] == True
        assert result["move_success"] == True

        # 验证分类结果
        classification = result["classification"]
        assert classification["primary_category"] == "工作"
        assert classification["confidence_score"] == 0.85

        # 验证路径规划
        path_plan = result["path_plan"]
        assert "工作" in path_plan["primary_path"]

        # 验证命名结果
        naming_result = result["naming_result"]
        assert "工作" in naming_result["new_filename"]

    def test_file_type_classification_rules(self, test_config, temp_workspace):
        """测试基于文件类型和内容的分类规则"""
        config_data, config_file = test_config

        rule_engine = RuleEngine(config_data)

        test_cases = [
            {
                "file_path": "invoice_001.pdf",
                "content": "发票 金额 税务",
                "expected_category": "财务",
            },
            {
                "file_path": "contract.docx",
                "content": "合同 协议 工作",
                "expected_category": "工作",
            },
            {
                "file_path": "photo.jpg",
                "content": "个人 家庭 照片",
                "expected_category": "个人",
            },
        ]

        for case in test_cases:
            # 模拟LLM分类结果
            classification_result = {
                "primary_category": "其他",
                "confidence_score": 0.5,
            }

            document_data = {
                "file_path": case["file_path"],
                "text_content": case["content"],
            }

            # 应用规则
            updated_result = rule_engine.apply_rules(
                classification_result, document_data
            )

            # 验证规则是否正确应用
            assert len(updated_result.get("rules_applied", [])) > 0

    def test_error_handling(self, test_config, temp_workspace):
        """测试错误处理"""
        config_data, config_file = test_config

        # 测试不存在的文件
        workflow = DocumentClassificationWorkflow(config_data)
        non_existent_file = temp_workspace / "source/non_existent.txt"

        result = workflow.process_file(non_existent_file)
        assert result["parse_success"] == False
        assert "error" in result

    def test_configuration_validation(self, test_config):
        """测试配置验证"""
        config_data, config_file = test_config

        # 测试配置加载
        config = Config(config_file)
        assert config.classification.categories == ["工作", "个人", "财务", "其他"]
        assert config.classification.confidence_threshold == 0.8
        assert config.classification.review_threshold == 0.6

        # 测试配置字典
        config_dict = config.get_config_dict()
        assert "classification" in config_dict
        assert "file" in config_dict
        assert "embedding" in config_dict

    @patch("ods.embeddings.models.LocalEmbeddingModel")
    @patch("ods.classifiers.llm_classifier.LLMClassifier")
    def test_confidence_based_review(
        self, mock_llm, mock_embedding, test_config, temp_workspace
    ):
        """测试基于置信度的审核机制"""
        config_data, config_file = test_config

        # 设置模拟返回低置信度结果
        mock_embedding_instance = Mock()
        mock_embedding_instance.is_available.return_value = True
        mock_embedding_instance.encode.return_value = [0.1] * 1024
        mock_embedding_instance.get_dimension.return_value = 1024
        mock_embedding_instance.get_model_info.return_value = {"type": "mock"}
        mock_embedding.return_value = mock_embedding_instance

        mock_llm_instance = Mock()
        mock_llm_instance.classify_document.return_value = {
            "primary_category": "其他",
            "confidence_score": 0.4,  # 低于review_threshold (0.6)
            "reasoning": "内容不明确",
        }
        mock_llm.return_value = mock_llm_instance

        # 测试规则引擎对低置信度的处理
        rule_engine = RuleEngine(config_data)
        classification_result = {"primary_category": "其他", "confidence_score": 0.4}

        updated_result = rule_engine.apply_rules(
            classification_result, {"file_path": "test.txt", "text_content": "模糊内容"}
        )

        # 验证是否标记为需要审核
        assert updated_result.get("needs_review") == True
        assert "review_reason" in updated_result

    def test_multiple_file_processing(self, test_config, temp_workspace):
        """测试多文件处理"""
        config_data, config_file = test_config

        # 使用真实的文档解析器测试多个文件
        parser = DocumentParser(config_data)

        source_dir = temp_workspace / "source"
        files = list(source_dir.glob("*.txt"))

        assert len(files) >= 3  # 确保有足够的测试文件

        # 测试批量解析
        results = []
        for file_path in files:
            try:
                result = parser.parse(file_path)
                results.append(
                    {
                        "file": str(file_path),
                        "success": result.success,
                        "content_length": (
                            len(result.content.text) if result.success else 0
                        ),
                    }
                )
            except Exception as e:
                results.append(
                    {"file": str(file_path), "success": False, "error": str(e)}
                )

        # 验证所有文件都被处理
        assert len(results) == len(files)
        success_count = sum(1 for r in results if r["success"])
        assert success_count > 0  # 至少有一些文件成功解析

    def test_component_integration(self, test_config, temp_workspace):
        """测试组件集成"""
        config_data, config_file = test_config

        # 创建所有组件实例
        components = {
            "parser": DocumentParser(config_data),
            "path_planner": PathPlanner(config_data),
            "renamer": Renamer(config_data),
            "rule_engine": RuleEngine(config_data),
        }

        # 验证所有组件都能正确初始化
        for name, component in components.items():
            assert component is not None, f"{name} 组件初始化失败"

        # 测试组件间的数据流
        test_file = temp_workspace / "source/工作报告.txt"

        # 1. 解析文档
        parse_result = components["parser"].parse(test_file)
        assert parse_result.success

        # 2. 模拟分类结果
        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.85,
            "tags": ["工作", "报告"],
        }

        # 3. 规划路径
        path_plan = components["path_planner"].plan_file_path(
            classification_result, str(test_file), {"file_type": "txt"}
        )
        assert path_plan["status"] == "planned"

        # 4. 生成命名
        document_data = {
            "file_path": str(test_file),
            "text_content": parse_result.content.text,
            "metadata": {},
        }
        naming_result = components["renamer"].generate_filename(
            path_plan, document_data, classification_result
        )
        assert naming_result["status"] == "generated"

        # 5. 应用规则
        updated_classification = components["rule_engine"].apply_rules(
            classification_result, document_data
        )
        assert "rules_applied" in updated_classification


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
