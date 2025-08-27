"""
增强规则引擎 - Step 2 多标签支持

支持多标签分类、规则阶段、复杂条件判断等高级功能
"""

import re
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
import json


class EnhancedRuleEngine:
    """增强规则引擎 - 支持多标签分类和复杂规则"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 加载配置
        self.taxonomies = config.get("classification", {}).get("taxonomies", {})
        self.tag_rules = config.get("classification", {}).get("tag_rules", {})
        self.rules_config = config.get("rules", {})

        # 初始化规则
        self.pre_classification_rules = self._load_pre_classification_rules()
        self.post_classification_rules = self._load_post_classification_rules()

        # 减少初始化日志冗余
        if not hasattr(EnhancedRuleEngine, "_init_logged"):
            self.logger.info(f"增强规则引擎初始化完成")
            self.logger.info(f"标签体系: {list(self.taxonomies.keys())}")
            self.logger.info(f"预分类规则: {len(self.pre_classification_rules)}条")
            self.logger.info(f"后分类规则: {len(self.post_classification_rules)}条")
            EnhancedRuleEngine._init_logged = True

    def _load_pre_classification_rules(self) -> List[Dict[str, Any]]:
        """加载预分类规则"""
        rules = self.rules_config.get("pre_classification", [])
        return self._validate_rules(rules, "pre_classification")

    def _load_post_classification_rules(self) -> List[Dict[str, Any]]:
        """加载后分类规则"""
        rules = self.rules_config.get("post_classification", [])
        return self._validate_rules(rules, "post_classification")

    def _validate_rules(
        self, rules: List[Dict[str, Any]], phase: str
    ) -> List[Dict[str, Any]]:
        """验证规则格式"""
        valid_rules = []

        for i, rule in enumerate(rules):
            try:
                # 基本字段验证
                if not all(key in rule for key in ["name", "condition", "action"]):
                    self.logger.warning(f"规则 {i} 缺少必要字段: {rule}")
                    continue

                # 条件验证
                if not self._validate_condition(rule["condition"], rule.get("value")):
                    self.logger.warning(f"规则 {i} 条件格式错误: {rule}")
                    continue

                # 动作验证
                if not self._validate_action(rule["action"], rule):
                    self.logger.warning(f"规则 {i} 动作格式错误: {rule}")
                    continue

                # 添加规则ID和阶段
                rule["rule_id"] = f"{phase}_{i}"
                rule["phase"] = phase
                rule["priority"] = rule.get("priority", "medium")

                valid_rules.append(rule)

            except Exception as e:
                self.logger.error(f"规则 {i} 验证失败: {e}")
                continue

        return valid_rules

    def _validate_condition(self, condition: str, value: Any) -> bool:
        """验证条件格式"""
        valid_conditions = [
            "filename_contains",
            "filename_regex",
            "file_extension",
            "content_contains",
            "content_regex",
            "tags_contain",
            "file_size",
            "creation_date",
            "modification_date",
        ]
        return condition in valid_conditions

    def _validate_action(self, action: str, rule: Dict[str, Any]) -> bool:
        """验证动作格式"""
        valid_actions = [
            "add_tag",
            "set_tag",
            "exclude",
            "require_review",
            "set_path_template",
            "set_confidence",
            "notify",
        ]
        return action in valid_actions

    def apply_pre_classification_rules(
        self, document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用预分类规则

        Args:
            document_data: 文档数据

        Returns:
            Dict[str, Any]: 处理后的文档数据，包含预分类标签
        """
        try:
            self.logger.debug(f"应用预分类规则: {document_data.get('file_path', '')}")

            # 初始化结果
            result = {
                "pre_tags": [],  # 预分类标签
                "excluded": False,  # 是否被排除
                "requires_review": False,  # 是否需要审核
                "applied_rules": [],  # 应用的规则
                "path_template": None,  # 路径模板
                "confidence_boost": 0.0,  # 置信度提升
            }

            # 按优先级排序规则
            sorted_rules = sorted(
                self.pre_classification_rules,
                key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["priority"], 1),
                reverse=True,
            )

            for rule in sorted_rules:
                if self._evaluate_condition(rule, document_data):
                    rule_result = self._execute_action(rule, document_data, result)
                    result["applied_rules"].append(
                        {
                            "rule_id": rule["rule_id"],
                            "rule_name": rule["name"],
                            "result": rule_result,
                        }
                    )

                    # 检查是否应该停止处理
                    if rule["action"] == "exclude":
                        result["excluded"] = True
                        break

                    # 检查是否需要审核
                    if rule["action"] == "require_review":
                        result["requires_review"] = True

            self.logger.info(
                f"预分类规则应用完成: {len(result['applied_rules'])}条规则"
            )
            return result

        except Exception as e:
            self.logger.error(f"预分类规则应用失败: {e}")
            return {"error": str(e), "pre_tags": [], "excluded": False}

    def apply_post_classification_rules(
        self,
        classification_result: Dict[str, Any],
        document_data: Dict[str, Any],
        pre_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        应用后分类规则

        Args:
            classification_result: LLM分类结果
            document_data: 文档数据
            pre_result: 预分类结果

        Returns:
            Dict[str, Any]: 处理后的分类结果
        """
        try:
            self.logger.debug(f"应用后分类规则: {document_data.get('file_path', '')}")

            # 合并预分类结果
            result = classification_result.copy()
            result["pre_classification"] = pre_result

            # 合并预分类标签
            if pre_result.get("pre_tags"):
                if "tags" not in result:
                    result["tags"] = []
                result["tags"].extend(pre_result["pre_tags"])

            # 应用后分类规则
            applied_rules = []

            for rule in self.post_classification_rules:
                if self._evaluate_condition(rule, document_data, result):
                    rule_result = self._execute_action(rule, document_data, result)
                    applied_rules.append(
                        {
                            "rule_id": rule["rule_id"],
                            "rule_name": rule["name"],
                            "result": rule_result,
                        }
                    )

            result["post_rules_applied"] = applied_rules

            # 应用标签规则
            result = self._apply_tag_rules(result)

            self.logger.info(f"后分类规则应用完成: {len(applied_rules)}条规则")
            return result

        except Exception as e:
            self.logger.error(f"后分类规则应用失败: {e}")
            classification_result["rule_error"] = str(e)
            return classification_result

    def _evaluate_condition(
        self,
        rule: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """评估规则条件"""
        try:
            condition = rule["condition"]
            value = rule["value"]

            if condition == "filename_contains":
                filename = Path(document_data.get("file_path", "")).name
                return value.lower() in filename.lower()

            elif condition == "filename_regex":
                filename = Path(document_data.get("file_path", "")).name
                return bool(re.search(value, filename, re.IGNORECASE))

            elif condition == "file_extension":
                file_ext = Path(document_data.get("file_path", "")).suffix.lower()
                if isinstance(value, list):
                    return file_ext in [
                        f".{ext}" if not ext.startswith(".") else ext for ext in value
                    ]
                else:
                    return (
                        file_ext == f".{value}" if not value.startswith(".") else value
                    )

            elif condition == "content_contains":
                content = document_data.get("text_content", "")
                if isinstance(value, list):
                    return any(v.lower() in content.lower() for v in value)
                else:
                    return value.lower() in content.lower()

            elif condition == "content_regex":
                content = document_data.get("text_content", "")
                return bool(re.search(value, content, re.IGNORECASE))

            elif condition == "tags_contain" and classification_result:
                tags = classification_result.get("tags", [])
                if isinstance(value, list):
                    return any(v in tags for v in value)
                else:
                    return value in tags

            elif condition == "file_size":
                file_path = document_data.get("file_path", "")
                if file_path and Path(file_path).exists():
                    size = Path(file_path).stat().st_size
                    return self._evaluate_comparison(size, value)

            elif condition == "creation_date":
                # 实现日期比较逻辑
                pass

            elif condition == "modification_date":
                # 实现日期比较逻辑
                pass

            return False

        except Exception as e:
            self.logger.error(f"条件评估失败: {e}")
            return False

    def _evaluate_comparison(self, actual: Any, expected: str) -> bool:
        """评估比较条件（如 file_size > 10485760）"""
        try:
            # 解析比较操作符
            if ">" in expected:
                threshold = int(expected.split(">")[1].strip())
                return actual > threshold
            elif "<" in expected:
                threshold = int(expected.split("<")[1].strip())
                return actual < threshold
            elif ">=" in expected:
                threshold = int(expected.split(">=")[1].strip())
                return actual >= threshold
            elif "<=" in expected:
                threshold = int(expected.split("<=")[1].strip())
                return actual <= threshold
            elif "==" in expected:
                threshold = int(expected.split("==")[1].strip())
                return actual == threshold
            else:
                return actual == expected
        except:
            return False

    def _execute_action(
        self,
        rule: Dict[str, Any],
        document_data: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行规则动作"""
        try:
            action = rule["action"]
            target = rule.get("target")

            if action == "add_tag":
                if "pre_tags" not in result:
                    result["pre_tags"] = []
                if target not in result["pre_tags"]:
                    result["pre_tags"].append(target)
                return {"action": "add_tag", "target": target, "success": True}

            elif action == "set_tag":
                if "pre_tags" not in result:
                    result["pre_tags"] = []
                result["pre_tags"] = [target] if isinstance(target, str) else target
                return {"action": "set_tag", "target": target, "success": True}

            elif action == "exclude":
                result["excluded"] = True
                return {"action": "exclude", "success": True}

            elif action == "require_review":
                result["requires_review"] = True
                return {"action": "require_review", "success": True}

            elif action == "set_path_template":
                result["path_template"] = target
                return {
                    "action": "set_path_template",
                    "template": target,
                    "success": True,
                }

            elif action == "set_confidence":
                result["confidence_boost"] = float(target)
                return {"action": "set_confidence", "boost": target, "success": True}

            elif action == "notify":
                self.logger.info(f"规则通知: {rule.get('name', '')} - {target}")
                return {"action": "notify", "message": target, "success": True}

            return {"action": action, "success": False, "error": "未知动作"}

        except Exception as e:
            self.logger.error(f"动作执行失败: {e}")
            return {"action": action, "success": False, "error": str(e)}

    def _apply_tag_rules(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """应用标签规则（互斥、优先级等）"""
        try:
            if "tags" not in result:
                return result

            tags = result["tags"]

            # 处理互斥标签
            if self.tag_rules.get("mutually_exclusive"):
                tags = self._resolve_mutually_exclusive_tags(tags)

            # 确定主标签
            if self.tag_rules.get("primary_tag_required", True):
                primary_tag = self._determine_primary_tag(tags)
                if primary_tag:
                    result["primary_tag"] = primary_tag
                    result["secondary_tags"] = [t for t in tags if t != primary_tag]
                else:
                    result["primary_tag"] = tags[0] if tags else None
                    result["secondary_tags"] = tags[1:] if len(tags) > 1 else []
            else:
                result["primary_tag"] = tags[0] if tags else None
                result["secondary_tags"] = tags[1:] if len(tags) > 1 else []

            # 更新结果中的标签列表（使用处理后的标签）
            result["tags"] = tags

            # 限制标签数量
            max_tags = self.tag_rules.get("max_tags_per_file", 5)
            if len(tags) > max_tags:
                result["secondary_tags"] = result["secondary_tags"][: max_tags - 1]
                result["tags"] = [result["primary_tag"]] + result["secondary_tags"]

            return result

        except Exception as e:
            self.logger.error(f"标签规则应用失败: {e}")
            return result

    def _resolve_mutually_exclusive_tags(self, tags: List[str]) -> List[str]:
        """解决互斥标签冲突"""
        try:
            if not self.tag_rules.get("mutually_exclusive"):
                return tags

            exclusive_groups = self.tag_rules["mutually_exclusive"]
            resolved_tags = tags.copy()

            for group in exclusive_groups:
                group_tags = [t for t in tags if t in group]
                if len(group_tags) > 1:
                    # 保留优先级最高的标签
                    priority_order = self.tag_rules.get("priority_order", [])
                    best_tag = self._get_highest_priority_tag(
                        group_tags, priority_order
                    )

                    # 移除其他互斥标签
                    for tag in group_tags:
                        if tag != best_tag and tag in resolved_tags:
                            resolved_tags.remove(tag)
                            self.logger.info(f"移除互斥标签: {tag} (保留: {best_tag})")

            return resolved_tags

        except Exception as e:
            self.logger.error(f"互斥标签解决失败: {e}")
            return tags

    def _get_highest_priority_tag(
        self, tags: List[str], priority_order: List[str]
    ) -> str:
        """获取优先级最高的标签"""
        try:
            if not priority_order:
                return tags[0]

            for taxonomy in priority_order:
                for tag in tags:
                    if tag in self.taxonomies.get(taxonomy, []):
                        return tag

            return tags[0]

        except Exception as e:
            self.logger.error(f"优先级标签确定失败: {e}")
            return tags[0]

    def _determine_primary_tag(self, tags: List[str]) -> Optional[str]:
        """确定主标签"""
        try:
            if not tags:
                return None

            # 按优先级顺序查找主标签
            priority_order = self.tag_rules.get("priority_order", [])

            for taxonomy in priority_order:
                for tag in tags:
                    if tag in self.taxonomies.get(taxonomy, []):
                        return tag

            # 如果没有找到，返回第一个标签
            return tags[0]

        except Exception as e:
            self.logger.error(f"主标签确定失败: {e}")
            return tags[0] if tags else None

    def get_rule_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            "taxonomies": self.taxonomies,
            "tag_rules": self.tag_rules,
            "pre_classification_rules": len(self.pre_classification_rules),
            "post_classification_rules": len(self.post_classification_rules),
            "total_rules": len(self.pre_classification_rules)
            + len(self.post_classification_rules),
        }
