import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from ods.naming.renamer import Renamer


class TestRenamer:
    """命名生成器测试"""

    def setup_method(self):
        """测试前准备"""
        self.config = {
            "naming": {
                "default_template": "{{category}}-{{title}}-{{date}}.{{ext}}",
                "max_filename_length": 200,
                "enable_llm_title": True,
                "title_max_length": 50,
                "conflict_resolution": "suffix",
                "invalid_chars": '[<>:"/\\\\|?*]',
                "replacement_char": "_",
                "templates_file": "test_naming_templates.yaml",
            }
        }

        self.renamer = Renamer(self.config)

    def test_init(self):
        """测试初始化"""
        assert (
            self.renamer.default_template == "{{category}}-{{title}}-{{date}}.{{ext}}"
        )
        assert self.renamer.max_filename_length == 200
        assert self.renamer.enable_llm_title == True
        assert self.renamer.title_max_length == 50

    def test_generate_filename_success(self):
        """测试成功的文件名生成"""
        path_plan = {
            "original_path": "/test/document.pdf",
            "primary_path": "test_output/工作/document.pdf",
            "category": "工作",
        }

        document_data = {
            "file_path": "/test/document.pdf",
            "text_content": "这是一个工作文档的内容",
            "summary": "工作文档摘要",
            "metadata": {"author": "张三"},
        }

        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.9,
            "tags": ["工作"],
        }

        result = self.renamer.generate_filename(
            path_plan, document_data, classification_result
        )

        assert result["status"] == "generated"
        assert result["original_path"] == "/test/document.pdf"
        assert "new_filename" in result
        assert "template_used" in result
        assert "document_info" in result

    def test_generate_filename_error(self):
        """测试文件名生成错误处理"""
        path_plan = {
            "original_path": "/test/document.pdf",
            "primary_path": "test_output/工作/document.pdf",
            "category": "工作",
        }

        document_data = {}
        classification_result = {}

        # 模拟错误
        with patch.object(
            self.renamer, "_extract_document_info", side_effect=Exception("测试错误")
        ):
            result = self.renamer.generate_filename(
                path_plan, document_data, classification_result
            )

        assert result["status"] == "error"
        assert "error_message" in result

    def test_extract_document_info(self):
        """测试文档信息提取"""
        document_data = {
            "file_path": "/test/document.pdf",
            "text_content": "这是一个工作文档的内容",
            "summary": "工作文档摘要",
            "metadata": {"author": "张三", "project": "项目A"},
        }

        classification_result = {
            "primary_category": "工作",
            "confidence_score": 0.9,
            "tags": ["工作", "项目A"],
        }

        info = self.renamer._extract_document_info(document_data, classification_result)

        assert info["category"] == "工作"
        assert info["tags"] == ["工作", "项目A"]
        assert info["confidence_score"] == 0.9
        assert info["ext"] == "pdf"
        assert info["original_name"] == "document"
        assert info["content_length"] == len("这是一个工作文档的内容")
        assert info["author"] == "张三"
        assert info["project"] == "项目A"
        assert "date" in info
        assert "year" in info
        assert "month" in info

    def test_extract_title_from_content(self):
        """测试从内容中提取标题"""
        # 测试有标题的内容
        content = "项目计划书\n\n这是一个重要的项目计划文档..."
        title = self.renamer._extract_title_from_content(content)
        assert title == "项目计划书"

        # 测试无标题的内容
        content = "这是一个没有明确标题的文档内容..."
        title = self.renamer._extract_title_from_content(content)
        assert title == ""

        # 测试空内容
        title = self.renamer._extract_title_from_content("")
        assert title == ""

    def test_generate_title_with_llm(self):
        """测试LLM标题生成"""
        document_data = {
            "text_content": "这是一个关于项目管理的文档，包含了详细的项目计划和执行方案。"
        }

        title = self.renamer._generate_title_with_llm(document_data)

        assert isinstance(title, str)
        assert len(title) > 0
        assert len(title) <= self.renamer.title_max_length

    def test_select_naming_template(self):
        """测试命名模板选择"""
        category = "工作"
        document_info = {"ext": "pdf"}

        # 测试类别模板
        template = self.renamer._select_naming_template(category, document_info)
        assert template == self.renamer.default_template

        # 测试文件类型模板
        self.renamer.templates["pdf"] = "{{category}}-{{title}}.pdf"
        template = self.renamer._select_naming_template("其他", document_info)
        assert template == "{{category}}-{{title}}.pdf"

    def test_apply_naming_template(self):
        """测试命名模板应用"""
        template = "{{category}}-{{title}}-{{date}}.{{ext}}"
        document_info = {
            "category": "工作",
            "title": "项目计划书",
            "date": "20240101",
            "ext": "pdf",
        }

        result = self.renamer._apply_naming_template(template, document_info)

        assert result == "工作-项目计划书-20240101.pdf"

    def test_simple_template_replace(self):
        """测试简单模板替换"""
        template = "{{category}}-{{title}}-{{date}}.{{ext}}"
        document_info = {
            "category": "工作",
            "title": "项目计划书",
            "date": "20240101",
            "ext": "pdf",
        }

        result = self.renamer._simple_template_replace(template, document_info)

        assert result == "工作-项目计划书-20240101.pdf"

    def test_clean_filename(self):
        """测试文件名清理"""
        # 测试正常文件名
        filename = "正常文件名.pdf"
        result = self.renamer._clean_filename(filename)
        assert result == "正常文件名.pdf"

        # 测试包含无效字符的文件名
        filename = "文件<名>:*.pdf"
        result = self.renamer._clean_filename(filename)
        assert "<" not in result
        assert ":" not in result
        assert "*" not in result

        # 测试空文件名
        result = self.renamer._clean_filename("")
        assert result == "未命名文件"

        # 测试只有空格的文件名
        result = self.renamer._clean_filename("   ")
        assert result == "未命名文件"

    def test_truncate_filename(self):
        """测试文件名截断"""
        # 测试正常长度文件名
        filename = "正常文件名.pdf"
        result = self.renamer._truncate_filename(filename)
        assert result == filename

        # 测试超长文件名
        long_filename = "a" * 300 + ".pdf"
        result = self.renamer._truncate_filename(long_filename)
        assert len(result) <= self.renamer.max_filename_length
        assert result.endswith(".pdf")

    def test_build_new_path(self):
        """测试新路径构建"""
        primary_path = "test_output/工作/document.pdf"
        new_filename = "工作-项目计划书-20240101.pdf"

        result = self.renamer._build_new_path(primary_path, new_filename)

        assert result == "test_output/工作/工作-项目计划书-20240101.pdf"

    def test_check_filename_conflicts(self):
        """测试文件名冲突检查"""
        new_path = "test_output/工作/document.pdf"
        original_path = "/test/document.pdf"

        conflict_info = self.renamer._check_filename_conflicts(new_path, original_path)

        assert "has_conflict" in conflict_info
        assert "conflict_type" in conflict_info
        assert "resolution" in conflict_info
        assert "final_path" in conflict_info

    def test_resolve_filename_conflict_with_suffix(self):
        """测试后缀文件名冲突解决"""
        path = "test_output/工作/document.pdf"

        # 创建必要的目录
        os.makedirs("test_output/工作", exist_ok=True)

        # 创建临时文件模拟冲突
        conflict_file = Path("test_output/工作/document.pdf")
        conflict_file.write_text("test")

        try:
            result = self.renamer._resolve_filename_conflict_with_suffix(path)
            assert result != path
            assert "_1" in result or "_2" in result
        finally:
            conflict_file.unlink()

    def test_resolve_filename_conflict_with_timestamp(self):
        """测试时间戳文件名冲突解决"""
        path = "test_output/工作/document.pdf"

        result = self.renamer._resolve_filename_conflict_with_timestamp(path)

        assert result != path
        assert "_" in result
        assert result.endswith(".pdf")

    def test_create_error_naming(self):
        """测试错误命名结果创建"""
        path_plan = {"original_path": "/test/document.pdf"}
        error_message = "测试错误"

        result = self.renamer._create_error_naming(path_plan, error_message)

        assert result["status"] == "error"
        assert result["error_message"] == error_message
        assert result["original_path"] == "/test/document.pdf"
        assert result["new_path"] == "/test/document.pdf"

    def test_add_naming_template(self):
        """测试添加命名模板"""
        category = "测试类别"
        template = "{{category}}-{{title}}-{{date}}.{{ext}}"

        result = self.renamer.add_naming_template(category, template)

        assert result == True
        assert category in self.renamer.templates
        assert self.renamer.templates[category] == template

    def test_remove_naming_template(self):
        """测试移除命名模板"""
        category = "测试类别"
        template = "{{category}}-{{title}}-{{date}}.{{ext}}"

        # 先添加模板
        self.renamer.templates[category] = template

        # 然后移除
        result = self.renamer.remove_naming_template(category)

        assert result == True
        assert category not in self.renamer.templates

    def test_get_naming_templates(self):
        """测试获取命名模板"""
        templates = self.renamer.get_naming_templates()

        assert isinstance(templates, dict)
        assert templates is not self.renamer.templates  # 应该是副本

    def test_validate_naming_result(self):
        """测试命名结果验证"""
        # 有效的命名结果
        valid_result = {
            "original_path": "/test/document.pdf",
            "new_path": "test_output/工作/document.pdf",
            "new_filename": "工作-项目计划书-20240101.pdf",
            "status": "generated",
        }

        result = self.renamer.validate_naming_result(valid_result)
        assert result["is_valid"] == True

        # 无效的命名结果
        invalid_result = {
            "original_path": "/test/document.pdf"
            # 缺少必要字段
        }

        result = self.renamer.validate_naming_result(invalid_result)
        assert result["is_valid"] == False
        assert len(result["errors"]) > 0

    def test_get_naming_statistics(self):
        """测试命名统计信息获取"""
        stats = self.renamer.get_naming_statistics()

        assert "default_template" in stats
        assert "max_filename_length" in stats
        assert "enable_llm_title" in stats
        assert "title_max_length" in stats
        assert "conflict_resolution" in stats
        assert "templates_count" in stats
        assert "invalid_chars_pattern" in stats
        assert "replacement_char" in stats

    def test_jinja2_filters(self):
        """测试Jinja2过滤器"""
        # 测试strftime过滤器
        from datetime import datetime

        dt = datetime(2024, 1, 1)
        result = self.renamer._strftime_filter(dt, "%Y%m%d")
        assert result == "20240101"

        # 测试truncate过滤器
        long_text = "这是一个很长的文本内容，需要被截断"
        result = self.renamer._truncate_filter(long_text, 10)
        assert len(result) <= 10
        assert result.endswith("...")

        # 测试clean_filename过滤器
        dirty_filename = "文件<名>:*.pdf"
        result = self.renamer._clean_filename_filter(dirty_filename)
        assert "<" not in result
        assert ":" not in result
        assert "*" not in result

    def teardown_method(self):
        """测试后清理"""
        # 清理测试目录
        if Path("test_output").exists():
            shutil.rmtree("test_output")

        # 清理测试文件
        if Path("test_naming_templates.yaml").exists():
            Path("test_naming_templates.yaml").unlink()
