"""
Database Review功能单元测试

测试数据库中review相关功能的实现
"""

import unittest
import json
from unittest.mock import Mock, patch
from datetime import datetime


class TestDatabaseReview(unittest.TestCase):
    """Database Review测试类"""

    def setUp(self):
        """测试前准备"""
        from ods.core.database import Database

        self.config = {
            "database": {
                "path": ":memory:",  # 使用内存数据库进行测试
            },
        }

        # 创建模拟数据库连接
        self.mock_conn = Mock()
        self.mock_cursor = Mock()

        # 设置mock对象
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_cursor.execute.return_value = None
        self.mock_conn.commit.return_value = None
        self.mock_cursor.lastrowid = 1

        # 模拟Database的所有外部依赖
        with patch("sqlite3.connect", return_value=self.mock_conn), patch(
            "ods.core.database.Database._init_database"
        ), patch(
            "ods.core.database.Database.get_connection", return_value=self.mock_conn
        ), patch.object(
            Database, "execute_query", return_value=[]
        ):
            self.database = Database(self.config)

    def test_create_review_session(self):
        """测试创建审核会话"""
        self.mock_cursor.lastrowid = 1
        self.mock_cursor.execute.return_value = None
        self.mock_conn.commit.return_value = None

        session_id = "review_12345678"
        user_id = "test_user"

        result = self.database.create_review_session(session_id, user_id)

        # 验证结果
        self.assertEqual(result, 1)

        # 验证SQL执行
        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        # 验证SQL语句
        self.assertIn("INSERT INTO review_sessions", sql)
        self.assertIn("session_id", sql)
        self.assertIn("user_id", sql)

        # 验证参数
        self.assertEqual(params[0], session_id)
        self.assertEqual(params[1], user_id)

        # 验证提交
        self.mock_conn.commit.assert_called_once()

    def test_create_review_session_no_user(self):
        """测试创建审核会话（无用户ID）"""
        self.mock_cursor.lastrowid = 2

        result = self.database.create_review_session("review_87654321")

        # 验证参数
        call_args = self.mock_cursor.execute.call_args[0]
        params = call_args[1]
        self.assertIsNone(params[1])  # user_id应为None

    def test_get_files_needing_review(self):
        """测试获取需要审核的文件列表"""
        # 模拟查询结果
        mock_files = [
            {
                "id": 1,
                "file_path": "/test/file1.pdf",
                "category": "工作",
                "tags": '["报告"]',
                "last_classified": "2024-01-01T10:00:00",
                "file_size": 1024,
                "needs_review": True,
                "updated_at": "2024-01-01T10:00:00",
            },
            {
                "id": 2,
                "file_path": "/test/file2.docx",
                "category": "个人",
                "tags": '["合同"]',
                "last_classified": "2024-01-02T10:00:00",
                "file_size": 2048,
                "needs_review": True,
                "updated_at": "2024-01-02T10:00:00",
            },
        ]

        self.database.execute_query = Mock(return_value=mock_files)

        result = self.database.get_files_needing_review(limit=10)

        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["file_path"], "/test/file1.pdf")
        self.assertEqual(result[1]["file_path"], "/test/file2.docx")

        # 验证查询调用
        self.database.execute_query.assert_called_once()
        call_args = self.database.execute_query.call_args[0]
        sql = call_args[0]

        # 验证SQL包含必要的条件
        self.assertIn("needs_review = TRUE", sql)
        self.assertIn("status = 'processed'", sql)
        self.assertIn("ORDER BY", sql)
        self.assertIn("LIMIT", sql)

    def test_get_files_needing_review_empty(self):
        """测试获取需要审核的文件列表（空结果）"""
        self.database.execute_query = Mock(return_value=[])

        result = self.database.get_files_needing_review()

        self.assertEqual(len(result), 0)

    def test_update_file_review_status(self):
        """测试更新文件审核状态"""
        file_path = "/test/document.pdf"
        needs_review = False

        # 模拟更新成功
        self.mock_cursor.rowcount = 1

        result = self.database.update_file_review_status(file_path, needs_review)

        # 验证结果
        self.assertTrue(result)

        # 验证SQL执行
        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        # 验证SQL语句
        self.assertIn("UPDATE status", sql)
        self.assertIn("needs_review = ?", sql)
        self.assertIn("updated_at", sql)

        # 验证参数
        self.assertEqual(params[0], needs_review)
        self.assertEqual(params[1], file_path)

    def test_update_file_review_status_not_found(self):
        """测试更新文件审核状态（文件不存在）"""
        file_path = "/test/nonexistent.pdf"

        # 模拟更新失败（没有行被影响）
        self.mock_cursor.rowcount = 0

        result = self.database.update_file_review_status(file_path, True)

        # 验证结果
        self.assertFalse(result)

    def test_record_review_action(self):
        """测试记录审核操作"""
        session_id = "review_12345678"
        file_id = 1
        original_category = "工作"
        original_tags = ["报告"]
        user_category = "财务"
        user_tags = ["发票"]
        review_action = "corrected"
        review_reason = "更准确的分类"
        processing_time = 2.5

        self.mock_cursor.lastrowid = 100

        result = self.database.record_review_action(
            session_id=session_id,
            file_id=file_id,
            original_category=original_category,
            original_tags=original_tags,
            user_category=user_category,
            user_tags=user_tags,
            review_action=review_action,
            review_reason=review_reason,
            processing_time=processing_time,
        )

        # 验证结果
        self.assertEqual(result, 100)

        # 验证SQL执行
        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        # 验证SQL语句
        self.assertIn("INSERT INTO review_records", sql)

        # 验证参数
        self.assertEqual(params[0], session_id)
        self.assertEqual(params[1], file_id)
        self.assertEqual(params[2], original_category)
        self.assertEqual(params[3], json.dumps(original_tags, ensure_ascii=False))
        self.assertEqual(params[4], user_category)
        self.assertEqual(params[5], json.dumps(user_tags, ensure_ascii=False))
        self.assertEqual(params[6], review_action)
        self.assertEqual(params[7], review_reason)
        self.assertEqual(params[8], processing_time)

    def test_record_review_action_minimal_params(self):
        """测试记录审核操作（最小参数）"""
        result = self.database.record_review_action(
            session_id="review_12345678",
            file_id=1,
            original_category="工作",
            original_tags=["报告"],
            user_category="财务",
            user_tags=["发票"],
            review_action="approved",
        )

        # 验证调用成功
        self.mock_cursor.execute.assert_called_once()

        # 验证参数（reason和processing_time应为None）
        call_args = self.mock_cursor.execute.call_args[0]
        params = call_args[1]
        self.assertIsNone(params[7])  # review_reason
        self.assertIsNone(params[8])  # processing_time

    def test_get_review_session_stats(self):
        """测试获取审核会话统计"""
        session_id = "review_12345678"

        # 模拟会话查询结果
        mock_session = {
            "session_id": session_id,
            "user_id": "test_user",
            "total_files": 10,
            "reviewed_files": 8,
            "status": "active",
        }

        # 模拟记录统计结果
        mock_records_stats = {
            "total_reviews": 8,
            "approved": 5,
            "corrected": 2,
            "rejected": 1,
            "avg_processing_time": 1.5,
        }

        self.database.execute_query = Mock(
            side_effect=[
                [mock_session],  # 会话查询
                [mock_records_stats],  # 记录统计查询
            ]
        )

        result = self.database.get_review_session_stats(session_id)

        # 验证结果结构
        self.assertIn("session", result)
        self.assertIn("records", result)
        self.assertIn("completion_rate", result)

        # 验证数据
        self.assertEqual(result["session"], mock_session)
        self.assertEqual(result["records"], mock_records_stats)
        self.assertEqual(result["completion_rate"], 80.0)  # 8/10 * 100

    def test_get_review_session_stats_not_found(self):
        """测试获取审核会话统计（会话不存在）"""
        self.database.execute_query = Mock(return_value=[])

        result = self.database.get_review_session_stats("nonexistent_session")

        self.assertEqual(result, {})

    def test_get_review_session_stats_no_records(self):
        """测试获取审核会话统计（无审核记录）"""
        mock_session = {
            "session_id": "review_12345678",
            "total_files": 10,
        }

        self.database.execute_query = Mock(
            side_effect=[
                [mock_session],  # 会话查询
                [],  # 无记录
            ]
        )

        result = self.database.get_review_session_stats("review_12345678")

        # 验证完成率为0
        self.assertEqual(result["completion_rate"], 0)

    def test_update_review_session(self):
        """测试更新审核会话"""
        session_id = "review_12345678"
        updates = {
            "status": "completed",
            "reviewed_files": 10,
            "end_time": "2024-01-01T12:00:00",
        }

        # 模拟更新成功
        self.mock_cursor.rowcount = 1

        result = self.database.update_review_session(session_id, updates)

        # 验证结果
        self.assertTrue(result)

        # 验证SQL执行
        self.mock_cursor.execute.assert_called_once()
        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]
        params = call_args[1]

        # 验证SQL语句
        self.assertIn("UPDATE review_sessions", sql)
        self.assertIn("status = ?", sql)
        self.assertIn("reviewed_files = ?", sql)
        self.assertIn("end_time = ?", sql)
        self.assertIn("updated_at", sql)

        # 验证参数
        self.assertEqual(params[0], "completed")
        self.assertEqual(params[1], 10)
        self.assertEqual(params[2], "2024-01-01T12:00:00")
        self.assertEqual(params[3], session_id)

    def test_update_review_session_no_updates(self):
        """测试更新审核会话（无更新内容）"""
        result = self.database.update_review_session("review_12345678", {})

        # 验证结果
        self.assertFalse(result)

        # 验证未执行SQL
        self.mock_cursor.execute.assert_not_called()

    def test_update_review_session_not_found(self):
        """测试更新审核会话（会话不存在）"""
        updates = {"status": "completed"}

        # 模拟更新失败
        self.mock_cursor.rowcount = 0

        result = self.database.update_review_session("nonexistent_session", updates)

        # 验证结果
        self.assertFalse(result)

    def test_database_error_handling(self):
        """测试数据库错误处理"""
        # 模拟数据库连接错误
        self.mock_conn.cursor.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception):
            self.database.create_review_session("test_session")

    def test_json_serialization(self):
        """测试JSON序列化"""
        tags = ["财务", "发票", "重要"]

        # 在record_review_action中测试JSON序列化
        self.database.record_review_action(
            session_id="test",
            file_id=1,
            original_category="工作",
            original_tags=tags,
            user_category="财务",
            user_tags=tags,
            review_action="approved",
        )

        # 验证JSON序列化调用
        call_args = self.mock_cursor.execute.call_args[0]
        params = call_args[1]

        # 验证tags被正确序列化为JSON字符串
        self.assertEqual(params[3], json.dumps(tags, ensure_ascii=False))
        self.assertEqual(params[5], json.dumps(tags, ensure_ascii=False))

    def test_timestamp_handling(self):
        """测试时间戳处理"""
        # 测试CURRENT_TIMESTAMP的使用
        self.database.create_review_session("test_session")

        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]

        # 验证SQL包含时间戳字段
        self.assertIn("created_at", sql)
        self.assertIn("CURRENT_TIMESTAMP", sql)

    def test_foreign_key_constraints(self):
        """测试外键约束"""
        # 测试review_records表的外键约束
        self.database.record_review_action(
            session_id="review_12345678",
            file_id=1,
            original_category="工作",
            original_tags=["报告"],
            user_category="财务",
            user_tags=["发票"],
            review_action="approved",
        )

        call_args = self.mock_cursor.execute.call_args[0]
        sql = call_args[0]

        # 验证外键约束（通过FOREIGN KEY引用验证）
        # 虽然无法直接测试约束，但可以验证SQL结构
        self.assertIn("session_id", sql)
        self.assertIn("file_id", sql)


if __name__ == "__main__":
    unittest.main()
