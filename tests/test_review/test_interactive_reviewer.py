"""
InteractiveReviewer单元测试

测试交互式审核界面的功能
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

from ods.review.interactive_reviewer import InteractiveReviewer


class TestInteractiveReviewer(unittest.TestCase):
    """InteractiveReviewer测试类"""

    def setUp(self):
        """测试前准备"""
        self.config = {
            "classification": {
                "taxonomies": {
                    "主类别": {"工作": [], "个人": [], "财务": []},
                    "文档类型": {"报告": [], "合同": [], "发票": []},
                    "敏感级别": {"公开": [], "内部": [], "机密": []},
                },
                "confidence_threshold": {
                    "auto": 0.85,
                    "review": 0.6,
                },
                "tag_rules": {
                    "max_tags_per_file": 5,
                    "primary_tag_required": True,
                },
            },
        }

        # 创建模拟的review_manager
        self.mock_review_manager = Mock()
        self.mock_reclassification_workflow = Mock()

        with patch(
            "ods.review.interactive_reviewer.ReviewManager",
            return_value=self.mock_review_manager,
        ), patch(
            "ods.review.interactive_reviewer.ReclassificationWorkflow",
            return_value=self.mock_reclassification_workflow,
        ):
            self.reviewer = InteractiveReviewer(self.config)

    def test_init(self):
        """测试InteractiveReviewer初始化"""
        self.assertIsNotNone(self.reviewer)
        self.assertEqual(self.reviewer.config, self.config)
        self.assertIsNotNone(self.reviewer.review_manager)
        self.assertIsNotNone(self.reviewer.reclassification_workflow)

    def test_start_review_session(self):
        """测试开始审核会话"""
        self.mock_review_manager.create_review_session.return_value = "review_12345678"

        session_id = self.reviewer.start_review_session("test_user")

        self.assertEqual(session_id, "review_12345678")
        self.mock_review_manager.create_review_session.assert_called_once_with(
            "test_user"
        )

    def test_get_pending_reviews_count(self):
        """测试获取待审核文件数量"""
        self.mock_review_manager.get_review_statistics.return_value = {
            "pending_reviews": 5
        }

        count = self.reviewer.get_pending_reviews_count()

        self.assertEqual(count, 5)
        self.mock_review_manager.get_review_statistics.assert_called_once()

    def test_display_file_info(self):
        """测试文件信息显示"""
        file_info = {
            "file_path": "/test/document.pdf",
            "file_size": 2048000,  # 2MB
            "category": "工作",
            "tags": ["报告"],
            "last_classified": "2024-01-01T10:00:00",
            "review_priority": 2.5,
        }

        # 捕获输出
        with patch("builtins.print") as mock_print:
            self.reviewer._display_file_info(file_info)

        # 验证输出调用
        self.assertTrue(mock_print.called)
        calls = [call[0][0] for call in mock_print.call_args_list]

        # 检查关键信息是否显示
        self.assertTrue(any("document.pdf" in call for call in calls))
        self.assertTrue(any("2.00 MB" in call for call in calls))
        self.assertTrue(any("工作" in call for call in calls))
        self.assertTrue(any("报告" in call for call in calls))

    def test_display_batch_file_list(self):
        """测试批量文件列表显示"""
        files = [
            {
                "file_path": "/test/file1.pdf",
                "category": "工作",
                "review_priority": 3.0,
            },
            {
                "file_path": "/test/file2.docx",
                "category": "个人",
                "review_priority": 1.5,
            },
        ]

        with patch("builtins.print") as mock_print:
            self.reviewer._display_batch_file_list(files)

        self.assertTrue(mock_print.called)

    def test_get_user_decision_approve(self):
        """测试获取用户决策（批准）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        with patch("builtins.input", return_value="1"):  # 选择批准
            decision = self.reviewer._get_user_decision(file_info)

        expected = {
            "action": "approved",
            "category": "工作",
            "tags": ["报告"],
        }
        self.assertEqual(decision, expected)

    def test_get_user_decision_correct(self):
        """测试获取用户决策（修改）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        # 模拟用户输入：2（修改）-> 1（选择财务）-> 0（跳过标签选择）
        inputs = ["2", "1", "0"]

        with patch("builtins.input", side_effect=inputs):
            decision = self.reviewer._get_user_decision(file_info)

        expected = {
            "action": "corrected",
            "category": "财务",  # 用户选择的类别
            "tags": [],  # 没有选择标签
        }
        self.assertEqual(decision, expected)

    def test_get_user_decision_reject(self):
        """测试获取用户决策（拒绝）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        with patch(
            "builtins.input", side_effect=["3", "文件质量不佳"]
        ):  # 选择拒绝并输入原因
            decision = self.reviewer._get_user_decision(file_info)

        expected = {
            "action": "rejected",
            "reason": "文件质量不佳",
            "category": "工作",
            "tags": ["报告"],
        }
        self.assertEqual(decision, expected)

    def test_get_user_decision_skip(self):
        """测试获取用户决策（跳过）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        with patch("builtins.input", return_value="4"):  # 选择跳过
            decision = self.reviewer._get_user_decision(file_info)

        expected = {"action": "skip"}
        self.assertEqual(decision, expected)

    def test_get_user_decision_quit(self):
        """测试获取用户决策（退出）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        with patch("builtins.input", return_value="5"):  # 选择退出
            decision = self.reviewer._get_user_decision(file_info)

        expected = {"action": "quit"}
        self.assertEqual(decision, expected)

    def test_get_user_decision_invalid_input(self):
        """测试获取用户决策（无效输入）"""
        file_info = {
            "category": "工作",
            "tags": ["报告"],
        }

        with patch(
            "builtins.input", side_effect=["invalid", "1"]
        ):  # 先无效输入，再有效输入
            with patch("builtins.print") as mock_print:
                decision = self.reviewer._get_user_decision(file_info)

        # 验证打印了错误信息
        self.assertTrue(mock_print.called)

        # 最终应该返回有效决策
        expected = {
            "action": "approved",
            "category": "工作",
            "tags": ["报告"],
        }
        self.assertEqual(decision, expected)

    def test_select_batch_template(self):
        """测试选择批量分类模板"""
        # 模拟用户输入：选择财务类别，然后跳过标签选择
        inputs = ["2", "0"]  # 2=财务, 0=跳过标签

        with patch("builtins.input", side_effect=inputs):
            template = self.reviewer._select_batch_template()

        expected = {
            "category": "个人",  # 索引1对应"个人"
            "tags": [],
        }
        self.assertEqual(template, expected)

    def test_select_batch_template_with_tags(self):
        """测试选择批量分类模板（包含标签）"""
        # 模拟用户输入：选择工作类别，选择报告标签
        inputs = ["0", "1", "0"]  # 0=工作, 1=报告, 0=结束标签选择

        with patch("builtins.input", side_effect=inputs):
            template = self.reviewer._select_batch_template()

        expected = {
            "category": "工作",  # 索引0对应"工作"
            "tags": ["报告"],  # 选择了报告标签
        }
        self.assertEqual(template, expected)

    def test_apply_template_to_file(self):
        """测试将模板应用到文件"""
        file_info = {
            "file_path": "/test/document.pdf",
            "file_extension": ".pdf",
        }

        template = {
            "category": "工作",
            "tags": ["报告"],
        }

        decision = self.reviewer._apply_template_to_file(file_info, template)

        expected = {
            "action": "corrected",
            "category": "工作",
            "tags": ["报告"],  # 由于是PDF文件，自动添加了报告标签
        }
        self.assertEqual(decision, expected)

    def test_apply_template_to_file_docx(self):
        """测试将模板应用到DOCX文件"""
        file_info = {
            "file_path": "/test/document.docx",
            "file_extension": ".docx",
        }

        template = {
            "category": "工作",
            "tags": ["合同"],
        }

        decision = self.reviewer._apply_template_to_file(file_info, template)

        expected = {
            "action": "corrected",
            "category": "工作",
            "tags": ["合同", "报告"],  # DOCX文件也自动添加了报告标签
        }
        self.assertEqual(decision, expected)

    def test_record_user_decision_approved(self):
        """测试记录用户决策（批准）"""
        file_info = {"id": 1}
        decision = {
            "action": "approved",
            "category": "工作",
            "tags": ["报告"],
        }

        # 模拟数据库操作成功
        self.mock_review_manager.record_review_decision.return_value = True

        with patch("builtins.print") as mock_print:
            self.reviewer._record_user_decision("session_123", file_info, decision)

        # 验证审核操作被记录
        self.mock_review_manager.record_review_decision.assert_called_once()

        # 验证输出信息
        self.assertTrue(mock_print.called)

    def test_record_user_decision_corrected(self):
        """测试记录用户决策（修改）"""
        file_info = {"id": 1, "file_path": "/test/file.pdf"}
        decision = {
            "action": "corrected",
            "category": "财务",
            "tags": ["发票"],
        }

        # 模拟操作成功
        self.mock_review_manager.record_review_decision.return_value = True
        self.mock_reclassification_workflow.reclassify_file.return_value = {
            "success": True,
            "path_changed": True,
            "old_path": "/old/path/file.pdf",
            "new_path": "/new/path/file.pdf",
        }

        with patch("builtins.print") as mock_print:
            self.reviewer._record_user_decision("session_123", file_info, decision)

        # 验证重新分类工作流被调用
        self.mock_reclassification_workflow.reclassify_file.assert_called_once()

        # 验证输出信息包含重新分类结果
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("重新分类完成" in call for call in print_calls))

    def test_record_user_decision_corrected_failed(self):
        """测试记录用户决策（修改失败）"""
        file_info = {"id": 1, "file_path": "/test/file.pdf"}
        decision = {
            "action": "corrected",
            "category": "财务",
            "tags": ["发票"],
        }

        # 模拟重新分类失败
        self.mock_review_manager.record_review_decision.return_value = True
        self.mock_reclassification_workflow.reclassify_file.return_value = {
            "success": False,
            "error": "重新分类失败",
        }

        with patch("builtins.print") as mock_print:
            self.reviewer._record_user_decision("session_123", file_info, decision)

        # 验证输出错误信息
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("重新分类失败" in call for call in print_calls))

    def test_record_user_decision_database_error(self):
        """测试记录用户决策（数据库错误）"""
        file_info = {"id": 1}
        decision = {
            "action": "approved",
            "category": "工作",
            "tags": ["报告"],
        }

        # 模拟数据库操作失败
        self.mock_review_manager.record_review_decision.return_value = False

        with patch("builtins.print") as mock_print:
            self.reviewer._record_user_decision("session_123", file_info, decision)

        # 验证输出错误信息
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("保存审核记录失败" in call for call in print_calls))


if __name__ == "__main__":
    unittest.main()
