"""
CLI Review命令单元测试

测试review和review-stats命令的功能
"""

import unittest
import sys
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner


class TestCLIReview(unittest.TestCase):
    """CLI Review测试类"""

    def setUp(self):
        """测试前准备"""
        self.runner = CliRunner()

        # 创建模拟配置对象
        self.mock_config_obj = Mock()
        self.mock_config_obj.get_config_dict.return_value = {
            "classification": {
                "taxonomies": {
                    "主类别": ["工作", "个人", "财务"],
                },
                "confidence_threshold": {
                    "auto": 0.85,
                    "review": 0.6,
                },
            },
        }

        self.config_patcher = patch("ods.cli.Config", return_value=self.mock_config_obj)

    @patch("ods.cli.review.interactive_reviewer.InteractiveReviewer")
    def test_review_command_basic(self, mock_reviewer_class):
        """测试review命令基本功能"""
        with self.config_patcher:
            # 设置mock
            mock_reviewer = Mock()
            mock_reviewer_class.return_value = mock_reviewer

            # 模拟有待审核文件
            mock_reviewer.get_pending_reviews_count.return_value = 3
            mock_reviewer.start_review_session.return_value = "review_12345678"

            # 导入review命令
            from ods.cli import review

            # 执行命令
            result = self.runner.invoke(review, [])

            # 验证执行成功
            self.assertEqual(result.exit_code, 0)

            # 验证输出包含预期内容
            self.assertIn("发现 3 个待审核文件", result.output)
            self.assertIn("开始审核会话", result.output)

            # 验证方法调用
            mock_reviewer_class.assert_called_once()
            mock_reviewer.get_pending_reviews_count.assert_called_once()
            mock_reviewer.start_review_session.assert_called_once()
            mock_reviewer.run_interactive_review.assert_called_once()

    @patch("ods.cli.review.interactive_reviewer.InteractiveReviewer")
    def test_review_command_no_pending_reviews(self, mock_reviewer_class):
        """测试review命令（无待审核文件）"""
        with self.config_patcher:
            mock_reviewer = Mock()
            mock_reviewer_class.return_value = mock_reviewer

            # 模拟无待审核文件
            mock_reviewer.get_pending_reviews_count.return_value = 0

            # 导入review命令
            from ods.cli import review

            # 执行命令
            result = self.runner.invoke(review, [])

            # 验证执行成功
            self.assertEqual(result.exit_code, 0)

            # 验证输出
            self.assertIn("没有找到需要审核的文件", result.output)
            self.assertIn("运行 'ods apply' 进行文件分类", result.output)

            # 验证未启动审核会话
            mock_reviewer.start_review_session.assert_not_called()
            mock_reviewer.run_interactive_review.assert_not_called()

    def test_review_command_with_options(self):
        """测试review命令带选项"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.interactive_reviewer.InteractiveReviewer"
            ) as mock_reviewer_class:
                mock_reviewer = Mock()
                mock_reviewer_class.return_value = mock_reviewer

                mock_reviewer.get_pending_reviews_count.return_value = 5
                mock_reviewer.start_review_session.return_value = "review_abcdef12"

                # 执行命令带选项
                result = self.runner.invoke(
                    review, ["--max-files", "20", "--user-id", "john_doe"]
                )

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证参数传递
                mock_reviewer.start_review_session.assert_called_once_with("john_doe")
                mock_reviewer.run_interactive_review.assert_called_once_with(
                    "review_abcdef12", 20, batch_mode=False
                )

    def test_review_command_batch_mode(self):
        """测试review命令批量模式"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.interactive_reviewer.InteractiveReviewer"
            ) as mock_reviewer_class:
                mock_reviewer = Mock()
                mock_reviewer_class.return_value = mock_reviewer

                mock_reviewer.get_pending_reviews_count.return_value = 10
                mock_reviewer.start_review_session.return_value = "review_batch123"

                # 执行批量模式命令
                result = self.runner.invoke(review, ["--batch", "--max-files", "15"])

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证输出包含批量模式提示
                self.assertIn("启用批量审核模式", result.output)

                # 验证调用参数
                mock_reviewer.run_interactive_review.assert_called_once_with(
                    "review_batch123", 15, batch_mode=True
                )

    def test_review_command_import_error(self):
        """测试review命令导入错误"""
        with self.config_patcher:
            # 模拟导入错误
            with patch(
                "ods.cli.InteractiveReviewer",
                side_effect=ImportError("Module not found"),
            ):
                result = self.runner.invoke(review, [])

                # 验证退出码为0（处理了异常）
                self.assertEqual(result.exit_code, 0)

                # 验证错误信息
                self.assertIn("无法加载审核模块", result.output)
                self.assertIn("Module not found", result.output)

    def test_review_command_runtime_error(self):
        """测试review命令运行时错误"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.interactive_reviewer.InteractiveReviewer"
            ) as mock_reviewer_class:
                mock_reviewer = Mock()
                mock_reviewer_class.return_value = mock_reviewer

                # 模拟运行时错误
                mock_reviewer.get_pending_reviews_count.side_effect = Exception(
                    "Runtime error"
                )

                result = self.runner.invoke(review, [])

                # 验证退出码为0（处理了异常）
                self.assertEqual(result.exit_code, 0)

                # 验证错误信息
                self.assertIn("审核过程出错", result.output)
                self.assertIn("Runtime error", result.output)

    def test_review_stats_command_basic(self):
        """测试review-stats命令基本功能"""
        with self.config_patcher:
            # 模拟ReviewManager
            with patch(
                "ods.cli.review.review_manager.ReviewManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                # 模拟统计数据
                mock_stats = {
                    "session": {
                        "session_id": "review_12345678",
                        "user_id": "test_user",
                        "total_files": 10,
                        "reviewed_files": 8,
                    },
                    "records": {
                        "total_reviews": 8,
                        "approved": 5,
                        "corrected": 2,
                        "rejected": 1,
                    },
                    "completion_rate": 80.0,
                }
                mock_manager.get_review_statistics.return_value = mock_stats

                # 执行命令
                result = self.runner.invoke(
                    review_stats, ["--session-id", "review_12345678"]
                )

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证输出包含统计信息
                self.assertIn("审核统计信息", result.output)
                self.assertIn("review_12345678", result.output)
                self.assertIn("test_user", result.output)
                self.assertIn("80.0%", result.output)
                self.assertIn("批准: 5", result.output)
                self.assertIn("修改: 2", result.output)
                self.assertIn("拒绝: 1", result.output)

    def test_review_stats_command_global_stats(self):
        """测试review-stats命令全局统计"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.review_manager.ReviewManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                # 模拟全局统计数据
                mock_stats = {
                    "pending_reviews": 15,
                    "total_sessions": 3,
                    "review_actions": {
                        "total": 45,
                        "approved": 30,
                        "corrected": 10,
                        "rejected": 5,
                    },
                }
                mock_manager.get_review_statistics.return_value = mock_stats

                # 执行命令（无session-id参数）
                result = self.runner.invoke(review_stats, [])

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证输出包含全局统计
                self.assertIn("待审核文件: 15", result.output)
                self.assertIn("审核会话总数: 3", result.output)
                self.assertIn("审核记录总数: 45", result.output)

    def test_review_stats_command_detailed(self):
        """测试review-stats命令详细模式"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.review_manager.ReviewManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                # 模拟包含处理时间的统计数据
                mock_stats = {
                    "session": {
                        "session_id": "review_12345678",
                        "user_id": "test_user",
                        "total_files": 10,
                        "reviewed_files": 8,
                    },
                    "records": {
                        "total_reviews": 8,
                        "approved": 5,
                        "corrected": 2,
                        "rejected": 1,
                        "avg_processing_time": 2.5,
                    },
                    "completion_rate": 80.0,
                }
                mock_manager.get_review_statistics.return_value = mock_stats

                # 执行详细模式命令
                result = self.runner.invoke(
                    review_stats, ["--session-id", "review_12345678", "--detailed"]
                )

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证输出包含详细处理时间
                self.assertIn("平均处理时间: 2.50 秒", result.output)

    def test_review_stats_command_no_stats(self):
        """测试review-stats命令（无统计数据）"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.review_manager.ReviewManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                # 模拟无统计数据
                mock_manager.get_review_statistics.return_value = {}

                # 执行命令
                result = self.runner.invoke(
                    review_stats, ["--session-id", "nonexistent"]
                )

                # 验证执行成功
                self.assertEqual(result.exit_code, 0)

                # 验证错误信息
                self.assertIn("未找到审核统计信息", result.output)

    def test_review_stats_command_import_error(self):
        """测试review-stats命令导入错误"""
        with self.config_patcher:
            # 模拟导入错误
            with patch(
                "ods.cli.ReviewManager", side_effect=ImportError("Module not found")
            ):
                result = self.runner.invoke(review_stats, [])

                # 验证退出码为0（处理了异常）
                self.assertEqual(result.exit_code, 0)

                # 验证错误信息
                self.assertIn("无法加载审核模块", result.output)
                self.assertIn("Module not found", result.output)

    def test_review_stats_command_runtime_error(self):
        """测试review-stats命令运行时错误"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.review_manager.ReviewManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                # 模拟运行时错误
                mock_manager.get_review_statistics.side_effect = Exception(
                    "Database error"
                )

                result = self.runner.invoke(review_stats, [])

                # 验证退出码为0（处理了异常）
                self.assertEqual(result.exit_code, 0)

                # 验证错误信息
                self.assertIn("获取统计信息出错", result.output)
                self.assertIn("Database error", result.output)

    def test_review_command_help(self):
        """测试review命令帮助信息"""
        with self.config_patcher:
            result = self.runner.invoke(review, ["--help"])

            # 验证执行成功
            self.assertEqual(result.exit_code, 0)

            # 验证帮助信息
            self.assertIn("启动交互式文件审核界面", result.output)
            self.assertIn("--max-files", result.output)
            self.assertIn("--user-id", result.output)
            self.assertIn("--batch", result.output)

    def test_review_stats_command_help(self):
        """测试review-stats命令帮助信息"""
        with self.config_patcher:
            result = self.runner.invoke(review_stats, ["--help"])

            # 验证执行成功
            self.assertEqual(result.exit_code, 0)

            # 验证帮助信息
            self.assertIn("查看审核统计信息", result.output)
            self.assertIn("--session-id", result.output)
            self.assertIn("--detailed", result.output)

    def test_command_output_encoding(self):
        """测试命令输出编码处理"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.interactive_reviewer.InteractiveReviewer"
            ) as mock_reviewer_class:
                mock_reviewer = Mock()
                mock_reviewer_class.return_value = mock_reviewer

                # 模拟包含中文的输出
                mock_reviewer.get_pending_reviews_count.return_value = 2
                mock_reviewer.start_review_session.return_value = "review_test123"

                result = self.runner.invoke(review, [])

                # 验证命令执行成功（输出编码正确）
                self.assertEqual(result.exit_code, 0)

                # 验证中文输出正确显示
                self.assertIn("待审核文件", result.output)

    def test_command_config_passing(self):
        """测试配置正确传递给组件"""
        with self.config_patcher:
            with patch(
                "ods.cli.review.interactive_reviewer.InteractiveReviewer"
            ) as mock_reviewer_class:
                mock_reviewer = Mock()
                mock_reviewer_class.return_value = mock_reviewer

                mock_reviewer.get_pending_reviews_count.return_value = 1
                mock_reviewer.start_review_session.return_value = "review_config123"

                # 执行命令
                result = self.runner.invoke(review, [])

                # 验证配置对象被传递
                mock_reviewer_class.assert_called_once_with(
                    self.mock_config_obj.get_config_dict.return_value
                )


if __name__ == "__main__":
    unittest.main()
