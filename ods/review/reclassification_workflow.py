"""
重新分类工作流

处理用户审核反馈后的重新分类流程
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ..core.database import Database
from ..core.enhanced_workflow import EnhancedWorkflow
from ..path_planner.path_planner import PathPlanner
from ..storage.file_mover import FileMover
from ..storage.index_updater import IndexUpdater


class ReclassificationWorkflow:
    """重新分类工作流 - 处理用户审核后的重新分类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化各个模块
        self.database = Database(config)
        self.enhanced_workflow = EnhancedWorkflow(config)
        self.path_planner = PathPlanner(config)
        self.file_mover = FileMover(config)
        self.index_updater = IndexUpdater(config)

        self.logger.info("重新分类工作流初始化完成")

    def reclassify_file(
        self,
        file_path: str,
        new_category: str,
        new_tags: List[str],
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        重新分类单个文件

        Args:
            file_path: 文件路径
            new_category: 新分类
            new_tags: 新标签列表
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 重新分类结果
        """
        try:
            self.logger.info(f"开始重新分类文件: {file_path}")

            # 获取文件信息
            file_info = self._get_file_info(file_path)
            if not file_info:
                return {"success": False, "error": f"文件不存在或未找到: {file_path}"}

            # 创建重新分类状态
            reclassification_state = {
                "file_path": file_path,
                "original_category": file_info.get("category"),
                "original_tags": file_info.get("tags", []),
                "new_category": new_category,
                "new_tags": new_tags,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "status": "processing",
            }

            # 更新数据库中的分类结果
            success = self._update_classification_in_database(
                file_info["id"], new_category, new_tags
            )

            if not success:
                return {"success": False, "error": "更新数据库分类失败"}

            # 重新规划路径
            path_plan = self._replan_file_path(
                file_path, new_category, new_tags, file_info
            )

            if not path_plan:
                return {"success": False, "error": "路径规划失败"}

            # 执行文件移动（如果需要）
            move_result = self._execute_file_move(path_plan, file_info)

            # 更新索引
            self._update_file_index(file_path, new_category, new_tags, file_info)

            # 记录重新分类操作
            self._record_reclassification_operation(
                reclassification_state, path_plan, move_result
            )

            result = {
                "success": True,
                "file_path": file_path,
                "old_category": reclassification_state["original_category"],
                "new_category": new_category,
                "old_tags": reclassification_state["original_tags"],
                "new_tags": new_tags,
                "path_changed": move_result.get("moved", False),
                "old_path": move_result.get("old_path"),
                "new_path": move_result.get("primary_target_path"),
                "processing_time": (
                    datetime.now()
                    - datetime.fromisoformat(reclassification_state["timestamp"])
                ).total_seconds(),
            }

            self.logger.info(f"重新分类完成: {file_path}")
            return result

        except Exception as e:
            self.logger.error(f"重新分类失败: {e}")
            return {"success": False, "error": str(e), "file_path": file_path}

    def reclassify_from_review_records(self, session_id: str) -> Dict[str, Any]:
        """
        根据审核记录批量重新分类

        Args:
            session_id: 审核会话ID

        Returns:
            Dict[str, Any]: 批量重新分类结果
        """
        try:
            self.logger.info(f"开始批量重新分类，会话ID: {session_id}")

            # 获取审核记录中被修改的文件
            corrected_records = self._get_corrected_review_records(session_id)

            if not corrected_records:
                return {
                    "success": True,
                    "message": "没有找到需要重新分类的文件",
                    "processed_files": 0,
                }

            results = []
            success_count = 0
            error_count = 0

            for record in corrected_records:
                file_id = record["file_id"]
                new_category = record["user_category"]
                new_tags = record["user_tags"]

                # 获取文件路径
                file_path = self._get_file_path_by_id(file_id)
                if not file_path:
                    self.logger.warning(f"无法找到文件ID对应的路径: {file_id}")
                    continue

                # 重新分类
                result = self.reclassify_file(
                    file_path=file_path,
                    new_category=new_category,
                    new_tags=new_tags,
                    user_id=record.get("session_user_id"),
                )

                results.append(result)

                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

            summary = {
                "success": True,
                "total_files": len(corrected_records),
                "successful_reclassifications": success_count,
                "failed_reclassifications": error_count,
                "results": results,
            }

            self.logger.info(
                f"批量重新分类完成: {success_count}/{len(corrected_records)} 成功"
            )
            return summary

        except Exception as e:
            self.logger.error(f"批量重新分类失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_files": 0,
                "successful_reclassifications": 0,
                "failed_reclassifications": 0,
            }

    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            Optional[Dict[str, Any]]: 文件信息
        """
        try:
            query = """
            SELECT f.*, fs.category, fs.tags, fs.last_classified
            FROM files f
            LEFT JOIN status fs ON f.file_path = fs.file_path
            WHERE f.file_path = ?
            """
            result = self.database.execute_query(query, (file_path,))
            return result[0] if result else None
        except Exception:
            return None

    def _update_classification_in_database(
        self, file_id: int, new_category: str, new_tags: List[str]
    ) -> bool:
        """
        更新数据库中的分类结果

        Args:
            file_id: 文件ID
            new_category: 新分类
            new_tags: 新标签

        Returns:
            bool: 更新是否成功
        """
        try:
            import json

            # 更新classifications表
            classification_query = """
            INSERT OR REPLACE INTO classifications (file_id, category, tags, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """
            self.database.execute_query(
                classification_query,
                (file_id, new_category, json.dumps(new_tags, ensure_ascii=False)),
                commit=True,
            )

            # 更新status表
            status_query = """
            UPDATE status
            SET category = ?, tags = ?, last_classified = CURRENT_TIMESTAMP,
                needs_review = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE file_path = (SELECT file_path FROM files WHERE id = ?)
            """
            self.database.execute_query(
                status_query,
                (new_category, json.dumps(new_tags, ensure_ascii=False), file_id),
                commit=True,
            )

            return True

        except Exception as e:
            self.logger.error(f"更新数据库分类失败: {e}")
            return False

    def _replan_file_path(
        self,
        file_path: str,
        new_category: str,
        new_tags: List[str],
        file_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        重新规划文件路径

        Args:
            file_path: 文件路径
            new_category: 新分类
            new_tags: 新标签
            file_info: 文件信息

        Returns:
            Optional[Dict[str, Any]]: 路径规划结果
        """
        try:
            # 创建模拟的分类结果
            classification_result = {
                "primary_category": new_category,
                "tags": new_tags,
                "confidence_score": 1.0,  # 用户确认的分类，置信度为1.0
                "needs_review": False,
            }

            # 规划路径
            path_plan = self.path_planner.plan_file_path(
                classification_result=classification_result,
                original_path=file_path,
                file_metadata={
                    "file_size": file_info.get("file_size"),
                    "file_path": file_path,
                },
            )

            return path_plan

        except Exception as e:
            self.logger.error(f"重新规划路径失败: {e}")
            return None

    def _execute_file_move(
        self, path_plan: Dict[str, Any], file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行文件移动

        Args:
            path_plan: 路径规划结果
            file_info: 文件信息

        Returns:
            Dict[str, Any]: 移动结果
        """
        try:
            # 检查是否需要移动（路径是否改变）
            old_path = Path(path_plan["original_path"])
            new_path = Path(path_plan["primary_path"])

            if old_path == new_path:
                # 路径没有改变，只需要更新索引
                return {
                    "moved": False,
                    "old_path": str(old_path),
                    "primary_target_path": str(new_path),
                    "message": "文件已在正确位置",
                }

            # 创建命名结果（保持原文件名）
            naming_result = {
                "new_path": str(new_path),
                "new_filename": new_path.name,
                "original_name": old_path.name,
            }

            # 执行移动
            move_result = self.file_mover.move_file(path_plan, naming_result)

            self.logger.info(f"文件移动完成: {old_path} -> {new_path}")
            return move_result

        except Exception as e:
            self.logger.error(f"执行文件移动失败: {e}")
            return {
                "moved": False,
                "error": str(e),
                "old_path": path_plan.get("original_path"),
                "primary_target_path": path_plan.get("primary_path"),
            }

    def _update_file_index(
        self,
        file_path: str,
        new_category: str,
        new_tags: List[str],
        file_info: Dict[str, Any],
    ):
        """
        更新文件索引

        Args:
            file_path: 文件路径
            new_category: 新分类
            new_tags: 新标签
            file_info: 文件信息
        """
        try:
            # 更新向量索引和LlamaIndex
            self.index_updater.update_file_index(
                file_path=file_path,
                category=new_category,
                tags=new_tags,
                metadata={
                    "file_size": file_info.get("file_size"),
                    "last_modified": file_info.get("modification_time"),
                    "reclassified": True,
                    "reclassification_time": datetime.now().isoformat(),
                },
            )

            self.logger.debug(f"索引更新完成: {file_path}")

        except Exception as e:
            self.logger.warning(f"更新文件索引失败: {e}")

    def _record_reclassification_operation(
        self,
        reclassification_state: Dict[str, Any],
        path_plan: Dict[str, Any],
        move_result: Dict[str, Any],
    ):
        """
        记录重新分类操作

        Args:
            reclassification_state: 重新分类状态
            path_plan: 路径规划结果
            move_result: 移动结果
        """
        try:
            operation_data = {
                "file_id": None,  # 需要从文件路径获取
                "operation_type": "reclassification",
                "old_path": reclassification_state["file_path"],
                "new_path": move_result.get("primary_target_path"),
                "old_name": Path(reclassification_state["file_path"]).name,
                "new_name": Path(move_result.get("primary_target_path", "")).name,
                "category": reclassification_state["new_category"],
                "tags": reclassification_state["new_tags"],
                "success": move_result.get("moved", False),
                "error_message": (
                    move_result.get("errors", [""])[0]
                    if move_result.get("errors")
                    else None
                ),
                "operator": reclassification_state.get("user_id", "system"),
                "metadata": {
                    "original_category": reclassification_state["original_category"],
                    "original_tags": reclassification_state["original_tags"],
                    "reclassification_reason": "user_review",
                },
            }

            self.index_updater.record_operation(operation_data)
            self.logger.debug(
                f"重新分类操作已记录: {reclassification_state['file_path']}"
            )

        except Exception as e:
            self.logger.warning(f"记录重新分类操作失败: {e}")

    def _get_corrected_review_records(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取审核记录中被修改的文件

        Args:
            session_id: 会话ID

        Returns:
            List[Dict[str, Any]]: 被修改的审核记录
        """
        try:
            query = """
            SELECT rr.*, rs.user_id as session_user_id
            FROM review_records rr
            JOIN review_sessions rs ON rr.session_id = rs.session_id
            WHERE rr.session_id = ? AND rr.review_action = 'corrected'
            ORDER BY rr.created_at
            """
            result = self.database.execute_query(query, (session_id,))
            return result
        except Exception:
            return []

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
