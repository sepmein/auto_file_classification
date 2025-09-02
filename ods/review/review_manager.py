"""
审核管理器

负责管理文件审核流程、会话管理和审核统计
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.database import Database


class ReviewManager:
    """审核管理器 - 管理文件审核流程"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化数据库连接
        self.database = Database(config)

        self.logger.info("审核管理器初始化完成")

    def create_review_session(self, user_id: str = None) -> str:
        """
        创建新的审核会话

        Args:
            user_id: 用户ID（可选）

        Returns:
            str: 会话ID
        """
        session_id = f"review_{uuid.uuid4().hex[:8]}"

        try:
            self.database.create_review_session(session_id, user_id)
            self.logger.info(f"创建审核会话: {session_id}")
            return session_id
        except Exception as e:
            self.logger.error(f"创建审核会话失败: {e}")
            raise

    def get_files_for_review(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取待审核文件列表

        Args:
            limit: 最大返回数量

        Returns:
            List[Dict[str, Any]]: 待审核文件列表
        """
        try:
            files = self.database.get_files_needing_review(limit)

            # 为每个文件添加额外的元数据
            for file_info in files:
                file_info["review_priority"] = self._calculate_review_priority(
                    file_info
                )
                file_info["last_classified_days"] = self._days_since_classification(
                    file_info
                )

            # 按优先级排序
            files.sort(key=lambda x: x["review_priority"], reverse=True)

            self.logger.info(f"获取到 {len(files)} 个待审核文件")
            return files

        except Exception as e:
            self.logger.error(f"获取待审核文件失败: {e}")
            return []

    def record_review_decision(
        self,
        session_id: str,
        file_id: int,
        original_category: str,
        original_tags: List[str],
        user_category: str,
        user_tags: List[str],
        review_action: str,
        review_reason: str = None,
        processing_time: float = None,
    ) -> bool:
        """
        记录审核决策

        Args:
            session_id: 会话ID
            file_id: 文件ID
            original_category: 原始分类
            original_tags: 原始标签
            user_category: 用户选择分类
            user_tags: 用户选择标签
            review_action: 审核动作 (approved/corrected/rejected)
            review_reason: 审核理由
            processing_time: 处理时间

        Returns:
            bool: 记录是否成功
        """
        try:
            # 记录审核操作
            record_id = self.database.record_review_action(
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

            # 更新文件状态
            if review_action in ["approved", "corrected"]:
                # 标记为不再需要审核
                file_path = self._get_file_path_by_id(file_id)
                if file_path:
                    self.database.update_file_review_status(file_path, False)

            # 更新会话统计
            self._update_session_stats(session_id)

            self.logger.info(f"记录审核决策成功: {review_action} for file {file_id}")
            return True

        except Exception as e:
            self.logger.error(f"记录审核决策失败: {e}")
            return False

    def get_review_statistics(self, session_id: str = None) -> Dict[str, Any]:
        """
        获取审核统计信息

        Args:
            session_id: 会话ID（可选，为空时返回全局统计）

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if session_id:
                # 单个会话统计
                return self.database.get_review_session_stats(session_id)
            else:
                # 全局审核统计
                stats = {}

                # 待审核文件总数
                pending_files = self.database.get_files_needing_review(1000)
                stats["pending_reviews"] = len(pending_files)

                # 审核会话统计
                session_query = "SELECT COUNT(*) as total_sessions FROM review_sessions"
                session_result = self.database.execute_query(session_query)
                stats["total_sessions"] = (
                    session_result[0]["total_sessions"] if session_result else 0
                )

                # 审核记录统计
                records_query = """
                SELECT COUNT(*) as total_reviews,
                       SUM(CASE WHEN review_action = 'approved' THEN 1 ELSE 0 END) as approved,
                       SUM(CASE WHEN review_action = 'corrected' THEN 1 ELSE 0 END) as corrected,
                       SUM(CASE WHEN review_action = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM review_records
                """
                records_result = self.database.execute_query(records_query)
                if records_result:
                    stats["review_actions"] = {
                        "total": records_result[0]["total_reviews"],
                        "approved": records_result[0]["approved"],
                        "corrected": records_result[0]["corrected"],
                        "rejected": records_result[0]["rejected"],
                    }

                return stats

        except Exception as e:
            self.logger.error(f"获取审核统计失败: {e}")
            return {}

    def end_review_session(self, session_id: str) -> bool:
        """
        结束审核会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 操作是否成功
        """
        try:
            updates = {"status": "completed", "end_time": datetime.now().isoformat()}
            success = self.database.update_review_session(session_id, updates)

            if success:
                self.logger.info(f"审核会话结束: {session_id}")

            return success

        except Exception as e:
            self.logger.error(f"结束审核会话失败: {e}")
            return False

    def _calculate_review_priority(self, file_info: Dict[str, Any]) -> float:
        """
        计算审核优先级

        Args:
            file_info: 文件信息

        Returns:
            float: 优先级分数
        """
        priority = 0.0

        # 基于文件大小
        file_size = file_info.get("file_size", 0)
        if file_size > 10 * 1024 * 1024:  # 10MB以上
            priority += 2.0
        elif file_size > 1 * 1024 * 1024:  # 1MB以上
            priority += 1.0

        # 基于分类时间（越久未审核优先级越高）
        days_since = self._days_since_classification(file_info)
        if days_since > 30:
            priority += 3.0
        elif days_since > 7:
            priority += 2.0
        elif days_since > 1:
            priority += 1.0

        # 基于文件类型
        file_ext = file_info.get("file_extension", "").lower()
        important_exts = [".pdf", ".docx", ".xlsx", ".pptx"]
        if file_ext in important_exts:
            priority += 1.5

        return priority

    def _days_since_classification(self, file_info: Dict[str, Any]) -> int:
        """
        计算距离上次分类的天数

        Args:
            file_info: 文件信息

        Returns:
            int: 天数
        """
        last_classified = file_info.get("last_classified")
        if not last_classified:
            return 999  # 如果没有分类记录，给很高优先级

        try:
            if isinstance(last_classified, str):
                last_classified = datetime.fromisoformat(
                    last_classified.replace("Z", "+00:00")
                )
            elif isinstance(last_classified, datetime):
                pass
            else:
                return 999

            now = datetime.now()
            if (
                hasattr(last_classified, "tzinfo")
                and last_classified.tzinfo is not None
            ):
                now = now.replace(tzinfo=last_classified.tzinfo)

            delta = now - last_classified
            return delta.days

        except Exception:
            return 999

    def _get_file_path_by_id(self, file_id: int) -> Optional[str]:
        """
        根据文件ID获取文件路径

        Args:
            file_id: 文件ID

        Returns:
            Optional[str]: 文件路径
        """
        try:
            query = "SELECT file_path FROM files WHERE id = ?"
            result = self.database.execute_query(query, (file_id,))
            return result[0]["file_path"] if result else None
        except Exception:
            return None

    def _update_session_stats(self, session_id: str):
        """
        更新会话统计信息

        Args:
            session_id: 会话ID
        """
        try:
            # 计算已审核文件数
            records_query = "SELECT COUNT(*) as reviewed_count FROM review_records WHERE session_id = ?"
            records_result = self.database.execute_query(records_query, (session_id,))

            if records_result:
                reviewed_count = records_result[0]["reviewed_count"]
                updates = {"reviewed_files": reviewed_count}
                self.database.update_review_session(session_id, updates)

        except Exception as e:
            self.logger.warning(f"更新会话统计失败: {e}")
