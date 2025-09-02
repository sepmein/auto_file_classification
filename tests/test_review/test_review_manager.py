"""
ReviewManager单元测试

测试审核管理器的核心功能
"""

import unittest
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ods.review.review_manager import ReviewManager


class TestReviewManager(unittest.TestCase):
    """ReviewManager测试类"""

    def setUp(self):
        """测试前准备"""
        self.config = {
            "database": {
                "path": ":memory:",  # 使用内存数据库进行测试
            },
            "classification": {
                "taxonomies": {
                    "主类别": ["工作", "个人", "财务"],
                    "文档类型": ["报告", "合同", "发票"],
                },
                "confidence_threshold": {
                    "auto": 0.85,
                    "review": 0.6,
                    "min": 0.3,
                },
                "tag_rules": {
                    "max_tags_per_file": 5,
                    "primary_tag_required": True,
                },
            },
        }

        # 创建模拟数据库
        self.mock_db = Mock()
        with patch("ods.review.review_manager.Database", return_value=self.mock_db):
            self.manager = ReviewManager(self.config)

    def test_init(self):
        """测试ReviewManager初始化"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.config, self.config)
        self.assertIsNotNone(self.manager.database)

    def test_create_review_session(self):
        """测试创建审核会话"""
        # 模拟数据库返回
        self.mock_db.create_review_session.return_value = 1

        session_id = self.manager.create_review_session("test_user")

        # 验证调用
        self.mock_db.create_review_session.assert_called_once()
        call_args = self.mock_db.create_review_session.call_args[0]
        self.assertEqual(call_args[1], "test_user")  # user_id参数

        # 验证session_id格式
        self.assertTrue(session_id.startswith("review_"))
        self.assertEqual(len(session_id), 15)  # review_ + 7位hex

    def test_create_review_session_no_user(self):
        """测试创建审核会话（无用户ID）"""
        self.mock_db.create_review_session.return_value = 1

        session_id = self.manager.create_review_session()

        self.mock_db.create_review_session.assert_called_once()
        call_args = self.mock_db.create_review_session.call_args[0]
        self.assertIsNone(call_args[1])  # user_id参数为None

    def test_create_review_session_error(self):
        """测试创建审核会话失败"""
        self.mock_db.create_review_session.side_effect = Exception("Database error")

        with self.assertRaises(Exception):
            self.manager.create_review_session("test_user")

    def test_get_files_for_review(self):
        """测试获取待审核文件列表"""
        # 模拟数据库返回
        mock_files = [
            {
                "id": 1,
                "file_path": "/test/file1.pdf",
                "category": "工作",
                "tags": '["报告"]',
                "last_classified": "2024-01-01T10:00:00",
                "file_size": 1024,
                "file_extension": ".pdf",
            },
            {
                "id": 2,
                "file_path": "/test/file2.docx",
                "category": "个人",
                "tags": '["合同"]',
                "last_classified": "2024-01-02T10:00:00",
                "file_size": 2048,
                "file_extension": ".docx",
            },
        ]
        self.mock_db.get_files_needing_review.return_value = mock_files

        files = self.manager.get_files_for_review(limit=10)

        # 验证调用
        self.mock_db.get_files_needing_review.assert_called_once_with(10)

        # 验证结果
        self.assertEqual(len(files), 2)
        self.assertIn("review_priority", files[0])
        self.assertIn("last_classified_days", files[0])

        # 验证优先级计算（PDF文件应有较高优先级）
        pdf_file = next(f for f in files if f["file_extension"] == ".pdf")
        docx_file = next(f for f in files if f["file_extension"] == ".docx")
        self.assertGreaterEqual(
            pdf_file["review_priority"], docx_file["review_priority"]
        )

    def test_get_files_for_review_empty(self):
        """测试获取待审核文件列表（空结果）"""
        self.mock_db.get_files_needing_review.return_value = []

        files = self.manager.get_files_for_review()

        self.assertEqual(len(files), 0)

    def test_record_review_decision_approved(self):
        """测试记录审核决策（批准）"""
        # 模拟数据库方法
        self.mock_db.record_review_action.return_value = 1
        self.mock_db.update_file_review_status.return_value = True

        # 模拟_get_file_path_by_id方法
        with patch.object(
            self.manager, "_get_file_path_by_id", return_value="/test/file.pdf"
        ):
            result = self.manager.record_review_decision(
                session_id="review_12345678",
                file_id=1,
                original_category="工作",
                original_tags=["报告"],
                user_category="工作",
                user_tags=["报告"],
                review_action="approved",
            )

        self.assertTrue(result)

        # 验证数据库调用
        self.mock_db.record_review_action.assert_called_once()
        self.mock_db.update_file_review_status.assert_called_once()

    def test_record_review_decision_corrected(self):
        """测试记录审核决策（修改）"""
        # 模拟数据库方法
        self.mock_db.record_review_action.return_value = 1
        self.mock_db.update_file_review_status.return_value = True

        # 模拟_get_file_path_by_id方法
        with patch.object(
            self.manager, "_get_file_path_by_id", return_value="/test/file.pdf"
        ):
            result = self.manager.record_review_decision(
                session_id="review_12345678",
                file_id=1,
                original_category="工作",
                original_tags=["报告"],
                user_category="财务",
                user_tags=["发票"],
                review_action="corrected",
            )

        self.assertTrue(result)

        # 验证数据库调用
        self.mock_db.record_review_action.assert_called_once()
        self.mock_db.update_file_review_status.assert_called_once()

    def test_record_review_decision_rejected(self):
        """测试记录审核决策（拒绝）"""
        self.mock_db.record_review_action.return_value = 1

        result = self.manager.record_review_decision(
            session_id="review_12345678",
            file_id=1,
            original_category="工作",
            original_tags=["报告"],
            user_category="工作",
            user_tags=["报告"],
            review_action="rejected",
            review_reason="文件损坏",
        )

        self.assertTrue(result)

        # 验证调用参数包含拒绝原因
        call_args = self.mock_db.record_review_action.call_args[0]
        self.assertEqual(call_args[7], "文件损坏")  # review_reason

        # 验证不会调用update_file_review_status（因为不是approved或corrected）
        self.mock_db.update_file_review_status.assert_not_called()

    def test_record_review_decision_error(self):
        """测试记录审核决策失败"""
        self.mock_db.record_review_action.side_effect = Exception("Database error")

        result = self.manager.record_review_decision(
            session_id="review_12345678",
            file_id=1,
            original_category="工作",
            original_tags=["报告"],
            user_category="工作",
            user_tags=["报告"],
            review_action="approved",
        )

        self.assertFalse(result)

    def test_get_review_statistics_global(self):
        """测试获取全局审核统计"""
        # 模拟数据库返回
        self.mock_db.get_files_needing_review.return_value = [
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ]
        self.mock_db.execute_query.side_effect = [
            [{"total_sessions": 5}],  # session查询
            [
                {
                    "total_reviews": 25,
                    "approved": 15,
                    "corrected": 8,
                    "rejected": 2,
                }
            ],  # records查询
        ]

        stats = self.manager.get_review_statistics()

        self.assertIn("pending_reviews", stats)
        self.assertIn("total_sessions", stats)
        self.assertIn("review_actions", stats)
        self.assertEqual(stats["pending_reviews"], 3)
        self.assertEqual(stats["total_sessions"], 5)

    def test_get_review_statistics_session(self):
        """测试获取会话审核统计"""
        session_id = "review_12345678"

        # 模拟数据库返回
        mock_session_stats = {
            "session": {"session_id": session_id, "total_files": 10},
            "records": {"total_reviews": 8, "approved": 5},
            "completion_rate": 80.0,
        }
        self.mock_db.get_review_session_stats.return_value = mock_session_stats

        stats = self.manager.get_review_statistics(session_id)

        self.assertEqual(stats, mock_session_stats)
        self.mock_db.get_review_session_stats.assert_called_once_with(session_id)

    def test_end_review_session(self):
        """测试结束审核会话"""
        self.mock_db.update_review_session.return_value = True

        result = self.manager.end_review_session("review_12345678")

        self.assertTrue(result)
        self.mock_db.update_review_session.assert_called_once()

    def test_end_review_session_error(self):
        """测试结束审核会话失败"""
        self.mock_db.update_review_session.side_effect = Exception("Database error")

        result = self.manager.end_review_session("review_12345678")

        self.assertFalse(result)

    def test_calculate_review_priority(self):
        """测试审核优先级计算"""
        # 测试文件大小优先级
        large_file = {
            "file_size": 15 * 1024 * 1024,  # 15MB
            "last_classified": "2024-01-01T10:00:00",
            "file_extension": ".txt",
        }

        small_file = {
            "file_size": 100 * 1024,  # 100KB
            "last_classified": "2024-01-01T10:00:00",
            "file_extension": ".txt",
        }

        priority_large = self.manager._calculate_review_priority(large_file)
        priority_small = self.manager._calculate_review_priority(small_file)

        self.assertGreater(priority_large, priority_small)

    def test_calculate_review_priority_extension(self):
        """测试文件扩展名优先级"""
        pdf_file = {
            "file_size": 1024,
            "last_classified": "2024-01-01T10:00:00",
            "file_extension": ".pdf",
        }

        txt_file = {
            "file_size": 1024,
            "last_classified": "2024-01-01T10:00:00",
            "file_extension": ".txt",
        }

        priority_pdf = self.manager._calculate_review_priority(pdf_file)
        priority_txt = self.manager._calculate_review_priority(txt_file)

        self.assertGreater(priority_pdf, priority_txt)

    def test_days_since_classification(self):
        """测试计算分类天数"""
        import datetime

        # 模拟3天前的分类
        three_days_ago = (
            datetime.datetime.now() - datetime.timedelta(days=3)
        ).isoformat()
        file_info = {"last_classified": three_days_ago}

        days = self.manager._days_since_classification(file_info)
        self.assertEqual(days, 3)

    def test_days_since_classification_no_date(self):
        """测试计算分类天数（无日期）"""
        file_info = {}

        days = self.manager._days_since_classification(file_info)
        self.assertEqual(days, 999)  # 默认高优先级

    def test_get_file_path_by_id(self):
        """测试根据ID获取文件路径"""
        self.mock_db.execute_query.return_value = [{"file_path": "/test/file.pdf"}]

        path = self.manager._get_file_path_by_id(1)

        self.assertEqual(path, "/test/file.pdf")
        self.mock_db.execute_query.assert_called_once()

    def test_get_file_path_by_id_not_found(self):
        """测试根据ID获取文件路径（未找到）"""
        self.mock_db.execute_query.return_value = []

        path = self.manager._get_file_path_by_id(1)

        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
