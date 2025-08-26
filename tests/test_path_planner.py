import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from ods.path_planner.path_planner import PathPlanner


class TestPathPlanner:
    """路径规划器测试"""

    def setup_method(self):
        """测试前准备"""
        self.config = {
            "path_planning": {
                "base_path": "test_output",
                "default_categories": ["工作", "个人", "财务", "其他"],
                "multi_label_strategy": "primary_with_links",
                "path_template": "{category}/{year}/{month}",
                "conflict_resolution": "suffix",
                "max_path_length": 260,
                "category_mapping_file": "test_category_mapping.yaml",
                "special_paths": {
                    "uncategorized": "待整理",
                    "needs_review": "待审核",
                    "important": "重要文件",
                    "archive": "归档",
                },
            },
            "classification": {"review_threshold": 0.6},
        }

        self.path_planner = PathPlanner(self.config)

    def test_init(self):
        """测试初始化"""
        assert self.path_planner.base_path == "test_output"
        assert self.path_planner.default_categories == ["工作", "个人", "财务", "其他"]
        assert self.path_planner.multi_label_strategy == "primary_with_links"

    def test_plan_file_path_success(self):
        """测试成功的路径规划"""
        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.9,
            "tags": ["工作", "项目A"],
        }

        original_path = "/test/document.pdf"
        file_metadata = {"file_size": 1024, "file_type": "pdf"}

        result = self.path_planner.plan_file_path(
            classification_result, original_path, file_metadata
        )

        assert result["status"] == "planned"
        assert result["category"] == "工作"
        assert "primary_path" in result
        assert "link_paths" in result
        assert result["confidence_score"] == 0.9

    def test_plan_file_path_low_confidence(self):
        """测试低置信度的路径规划"""
        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.5,  # 低于阈值
            "tags": ["工作"],
        }

        original_path = "/test/document.pdf"
        file_metadata = {}

        result = self.path_planner.plan_file_path(
            classification_result, original_path, file_metadata
        )

        assert result["status"] == "needs_review"
        assert result["category"] == "needs_review"
        assert "review_reason" in result

    def test_plan_file_path_error(self):
        """测试路径规划错误处理"""
        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.9,
            "tags": ["工作"],
        }

        original_path = "/test/document.pdf"
        file_metadata = {}

        # 模拟错误
        with patch.object(
            self.path_planner,
            "_determine_primary_path",
            side_effect=Exception("测试错误"),
        ):
            result = self.path_planner.plan_file_path(
                classification_result, original_path, file_metadata
            )

        assert result["status"] == "error"
        assert "error_message" in result

    def test_determine_primary_path(self):
        """测试主路径确定"""
        category = "工作"
        original_path = "/test/document.pdf"
        metadata = {"year": "2024", "month": "01"}

        result = self.path_planner._determine_primary_path(
            category, original_path, metadata
        )

        assert "test_output" in result
        assert "工作" in result
        assert "document.pdf" in result

    def test_get_category_base_path(self):
        """测试类别基础路径获取"""
        # 测试默认类别
        assert self.path_planner._get_category_base_path("工作") == "工作"
        assert self.path_planner._get_category_base_path("个人") == "个人"

        # 测试特殊路径
        assert self.path_planner._get_category_base_path("uncategorized") == "待整理"
        assert self.path_planner._get_category_base_path("needs_review") == "待审核"

        # 测试未知类别
        assert self.path_planner._get_category_base_path("未知类别") == "其他"

    def test_get_template_variables(self):
        """测试模板变量获取"""
        category = "工作"
        metadata = {"author": "张三", "project": "项目A"}

        variables = self.path_planner._get_template_variables(category, metadata)

        assert variables["category"] == "工作"
        assert variables["author"] == "张三"
        assert variables["project"] == "项目A"
        assert "year" in variables
        assert "month" in variables
        assert "date" in variables

    def test_apply_path_template(self):
        """测试路径模板应用"""
        template = "{category}/{year}/{month}"
        variables = {"category": "工作", "year": "2024", "month": "01"}

        result = self.path_planner._apply_path_template(template, variables)

        assert result == "工作/2024/01"

    def test_plan_link_paths(self):
        """测试链接路径规划"""
        tags = ["工作", "项目A", "重要"]
        primary_category = "工作"
        primary_path = "test_output/工作/2024/01/document.pdf"

        link_paths = self.path_planner._plan_link_paths(
            tags, primary_category, primary_path
        )

        assert len(link_paths) == 2  # 项目A 和 重要
        for link_info in link_paths:
            assert "source_path" in link_info
            assert "link_path" in link_info
            assert "tag" in link_info
            assert "type" in link_info

    def test_check_path_conflicts(self):
        """测试路径冲突检查"""
        target_path = "test_output/工作/document.pdf"
        original_path = "/test/document.pdf"

        conflict_info = self.path_planner._check_path_conflicts(
            target_path, original_path
        )

        assert "has_conflict" in conflict_info
        assert "conflict_type" in conflict_info
        assert "resolution" in conflict_info
        assert "suggested_path" in conflict_info

    def test_resolve_conflict_with_suffix(self):
        """测试后缀冲突解决"""
        path = "test_output/工作/document.pdf"

        # 创建必要的目录
        os.makedirs("test_output/工作", exist_ok=True)

        # 创建临时文件模拟冲突
        conflict_file = Path("test_output/工作/document.pdf")
        conflict_file.write_text("test")

        try:
            result = self.path_planner._resolve_conflict_with_suffix(path)
            assert result != path
            assert "_1" in result or "_2" in result
        finally:
            conflict_file.unlink()

    def test_resolve_conflict_with_timestamp(self):
        """测试时间戳冲突解决"""
        path = "test_output/工作/document.pdf"

        result = self.path_planner._resolve_conflict_with_timestamp(path)

        assert result != path
        assert "_" in result
        assert result.endswith(".pdf")

    def test_resolve_long_path(self):
        """测试长路径解决"""
        # 创建一个超长路径
        long_filename = "a" * 300 + ".pdf"
        long_path = f"test_output/工作/{long_filename}"

        result = self.path_planner._resolve_long_path(long_path)

        assert len(result) <= self.path_planner.max_path_length

    def test_ensure_path_length(self):
        """测试路径长度确保"""
        path = Path("test_output/工作")
        filename = "document.pdf"

        result = self.path_planner._ensure_path_length(path, filename)

        assert isinstance(result, Path)
        full_path = result / filename
        assert len(str(full_path)) <= self.path_planner.max_path_length

    def test_create_directory_structure(self):
        """测试目录结构创建"""
        path_plan = {
            "primary_path": "test_output/工作/2024/01/document.pdf",
            "link_paths": [{"link_path": "test_output/项目A/链接/document.pdf"}],
        }

        result = self.path_planner.create_directory_structure(path_plan)

        assert result is True
        assert Path("test_output/工作/2024/01").exists()
        assert Path("test_output/项目A/链接").exists()

    def test_validate_path_plan(self):
        """测试路径规划验证"""
        # 有效的路径规划
        valid_plan = {
            "original_path": "/test/document.pdf",
            "primary_path": "test_output/工作/document.pdf",
            "status": "planned",
        }

        result = self.path_planner.validate_path_plan(valid_plan)
        assert result["is_valid"] is True

        # 无效的路径规划
        invalid_plan = {
            "original_path": "/test/document.pdf"
            # 缺少必要字段
        }

        result = self.path_planner.validate_path_plan(invalid_plan)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_get_path_statistics(self):
        """测试路径统计信息获取"""
        stats = self.path_planner.get_path_statistics()

        assert "base_path" in stats
        assert "default_categories" in stats
        assert "multi_label_strategy" in stats
        assert "path_template" in stats
        assert "max_path_length" in stats
        assert "special_paths" in stats
        assert "category_mapping_count" in stats

    def teardown_method(self):
        """测试后清理"""
        # 清理测试目录
        if Path("test_output").exists():
            shutil.rmtree("test_output")

        # 清理测试文件
        if Path("test_category_mapping.yaml").exists():
            Path("test_category_mapping.yaml").unlink()
