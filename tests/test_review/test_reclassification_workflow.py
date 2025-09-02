"""
ReclassificationWorkflow单元测试

测试重新分类工作流的功能
"""

import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ods.review.reclassification_workflow import ReclassificationWorkflow


class TestReclassificationWorkflow(unittest.TestCase):
    """ReclassificationWorkflow测试类"""

    def setUp(self):
        """测试前准备"""
        self.config = {
            "database": {
                "path": ":memory:",
            },
            "classification": {
                "taxonomies": {
                    "主类别": ["工作", "个人", "财务"],
                    "文档类型": ["报告", "合同", "发票"],
                },
            },
        }

        # 创建模拟组件
        self.mock_database = Mock()
        self.mock_workflow = Mock()
        self.mock_path_planner = Mock()
        self.mock_file_mover = Mock()
        self.mock_index_updater = Mock()

        with patch(
            "ods.review.reclassification_workflow.Database",
            return_value=self.mock_database,
        ), patch(
            "ods.review.reclassification_workflow.EnhancedWorkflow",
            return_value=self.mock_workflow,
        ), patch(
            "ods.review.reclassification_workflow.PathPlanner",
            return_value=self.mock_path_planner,
        ), patch(
            "ods.review.reclassification_workflow.FileMover",
            return_value=self.mock_file_mover,
        ), patch(
            "ods.review.reclassification_workflow.IndexUpdater",
            return_value=self.mock_index_updater,
        ):
            self.workflow = ReclassificationWorkflow(self.config)

    def test_init(self):
        """测试ReclassificationWorkflow初始化"""
        self.assertIsNotNone(self.workflow)
        self.assertEqual(self.workflow.config, self.config)
        self.assertIsNotNone(self.workflow.database)
        self.assertIsNotNone(self.workflow.enhanced_workflow)
        self.assertIsNotNone(self.workflow.path_planner)
        self.assertIsNotNone(self.workflow.file_mover)
        self.assertIsNotNone(self.workflow.index_updater)

    def test_reclassify_file_success(self):
        """测试重新分类文件（成功）"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟数据库查询
        mock_file_info = {
            "id": 1,
            "category": "工作",
            "tags": ["报告"],
            "file_size": 1024,
        }
        self.mock_database.execute_query.side_effect = [
            [mock_file_info],  # 文件信息查询
            None,  # 分类更新
            None,  # 状态更新
        ]

        # 模拟路径规划
        mock_path_plan = {
            "original_path": file_path,
            "primary_path": "/new/path/document.pdf",
            "status": "planned",
        }
        self.mock_path_planner.plan_file_path.return_value = mock_path_plan

        # 模拟文件移动
        mock_move_result = {
            "moved": True,
            "old_path": file_path,
            "primary_target_path": "/new/path/document.pdf",
        }
        self.mock_file_mover.move_file.return_value = mock_move_result

        result = self.workflow.reclassify_file(
            file_path, new_category, new_tags, "test_user"
        )

        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["file_path"], file_path)
        self.assertEqual(result["old_category"], "工作")
        self.assertEqual(result["new_category"], new_category)
        self.assertEqual(result["old_tags"], ["报告"])
        self.assertEqual(result["new_tags"], new_tags)
        self.assertTrue(result["path_changed"])

        # 验证组件调用
        self.mock_database.execute_query.assert_called()
        self.mock_path_planner.plan_file_path.assert_called_once()
        self.mock_file_mover.move_file.assert_called_once()
        self.mock_index_updater.update_file_index.assert_called_once()

    def test_reclassify_file_no_change(self):
        """测试重新分类文件（路径无变化）"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟文件已在正确位置
        mock_file_info = {
            "id": 1,
            "category": "财务",  # 已经是目标分类
            "tags": ["发票"],  # 已经是目标标签
            "file_size": 1024,
        }
        self.mock_database.execute_query.side_effect = [
            [mock_file_info],
            None,
            None,  # 数据库更新
        ]

        # 模拟路径规划返回相同路径
        mock_path_plan = {
            "original_path": file_path,
            "primary_path": file_path,  # 路径相同
            "status": "planned",
        }
        self.mock_path_planner.plan_file_path.return_value = mock_path_plan

        # 模拟文件移动（未实际移动）
        mock_move_result = {
            "moved": False,
            "old_path": file_path,
            "primary_target_path": file_path,
            "message": "文件已在正确位置",
        }
        self.mock_file_mover.move_file.return_value = mock_move_result

        result = self.workflow.reclassify_file(file_path, new_category, new_tags)

        # 验证结果
        self.assertTrue(result["success"])
        self.assertFalse(result["path_changed"])
        self.assertEqual(result["old_path"], file_path)
        self.assertEqual(result["new_path"], file_path)

    def test_reclassify_file_not_found(self):
        """测试重新分类文件（文件不存在）"""
        file_path = os.path.join("test", "nonexistent.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟文件不存在
        self.mock_database.execute_query.return_value = []

        result = self.workflow.reclassify_file(file_path, new_category, new_tags)

        # 验证结果
        self.assertFalse(result["success"])
        self.assertIn("不存在", result["error"])

    def test_reclassify_file_database_error(self):
        """测试重新分类文件（数据库错误）"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟_get_file_info返回None（数据库错误）
        with patch.object(self.workflow, "_get_file_info", return_value=None):
            result = self.workflow.reclassify_file(file_path, new_category, new_tags)

        # 验证结果
        self.assertFalse(result["success"])
        self.assertIn("文件不存在或未找到", result["error"])

    def test_reclassify_file_path_planning_error(self):
        """测试重新分类文件（路径规划错误）"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟文件信息正常
        mock_file_info = {
            "id": 1,
            "category": "工作",
            "tags": ["报告"],
            "file_size": 1024,
        }
        self.mock_database.execute_query.side_effect = [
            [mock_file_info],
            None,
            None,  # 数据库更新成功
        ]

        # 模拟路径规划失败
        self.mock_path_planner.plan_file_path.return_value = None

        result = self.workflow.reclassify_file(file_path, new_category, new_tags)

        # 验证结果
        self.assertFalse(result["success"])
        self.assertIn("路径规划失败", result["error"])

    def test_reclassify_from_review_records(self):
        """测试根据审核记录批量重新分类"""
        session_id = "review_12345678"

        # 模拟审核记录
        mock_records = [
            {
                "file_id": 1,
                "user_category": "财务",
                "user_tags": ["发票"],
                "session_user_id": "test_user",
            },
            {
                "file_id": 2,
                "user_category": "工作",
                "user_tags": ["报告"],
                "session_user_id": "test_user",
            },
        ]

        self.workflow._get_corrected_review_records = Mock(return_value=mock_records)

        # 模拟文件路径查询
        self.workflow._get_file_path_by_id = Mock(
            side_effect=[
                "/test/file1.pdf",
                "/test/file2.pdf",
            ]
        )

        # 模拟重新分类成功
        self.workflow.reclassify_file = Mock(
            side_effect=[
                {"success": True, "file_path": "/test/file1.pdf"},
                {
                    "success": False,
                    "error": "重新分类失败",
                    "file_path": "/test/file2.pdf",
                },
            ]
        )

        result = self.workflow.reclassify_from_review_records(session_id)

        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["total_files"], 2)
        self.assertEqual(result["successful_reclassifications"], 1)
        self.assertEqual(result["failed_reclassifications"], 1)
        self.assertEqual(len(result["results"]), 2)

        # 验证调用
        self.assertEqual(self.workflow.reclassify_file.call_count, 2)

    def test_reclassify_from_review_records_no_records(self):
        """测试根据审核记录批量重新分类（无记录）"""
        session_id = "review_12345678"

        # 模拟无审核记录
        self.workflow._get_corrected_review_records = Mock(return_value=[])

        result = self.workflow.reclassify_from_review_records(session_id)

        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["processed_files"], 0)

    def test_get_corrected_review_records(self):
        """测试获取修改的审核记录"""
        session_id = "review_12345678"

        mock_records = [
            {
                "id": 1,
                "file_id": 1,
                "user_category": "财务",
                "user_tags": '["发票"]',
                "review_action": "corrected",
            }
        ]

        self.mock_database.execute_query.return_value = mock_records

        records = self.workflow._get_corrected_review_records(session_id)

        # 验证调用
        self.mock_database.execute_query.assert_called_once()

        # 验证结果
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["file_id"], 1)
        self.assertEqual(records[0]["user_category"], "财务")

    def test_get_file_path_by_id(self):
        """测试根据ID获取文件路径"""
        file_id = 1
        expected_path = "/test/document.pdf"

        self.mock_database.execute_query.return_value = [{"file_path": expected_path}]

        path = self.workflow._get_file_path_by_id(file_id)

        # 验证结果
        self.assertEqual(path, expected_path)

        # 验证调用
        self.mock_database.execute_query.assert_called_once()

    def test_get_file_path_by_id_not_found(self):
        """测试根据ID获取文件路径（未找到）"""
        file_id = 1

        self.mock_database.execute_query.return_value = []

        path = self.workflow._get_file_path_by_id(file_id)

        # 验证结果
        self.assertIsNone(path)

    def test_update_classification_in_database(self):
        """测试更新数据库中的分类结果"""
        file_id = 1
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟数据库操作成功
        self.mock_database.execute_query.return_value = None

        result = self.workflow._update_classification_in_database(
            file_id, new_category, new_tags
        )

        # 验证结果
        self.assertTrue(result)

        # 验证数据库调用次数（应调用2次：insert分类、update状态）
        self.assertEqual(self.mock_database.execute_query.call_count, 2)

    def test_update_classification_in_database_error(self):
        """测试更新数据库中的分类结果（错误）"""
        file_id = 1
        new_category = "财务"
        new_tags = ["发票"]

        # 模拟数据库错误
        self.mock_database.execute_query.side_effect = Exception("Database error")

        result = self.workflow._update_classification_in_database(
            file_id, new_category, new_tags
        )

        # 验证结果
        self.assertFalse(result)

    def test_replan_file_path(self):
        """测试重新规划文件路径"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        mock_file_info = {
            "file_size": 1024,
        }

        mock_path_plan = {
            "original_path": file_path,
            "primary_path": "/new/path/document.pdf",
            "status": "planned",
        }

        self.mock_path_planner.plan_file_path.return_value = mock_path_plan

        path_plan = self.workflow._replan_file_path(
            file_path, new_category, new_tags, mock_file_info
        )

        # 验证结果
        self.assertEqual(path_plan, mock_path_plan)

        # 验证调用
        self.mock_path_planner.plan_file_path.assert_called_once()

    def test_execute_file_move_success(self):
        """测试执行文件移动（成功）"""
        mock_path_plan = {
            "original_path": "/old/path/file.pdf",
            "primary_path": "/new/path/file.pdf",
        }

        mock_file_info = {"file_size": 1024}

        mock_move_result = {
            "moved": True,
            "old_path": os.path.join("old", "path", "file.pdf"),
            "primary_target_path": os.path.join("new", "path", "file.pdf"),
        }

        self.mock_file_mover.move_file.return_value = mock_move_result

        result = self.workflow._execute_file_move(mock_path_plan, mock_file_info)

        # 验证结果
        self.assertEqual(result, mock_move_result)
        self.assertTrue(result["moved"])

        # 验证调用
        self.mock_file_mover.move_file.assert_called_once()

    def test_execute_file_move_no_change(self):
        """测试执行文件移动（无变化）"""
        file_path = "/test/file.pdf"

        mock_path_plan = {
            "original_path": file_path,
            "primary_path": file_path,  # 路径相同
        }

        mock_file_info = {"file_size": 1024}

        mock_move_result = {
            "moved": False,
            "old_path": file_path,
            "primary_target_path": file_path,
            "message": "文件已在正确位置",
        }

        self.mock_file_mover.move_file.return_value = mock_move_result

        result = self.workflow._execute_file_move(mock_path_plan, mock_file_info)

        # 验证结果
        self.assertEqual(result, mock_move_result)
        self.assertFalse(result["moved"])

    def test_execute_file_move_error(self):
        """测试执行文件移动（错误）"""
        mock_path_plan = {
            "original_path": "/old/path/file.pdf",
            "primary_path": "/new/path/file.pdf",
        }

        mock_file_info = {"file_size": 1024}

        # 模拟移动错误
        self.mock_file_mover.move_file.side_effect = Exception("Permission denied")

        result = self.workflow._execute_file_move(mock_path_plan, mock_file_info)

        # 验证结果
        self.assertFalse(result["moved"])
        self.assertIn("Permission denied", result["error"])

    def test_update_file_index(self):
        """测试更新文件索引"""
        file_path = os.path.join("test", "document.pdf")
        new_category = "财务"
        new_tags = ["发票"]

        mock_file_info = {
            "file_size": 1024,
            "last_modified": "2024-01-01T10:00:00",
        }

        # 模拟索引更新成功
        self.mock_index_updater.update_file_index.return_value = None

        self.workflow._update_file_index(
            file_path, new_category, new_tags, mock_file_info
        )

        # 验证调用
        self.mock_index_updater.update_file_index.assert_called_once()

        # 验证调用参数
        call_args = self.mock_index_updater.update_file_index.call_args
        args, kwargs = call_args

        self.assertEqual(args[0], file_path)  # file_path
        self.assertEqual(args[1], new_category)  # category
        self.assertEqual(args[2], new_tags)  # tags

        # 验证metadata参数
        metadata = kwargs["metadata"]
        self.assertEqual(metadata["file_size"], 1024)
        self.assertEqual(metadata["last_modified"], "2024-01-01T10:00:00")
        self.assertTrue(metadata["reclassified"])
        self.assertIsNotNone(metadata["reclassification_time"])


if __name__ == "__main__":
    unittest.main()
