"""
规则检查器模块
负责应用用户定义的规则来调整分类结果
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import yaml


class RuleChecker:
    """规则检查器 - 应用用户定义的规则调整分类结果"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 规则配置
        self.rules_config = config.get("rules", {})
        self.rules_file = self.rules_config.get("rules_file", "config/rules.yaml")
        self.enable_rules = self.rules_config.get("enable_rules", True)
        self.strict_mode = self.rules_config.get("strict_mode", False)

        # 规则类型 (先初始化，再加载规则)
        self.rule_types = {
            "file_extension": self._check_file_extension_rules,
            "file_name": self._check_file_name_rules,
            "content_keywords": self._check_content_keywords_rules,
            "file_size": self._check_file_size_rules,
            "file_path": self._check_file_path_rules,
            "custom": self._check_custom_rules,
        }

        # 加载规则
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        """加载规则配置"""
        try:
            if not self.enable_rules:
                self.logger.info("规则检查已禁用")
                return {}

            rules_path = Path(self.rules_file)
            if not rules_path.exists():
                self.logger.warning(f"规则文件不存在: {rules_path}")
                return self._get_default_rules()

            with open(rules_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)

            # 验证规则格式
            validated_rules = self._validate_rules(rules)
            self.logger.info(f"成功加载 {len(validated_rules)} 条规则")
            return validated_rules

        except Exception as e:
            self.logger.error(f"加载规则失败: {e}")
            return self._get_default_rules()

    def _get_default_rules(self) -> Dict[str, Any]:
        """获取默认规则"""
        return {
            "file_extension": {
                ".pdf": {"category": "文档", "priority": 1},
                ".docx": {"category": "文档", "priority": 1},
                ".doc": {"category": "文档", "priority": 1},
                ".txt": {"category": "文本", "priority": 1},
                ".md": {"category": "文本", "priority": 1},
                ".jpg": {"category": "图片", "priority": 1},
                ".png": {"category": "图片", "priority": 1},
                ".xlsx": {"category": "表格", "priority": 1},
                ".pptx": {"category": "演示", "priority": 1},
            },
            "file_name": {
                "发票": {"category": "财务", "priority": 2},
                "合同": {"category": "工作", "priority": 2},
                "简历": {"category": "个人", "priority": 2},
                "报告": {"category": "工作", "priority": 2},
            },
            "content_keywords": {
                "发票": {"category": "财务", "priority": 3},
                "金额": {"category": "财务", "priority": 3},
                "合同": {"category": "工作", "priority": 3},
                "项目": {"category": "工作", "priority": 3},
                "个人": {"category": "个人", "priority": 3},
            },
        }

    def _validate_rules(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """验证规则格式"""
        validated_rules = {}

        for rule_type, rule_data in rules.items():
            if rule_type in self.rule_types:
                if isinstance(rule_data, dict):
                    validated_rules[rule_type] = rule_data
                else:
                    self.logger.warning(f"规则类型 {rule_type} 格式无效，跳过")
            else:
                self.logger.warning(f"未知规则类型: {rule_type}")

        return validated_rules

    def apply_rules(
        self, classification_result: Dict[str, Any], document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用规则调整分类结果"""
        try:
            if not self.enable_rules or not self.rules:
                return classification_result

            self.logger.info("开始应用规则检查")

            # 收集所有规则匹配结果
            rule_matches = []

            for rule_type, rule_checker in self.rule_types.items():
                if rule_type in self.rules:
                    matches = rule_checker(document_data, self.rules[rule_type])
                    rule_matches.extend(matches)

            # 如果没有规则匹配，返回原结果
            if not rule_matches:
                self.logger.info("没有规则匹配，保持原分类结果")
                return classification_result

            # 按优先级排序规则匹配
            rule_matches.sort(key=lambda x: x["priority"], reverse=True)

            # 应用最高优先级的规则
            top_rule = rule_matches[0]
            self.logger.info(
                f"应用规则: {top_rule['rule_type']} -> {top_rule['category']}"
            )

            # 调整分类结果
            adjusted_result = classification_result.copy()
            adjusted_result["primary_category"] = top_rule["category"]
            adjusted_result["rule_applied"] = {
                "rule_type": top_rule["rule_type"],
                "rule_value": top_rule["rule_value"],
                "priority": top_rule["priority"],
                "confidence_boost": 0.2,  # 规则匹配提高置信度
            }

            # 提高置信度
            original_confidence = adjusted_result.get("confidence_score", 0.0)
            adjusted_result["confidence_score"] = min(1.0, original_confidence + 0.2)

            # 更新推理
            original_reasoning = adjusted_result.get("reasoning", "")
            adjusted_result["reasoning"] = (
                f"{original_reasoning} (应用规则: {top_rule['rule_type']}={top_rule['rule_value']})"
            )

            # 如果置信度足够高，不需要复核
            if adjusted_result["confidence_score"] >= 0.8:
                adjusted_result["needs_review"] = False

            self.logger.info(
                f"规则应用完成，新类别: {adjusted_result['primary_category']}"
            )
            return adjusted_result

        except Exception as e:
            self.logger.error(f"应用规则失败: {e}")
            return classification_result

    def _check_file_extension_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查文件扩展名规则"""
        matches = []
        file_path = document_data.get("file_path", "")

        if file_path:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in rules:
                rule_info = rules[file_ext]
                matches.append(
                    {
                        "rule_type": "file_extension",
                        "rule_value": file_ext,
                        "category": rule_info["category"],
                        "priority": rule_info.get("priority", 1),
                    }
                )

        return matches

    def _check_file_name_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查文件名规则"""
        matches = []
        file_path = document_data.get("file_path", "")

        if file_path:
            file_name = Path(file_path).stem.lower()
            for keyword, rule_info in rules.items():
                if keyword.lower() in file_name:
                    matches.append(
                        {
                            "rule_type": "file_name",
                            "rule_value": keyword,
                            "category": rule_info["category"],
                            "priority": rule_info.get("priority", 1),
                        }
                    )

        return matches

    def _check_content_keywords_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查内容关键词规则"""
        matches = []
        text_content = document_data.get("text_content", "")
        summary = document_data.get("summary", "")

        # 合并文本内容
        full_text = f"{text_content} {summary}".lower()

        for keyword, rule_info in rules.items():
            if keyword.lower() in full_text:
                matches.append(
                    {
                        "rule_type": "content_keywords",
                        "rule_value": keyword,
                        "category": rule_info["category"],
                        "priority": rule_info.get("priority", 1),
                    }
                )

        return matches

    def _check_file_size_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查文件大小规则"""
        matches = []
        file_size = document_data.get("metadata", {}).get("size", 0)

        for size_rule, rule_info in rules.items():
            # 解析大小规则（如 ">10MB", "<1MB"）
            if self._evaluate_size_rule(file_size, size_rule):
                matches.append(
                    {
                        "rule_type": "file_size",
                        "rule_value": size_rule,
                        "category": rule_info["category"],
                        "priority": rule_info.get("priority", 1),
                    }
                )

        return matches

    def _check_file_path_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查文件路径规则"""
        matches = []
        file_path = document_data.get("file_path", "")

        if file_path:
            file_path_lower = str(file_path).lower()
            for path_pattern, rule_info in rules.items():
                if path_pattern.lower() in file_path_lower:
                    matches.append(
                        {
                            "rule_type": "file_path",
                            "rule_value": path_pattern,
                            "category": rule_info["category"],
                            "priority": rule_info.get("priority", 1),
                        }
                    )

        return matches

    def _check_custom_rules(
        self, document_data: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查自定义规则"""
        matches = []

        for rule_name, rule_config in rules.items():
            try:
                # 自定义规则应该包含条件表达式和结果
                condition = rule_config.get("condition", "")
                if condition and self._evaluate_custom_condition(
                    condition, document_data
                ):
                    matches.append(
                        {
                            "rule_type": "custom",
                            "rule_value": rule_name,
                            "category": rule_config["category"],
                            "priority": rule_config.get("priority", 1),
                        }
                    )
            except Exception as e:
                self.logger.warning(f"自定义规则 {rule_name} 执行失败: {e}")

        return matches

    def _evaluate_size_rule(self, file_size: int, size_rule: str) -> bool:
        """评估文件大小规则"""
        try:
            # 解析大小规则
            if ">" in size_rule:
                threshold = self._parse_size_string(size_rule.split(">")[1])
                return file_size > threshold
            elif "<" in size_rule:
                threshold = self._parse_size_string(size_rule.split("<")[1])
                return file_size < threshold
            elif "=" in size_rule:
                threshold = self._parse_size_string(size_rule.split("=")[1])
                return file_size == threshold
            else:
                return False
        except:
            return False

    def _parse_size_string(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.strip().upper()
        if "KB" in size_str:
            return int(float(size_str.replace("KB", "")) * 1024)
        elif "MB" in size_str:
            return int(float(size_str.replace("MB", "")) * 1024 * 1024)
        elif "GB" in size_str:
            return int(float(size_str.replace("GB", "")) * 1024 * 1024 * 1024)
        else:
            return int(float(size_str))

    def _evaluate_custom_condition(
        self, condition: str, document_data: Dict[str, Any]
    ) -> bool:
        """评估自定义条件"""
        try:
            # 简单的条件评估，支持基本的逻辑运算
            # 这里可以实现更复杂的条件解析器

            # 示例：检查文件路径是否包含特定字符串
            if "path_contains" in condition:
                pattern = re.search(r'path_contains\("([^"]+)"\)', condition)
                if pattern:
                    search_term = pattern.group(1)
                    file_path = document_data.get("file_path", "")
                    return search_term.lower() in str(file_path).lower()

            # 示例：检查文件大小是否大于某个值
            elif "size_greater_than" in condition:
                pattern = re.search(r"size_greater_than\((\d+)\)", condition)
                if pattern:
                    threshold = int(pattern.group(1))
                    file_size = document_data.get("metadata", {}).get("size", 0)
                    return file_size > threshold

            return False

        except Exception as e:
            self.logger.warning(f"自定义条件评估失败: {e}")
            return False

    def add_rule(
        self, rule_type: str, rule_value: str, category: str, priority: int = 1
    ) -> bool:
        """添加新规则"""
        try:
            if rule_type not in self.rules:
                self.rules[rule_type] = {}

            self.rules[rule_type][rule_value] = {
                "category": category,
                "priority": priority,
            }

            self.logger.info(f"添加规则: {rule_type} -> {rule_value} -> {category}")
            return True

        except Exception as e:
            self.logger.error(f"添加规则失败: {e}")
            return False

    def remove_rule(self, rule_type: str, rule_value: str) -> bool:
        """删除规则"""
        try:
            if rule_type in self.rules and rule_value in self.rules[rule_type]:
                del self.rules[rule_type][rule_value]
                self.logger.info(f"删除规则: {rule_type} -> {rule_value}")
                return True
            else:
                self.logger.warning(f"规则不存在: {rule_type} -> {rule_value}")
                return False

        except Exception as e:
            self.logger.error(f"删除规则失败: {e}")
            return False

    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        summary = {
            "total_rules": 0,
            "rules_by_type": {},
            "enabled": self.enable_rules,
            "strict_mode": self.strict_mode,
        }

        for rule_type, rules in self.rules.items():
            summary["rules_by_type"][rule_type] = len(rules)
            summary["total_rules"] += len(rules)

        return summary

    def export_rules(self, export_path: str) -> bool:
        """导出规则配置"""
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                yaml.dump(self.rules, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"规则配置已导出到: {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出规则失败: {e}")
            return False

    def import_rules(self, import_path: str) -> bool:
        """导入规则配置"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                new_rules = yaml.safe_load(f)

            # 验证规则格式
            validated_rules = self._validate_rules(new_rules)

            # 更新规则
            self.rules.update(validated_rules)

            self.logger.info(f"成功导入 {len(validated_rules)} 条规则")
            return True

        except Exception as e:
            self.logger.error(f"导入规则失败: {e}")
            return False
