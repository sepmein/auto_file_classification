"""
交互式审核界面

提供命令行交互界面用于文件审核
"""

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from .review_manager import ReviewManager
from .reclassification_workflow import ReclassificationWorkflow


class InteractiveReviewer:
    """交互式审核界面"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化审核管理器
        self.review_manager = ReviewManager(config)
        self.reclassification_workflow = ReclassificationWorkflow(config)

        # 获取配置的标签体系
        self.taxonomies = config.get("classification", {}).get("taxonomies", {})
        self.tag_rules = config.get("classification", {}).get("tag_rules", {})

        self.logger.info("交互式审核界面初始化完成")

    def start_review_session(self, user_id: str = None) -> str:
        """
        开始审核会话

        Args:
            user_id: 用户ID

        Returns:
            str: 会话ID
        """
        session_id = self.review_manager.create_review_session(user_id)
        print(f"\n🎯 开始审核会话: {session_id}")
        print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return session_id

    def run_interactive_review(
        self, session_id: str, max_files: int = 10, batch_mode: bool = False
    ):
        """
        运行交互式审核流程

        Args:
            session_id: 会话ID
            max_files: 最大审核文件数
            batch_mode: 是否启用批量模式
        """
        print("\n" + "=" * 60)
        print("📋 文件审核界面")
        if batch_mode:
            print("🔄 批量审核模式")
        print("=" * 60)

        # 获取待审核文件
        files_to_review = self.review_manager.get_files_for_review(max_files)

        if not files_to_review:
            print("✅ 没有找到需要审核的文件！")
            return

        print(f"📂 找到 {len(files_to_review)} 个待审核文件")

        if batch_mode:
            # 批量审核模式
            self._run_batch_review(session_id, files_to_review)
        else:
            # 单文件审核模式
            self._run_single_review(session_id, files_to_review)

    def _run_single_review(
        self, session_id: str, files_to_review: List[Dict[str, Any]]
    ):
        """
        运行单文件审核模式

        Args:
            session_id: 会话ID
            files_to_review: 待审核文件列表
        """
        reviewed_count = 0

        for i, file_info in enumerate(files_to_review, 1):
            print(f"\n{'='*50}")
            print(f"📄 文件 {i}/{len(files_to_review)}")
            print(f"{'='*50}")

            if self._review_single_file(session_id, file_info):
                reviewed_count += 1
            else:
                break  # 用户选择退出

        # 显示会话总结
        self._show_session_summary(session_id, reviewed_count)

    def _run_batch_review(self, session_id: str, files_to_review: List[Dict[str, Any]]):
        """
        运行批量审核模式

        Args:
            session_id: 会话ID
            files_to_review: 待审核文件列表
        """
        print("\n🔄 批量审核模式")
        print("您可以对多个文件应用相同的操作")
        print("-" * 40)

        # 显示文件列表
        self._display_batch_file_list(files_to_review)

        # 获取批量操作
        batch_decision = self._get_batch_decision()

        if batch_decision["action"] == "individual":
            # 切换到单文件模式
            self._run_single_review(session_id, files_to_review)
            return

        if batch_decision["action"] == "cancel":
            print("❌ 批量审核已取消")
            return

        # 应用批量操作
        applied_count = 0
        for file_info in files_to_review:
            try:
                # 为每个文件创建决策
                file_decision = batch_decision.copy()

                # 如果是修改分类，需要为每个文件调整
                if file_decision["action"] == "apply_template":
                    file_decision = self._apply_template_to_file(
                        file_info, batch_decision["template"]
                    )

                # 记录决策
                self._record_user_decision(session_id, file_info, file_decision)
                applied_count += 1

                print(f"✅ 已处理: {Path(file_info['file_path']).name}")

            except Exception as e:
                print(f"❌ 处理失败 {Path(file_info['file_path']).name}: {e}")

        print(f"\n📊 批量处理完成: {applied_count}/{len(files_to_review)} 个文件")
        self._show_session_summary(session_id, applied_count)

    def _display_batch_file_list(self, files: List[Dict[str, Any]]):
        """
        显示批量文件列表

        Args:
            files: 文件列表
        """
        print("📋 待审核文件列表:")
        print("-" * 60)

        for i, file_info in enumerate(files[:10], 1):  # 只显示前10个
            file_name = Path(file_info["file_path"]).name
            category = file_info.get("category", "未分类")
            priority = file_info.get("review_priority", 0)

            priority_icon = "⭐" if priority > 2 else "⚠️" if priority > 1 else "📝"
            print(f"{i:2d}. {priority_icon} {file_name}")
            print(f"      📁 分类: {category}")

        if len(files) > 10:
            print(f"      ... 还有 {len(files) - 10} 个文件")

        print("-" * 60)

    def _get_batch_decision(self) -> Dict[str, Any]:
        """
        获取批量操作决策

        Returns:
            Dict[str, Any]: 批量决策
        """
        while True:
            print("\n批量操作选项:")
            print("1. ✅ 批量批准所有文件（保持当前分类）")
            print("2. 🚫 批量拒绝所有文件")
            print("3. 📝 应用分类模板")
            print("4. 🔄 切换到逐个审核模式")
            print("5. ❌ 取消批量审核")
            print("-" * 40)

            choice = input("请选择批量操作 (1-5): ").strip()

            if choice == "1":
                return {"action": "approved"}
            elif choice == "2":
                reason = input("请输入批量拒绝理由: ").strip()
                return {"action": "rejected", "reason": reason}
            elif choice == "3":
                template = self._select_batch_template()
                return {"action": "apply_template", "template": template}
            elif choice == "4":
                return {"action": "individual"}
            elif choice == "5":
                return {"action": "cancel"}
            else:
                print("❌ 无效选择，请重新输入")

    def _select_batch_template(self) -> Dict[str, Any]:
        """
        选择批量分类模板

        Returns:
            Dict[str, Any]: 分类模板
        """
        print("\n📝 选择分类模板")

        # 显示可选的主类别
        print("可选的主类别:")
        main_categories = list(self.taxonomies.get("主类别", {}).keys())
        for i, category in enumerate(main_categories, 1):
            print(f"{i}. {category}")

        # 选择主类别
        while True:
            try:
                choice = int(input("选择主类别: ").strip())
                if 1 <= choice <= len(main_categories):
                    selected_category = main_categories[choice - 1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(main_categories)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")

        # 选择标签
        print(
            f"\n为 '{selected_category}' 选择标签 (可多选，输入数字用逗号分隔，输入0跳过):"
        )

        selected_tags = []
        for taxonomy_name, tags in self.taxonomies.items():
            if taxonomy_name == "主类别":
                continue

            print(f"\n{taxonomy_name}:")
            for i, tag in enumerate(tags, 1):
                print(f"{i}. {tag}")

            choices = input(f"选择 {taxonomy_name} 标签: ").strip()
            if choices and choices != "0":
                try:
                    indices = [int(x.strip()) for x in choices.split(",")]
                    for idx in indices:
                        if 1 <= idx <= len(tags):
                            selected_tags.append(tags[idx - 1])
                except ValueError:
                    print(f"❌ {taxonomy_name} 标签选择无效，跳过")

        return {"category": selected_category, "tags": selected_tags}

    def _apply_template_to_file(
        self, file_info: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将模板应用到单个文件

        Args:
            file_info: 文件信息
            template: 分类模板

        Returns:
            Dict[str, Any]: 应用模板后的决策
        """
        # 这里可以根据文件特征调整模板
        # 例如，根据文件名自动调整标签

        decision = {
            "action": "corrected",
            "category": template["category"],
            "tags": template["tags"].copy(),
        }

        # 根据文件类型添加特定标签
        file_ext = Path(file_info["file_path"]).suffix.lower()
        if file_ext in [".pdf", ".docx", ".pptx"] and "报告" not in decision["tags"]:
            if "报告" in self.taxonomies.get("文档类型", []):
                decision["tags"].append("报告")

        return decision

    def _review_single_file(self, session_id: str, file_info: Dict[str, Any]) -> bool:
        """
        审核单个文件

        Args:
            session_id: 会话ID
            file_info: 文件信息

        Returns:
            bool: 是否继续审核
        """
        try:
            # 显示文件信息
            self._display_file_info(file_info)

            # 获取用户决策
            decision = self._get_user_decision(file_info)

            if decision["action"] == "skip":
                return True
            elif decision["action"] == "quit":
                return False

            # 记录审核决策
            self._record_user_decision(session_id, file_info, decision)

            return True

        except KeyboardInterrupt:
            print("\n\n⚠️ 审核被用户中断")
            return False
        except Exception as e:
            print(f"\n❌ 审核文件时出错: {e}")
            return True

    def _display_file_info(self, file_info: Dict[str, Any]):
        """
        显示文件信息

        Args:
            file_info: 文件信息
        """
        file_path = file_info.get("file_path", "")
        file_name = Path(file_path).name

        print(f"📁 文件: {file_name}")
        print(f"📂 路径: {file_path}")

        # 文件大小
        file_size = file_info.get("file_size", 0)
        if file_size:
            size_mb = file_size / (1024 * 1024)
            print(f"📊 大小: {size_mb:.2f} MB")

        # 当前分类
        current_category = file_info.get("category", "未分类")
        current_tags = file_info.get("tags", [])
        if isinstance(current_tags, str):
            try:
                current_tags = json.loads(current_tags)
            except:
                current_tags = []

        print(f"🏷️  当前分类: {current_category}")
        if current_tags:
            print(f"🏷️  当前标签: {', '.join(current_tags)}")

        # 分类时间
        last_classified = file_info.get("last_classified")
        if last_classified:
            print(f"🕒 分类时间: {last_classified}")

        # 优先级信息
        priority = file_info.get("review_priority", 0)
        if priority > 2:
            print(f"⭐ 优先级: 高 ({priority:.1f})")
        elif priority > 1:
            print(f"⚠️  优先级: 中 ({priority:.1f})")
        else:
            print(f"📝 优先级: 低 ({priority:.1f})")

    def _get_user_decision(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取用户审核决策

        Args:
            file_info: 文件信息

        Returns:
            Dict[str, Any]: 用户决策
        """
        while True:
            print("\n" + "-" * 40)
            print("请选择操作:")
            print("1. ✅ 批准当前分类")
            print("2. ✏️  修改分类")
            print("3. 🚫 拒绝/标记为问题")
            print("4. ⏭️  跳过此文件")
            print("5. 🛑 退出审核")
            print("-" * 40)

            choice = input("请输入选择 (1-5): ").strip()

            if choice == "1":
                return {
                    "action": "approved",
                    "category": file_info.get("category"),
                    "tags": file_info.get("tags", []),
                }
            elif choice == "2":
                return self._get_modification_decision(file_info)
            elif choice == "3":
                reason = input("请输入拒绝理由: ").strip()
                return {
                    "action": "rejected",
                    "reason": reason,
                    "category": file_info.get("category"),
                    "tags": file_info.get("tags", []),
                }
            elif choice == "4":
                return {"action": "skip"}
            elif choice == "5":
                return {"action": "quit"}
            else:
                print("❌ 无效选择，请重新输入")

    def _get_modification_decision(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取修改分类的决策

        Args:
            file_info: 文件信息

        Returns:
            Dict[str, Any]: 修改决策
        """
        print("\n📝 修改分类")
        print("-" * 30)

        # 显示可选的分类
        print("可选的主类别:")
        for i, category in enumerate(self.taxonomies.get("主类别", []), 1):
            print(f"{i}. {category}")

        # 让用户选择新分类
        while True:
            try:
                choice = int(input("选择主类别 (输入数字): ").strip())
                categories = self.taxonomies.get("主类别", [])
                if 1 <= choice <= len(categories):
                    new_category = categories[choice - 1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(categories)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")

        # 选择标签
        new_tags = self._select_tags()

        return {"action": "corrected", "category": new_category, "tags": new_tags}

    def _select_tags(self) -> List[str]:
        """
        让用户选择标签

        Returns:
            List[str]: 选择的标签
        """
        selected_tags = []

        print("\n🏷️ 选择标签 (可多选，输入数字用逗号分隔，输入0结束)")

        for taxonomy_name, tags in self.taxonomies.items():
            if taxonomy_name == "主类别":
                continue

            print(f"\n{taxonomy_name}:")
            for i, tag in enumerate(tags, 1):
                print(f"{i}. {tag}")

            while True:
                choices = input(f"选择 {taxonomy_name} 标签: ").strip()

                if choices == "0":
                    break

                try:
                    indices = [int(x.strip()) for x in choices.split(",")]
                    for idx in indices:
                        if 1 <= idx <= len(tags):
                            selected_tags.append(tags[idx - 1])
                        else:
                            print(f"❌ 无效选择: {idx}")
                    break
                except ValueError:
                    print("❌ 请输入有效的数字，用逗号分隔")

        return selected_tags

    def _record_user_decision(
        self, session_id: str, file_info: Dict[str, Any], decision: Dict[str, Any]
    ):
        """
        记录用户审核决策

        Args:
            session_id: 会话ID
            file_info: 文件信息
            decision: 用户决策
        """
        try:
            # 获取原始信息
            original_category = file_info.get("category", "")
            original_tags = file_info.get("tags", [])
            if isinstance(original_tags, str):
                try:
                    original_tags = json.loads(original_tags)
                except:
                    original_tags = []

            # 记录审核操作
            success = self.review_manager.record_review_decision(
                session_id=session_id,
                file_id=file_info.get("id"),
                original_category=original_category,
                original_tags=original_tags,
                user_category=decision.get("category", ""),
                user_tags=decision.get("tags", []),
                review_action=decision["action"],
                review_reason=decision.get("reason"),
                processing_time=0.5,  # 估算的处理时间
            )

            if success:
                print(f"✅ 审核记录已保存: {decision['action']}")

                # 如果用户修改了分类，触发重新分类工作流
                if decision["action"] == "corrected":
                    file_path = file_info.get("file_path", "")
                    new_category = decision.get("category", "")
                    new_tags = decision.get("tags", [])

                    print(f"🔄 正在重新分类文件...")
                    reclass_result = self.reclassification_workflow.reclassify_file(
                        file_path=file_path,
                        new_category=new_category,
                        new_tags=new_tags,
                        user_id=session_id.split("_")[1] if "_" in session_id else None,
                    )

                    if reclass_result["success"]:
                        print(f"✅ 重新分类完成!")
                        if reclass_result.get("path_changed", False):
                            print(
                                f"📁 文件已移动: {reclass_result['old_path']} -> {reclass_result['new_path']}"
                            )
                        else:
                            print(f"📁 文件位置保持不变")
                    else:
                        print(
                            f"❌ 重新分类失败: {reclass_result.get('error', '未知错误')}"
                        )
            else:
                print("❌ 保存审核记录失败")

        except Exception as e:
            print(f"❌ 记录审核决策时出错: {e}")

    def _show_session_summary(self, session_id: str, reviewed_count: int):
        """
        显示会话总结

        Args:
            session_id: 会话ID
            reviewed_count: 已审核文件数
        """
        print(f"\n{'='*50}")
        print("📊 审核会话总结")
        print(f"{'='*50}")

        # 获取会话统计
        stats = self.review_manager.get_review_statistics(session_id)

        if stats:
            session_info = stats.get("session", {})
            records_info = stats.get("records", {})

            print(f"🎯 会话ID: {session_id}")
            print(f"📂 已审核: {reviewed_count} 个文件")
            print(f"📊 批准: {records_info.get('approved', 0)} 个")
            print(f"✏️  修改: {records_info.get('corrected', 0)} 个")
            print(f"🚫 拒绝: {records_info.get('rejected', 0)} 个")

            completion_rate = stats.get("completion_rate", 0)
            print(f"📈 完成率: {completion_rate:.1f}%")
        else:
            print(f"📂 已审核: {reviewed_count} 个文件")

        print("\n✅ 审核会话完成！")
        print("💡 您可以使用 'ods apply' 重新处理已修改分类的文件")

    def get_pending_reviews_count(self) -> int:
        """
        获取待审核文件数量

        Returns:
            int: 待审核文件数量
        """
        stats = self.review_manager.get_review_statistics()
        return stats.get("pending_reviews", 0)
