"""
规则引擎

用于实现用户自定义规则处理，为Stage 1提供基本功能
"""

import re
import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class RuleEngine:
    """规则引擎 - Stage 1基本实现"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 加载规则
        self.rules = self._load_rules()
        self.category_keywords = self._load_category_keywords()

        self.logger.info(f"规则引擎初始化完成，加载{len(self.rules)}条规则")

    def apply_rules(
        self, classification_result: Dict[str, Any], document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        应用规则处理分类结果

        Args:
            classification_result: LLM分类结果
            document_data: 文档数据

        Returns:
            Dict[str, Any]: 处理后的分类结果
        """
        try:
            self.logger.debug(f"应用规则处理: {document_data.get('file_path', '')}")

            # 复制原始结果
            result = classification_result.copy()
            applied_rules = []

            # 获取文档信息
            file_path = document_data.get("file_path", "")
            text_content = document_data.get("text_content", "")
            file_name = Path(file_path).name if file_path else ""

            # 应用文件名规则
            filename_rules = self._apply_filename_rules(file_name, result)
            applied_rules.extend(filename_rules)

            # 应用内容规则
            content_rules = self._apply_content_rules(text_content, result)
            applied_rules.extend(content_rules)

            # 应用关键词规则
            keyword_rules = self._apply_keyword_rules(text_content, result)
            applied_rules.extend(keyword_rules)

            # 应用置信度规则
            confidence_rules = self._apply_confidence_rules(result)
            applied_rules.extend(confidence_rules)

            # 记录应用的规则
            result["rules_applied"] = applied_rules
            result["rule_count"] = len(applied_rules)

            if applied_rules:
                self.logger.info(
                    f"应用了{len(applied_rules)}条规则: {[r['rule_id'] for r in applied_rules]}"
                )

            return result

        except Exception as e:
            self.logger.error(f"规则应用失败: {e}")
            # 返回原始结果
            classification_result["rules_applied"] = []
            classification_result["rule_error"] = str(e)
            return classification_result

    def _apply_filename_rules(
        self, filename: str, result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """应用文件名规则"""
        applied_rules = []

        # 预定义的文件名规则
        filename_rules = [
            {
                "id": "invoice_filename",
                "pattern": r"发票|invoice",
                "category": "财务",
                "confidence_boost": 0.2,
            },
            {
                "id": "contract_filename",
                "pattern": r"合同|contract",
                "category": "工作",
                "confidence_boost": 0.2,
            },
            {
                "id": "report_filename",
                "pattern": r"报告|report|汇报",
                "category": "工作",
                "confidence_boost": 0.15,
            },
            {
                "id": "personal_filename",
                "pattern": r"个人|private|personal",
                "category": "个人",
                "confidence_boost": 0.15,
            },
            {
                "id": "photo_filename",
                "pattern": r"照片|photo|image|img",
                "category": "个人",
                "confidence_boost": 0.1,
            },
            {
                "id": "resume_filename",
                "pattern": r"简历|resume|cv",
                "category": "个人",
                "confidence_boost": 0.2,
            },
        ]

        for rule in filename_rules:
            if re.search(rule["pattern"], filename, re.IGNORECASE):
                # 应用规则
                old_category = result.get("primary_category", "")
                old_confidence = result.get("confidence_score", 0.0)

                # 如果规则指定的类别与当前类别不同，且规则置信度足够高
                if rule["category"] != old_category:
                    new_confidence = min(1.0, old_confidence + rule["confidence_boost"])

                    # 如果提升后的置信度足够高，则修改分类
                    if new_confidence > old_confidence + 0.1:  # 至少提升0.1
                        result["primary_category"] = rule["category"]
                        result["confidence_score"] = new_confidence
                        result["reasoning"] = f"文件名匹配规则: {rule['pattern']}"

                        applied_rules.append(
                            {
                                "rule_id": rule["id"],
                                "rule_type": "filename",
                                "pattern": rule["pattern"],
                                "action": "category_change",
                                "old_category": old_category,
                                "new_category": rule["category"],
                                "confidence_change": rule["confidence_boost"],
                            }
                        )

        return applied_rules

    def _apply_content_rules(
        self, content: str, result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """应用内容规则"""
        applied_rules = []

        if not content:
            return applied_rules

        # 预定义的内容规则
        content_rules = [
            {
                "id": "financial_content",
                "pattern": r"(金额|费用|报销|账单|财务|税务)",
                "category": "财务",
                "confidence_boost": 0.15,
            },
            {
                "id": "work_content",
                "pattern": r"(项目|会议|工作|任务|计划|方案)",
                "category": "工作",
                "confidence_boost": 0.1,
            },
            {
                "id": "personal_content",
                "pattern": r"(个人|家庭|旅行|生活|日记)",
                "category": "个人",
                "confidence_boost": 0.1,
            },
            {
                "id": "confidential_content",
                "pattern": r"(机密|保密|confidential|secret)",
                "category": "重要",
                "confidence_boost": 0.2,
            },
        ]

        # 只检查前500个字符以提高性能
        content_sample = content[:500]

        for rule in content_rules:
            matches = re.findall(rule["pattern"], content_sample, re.IGNORECASE)
            if matches:
                match_count = len(matches)
                confidence_boost = rule["confidence_boost"] * min(
                    match_count / 3, 1.0
                )  # 最多3倍加成

                old_confidence = result.get("confidence_score", 0.0)
                new_confidence = min(1.0, old_confidence + confidence_boost)

                # 如果内容强烈表明某个类别，考虑修改分类
                if (
                    rule["category"] != result.get("primary_category")
                    and confidence_boost > 0.15
                ):
                    result["primary_category"] = rule["category"]
                    result["confidence_score"] = new_confidence
                    result["reasoning"] = (
                        f"内容匹配规则: {rule['pattern']} (匹配{match_count}次)"
                    )
                else:
                    result["confidence_score"] = new_confidence

                applied_rules.append(
                    {
                        "rule_id": rule["id"],
                        "rule_type": "content",
                        "pattern": rule["pattern"],
                        "match_count": match_count,
                        "confidence_boost": confidence_boost,
                    }
                )

        return applied_rules

    def _apply_keyword_rules(
        self, content: str, result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """应用关键词规则"""
        applied_rules = []

        if not content or not self.category_keywords:
            return applied_rules

        # 计算每个类别的关键词匹配分数
        category_scores = {}

        for category, keywords in self.category_keywords.items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword in content:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                category_scores[category] = {
                    "score": score,
                    "keywords": matched_keywords,
                }

        # 如果有匹配的关键词，应用规则
        if category_scores:
            # 找到最高分的类别
            best_category = max(
                category_scores.keys(), key=lambda x: category_scores[x]["score"]
            )
            best_score = category_scores[best_category]["score"]

            # 如果关键词分数足够高，考虑修改分类
            confidence_boost = min(0.2, best_score * 0.05)  # 每个关键词0.05分，最多0.2

            old_confidence = result.get("confidence_score", 0.0)
            new_confidence = min(1.0, old_confidence + confidence_boost)

            if (
                best_category != result.get("primary_category")
                and confidence_boost > 0.1
            ):
                result["primary_category"] = best_category
                result["confidence_score"] = new_confidence
                result["reasoning"] = (
                    f"关键词匹配: {', '.join(category_scores[best_category]['keywords'])}"
                )
            else:
                result["confidence_score"] = new_confidence

            applied_rules.append(
                {
                    "rule_id": "keyword_matching",
                    "rule_type": "keyword",
                    "category": best_category,
                    "matched_keywords": category_scores[best_category]["keywords"],
                    "keyword_score": best_score,
                    "confidence_boost": confidence_boost,
                }
            )

        return applied_rules

    def _apply_confidence_rules(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用置信度规则"""
        applied_rules = []

        confidence = result.get("confidence_score", 0.0)
        category = result.get("primary_category", "")

        # 置信度过低，标记需要审核
        review_threshold = self.config.get("classification", {}).get(
            "review_threshold", 0.6
        )

        if confidence < review_threshold:
            result["needs_review"] = True
            result["review_reason"] = (
                f"置信度过低: {confidence:.2f} < {review_threshold}"
            )

            applied_rules.append(
                {
                    "rule_id": "low_confidence_review",
                    "rule_type": "confidence",
                    "action": "mark_for_review",
                    "confidence": confidence,
                    "threshold": review_threshold,
                }
            )

        # 未分类的文档
        if category in ["其他", "Uncategorized", "unknown", ""]:
            result["needs_review"] = True
            result["review_reason"] = "未能确定具体类别"

            applied_rules.append(
                {
                    "rule_id": "uncategorized_review",
                    "rule_type": "category",
                    "action": "mark_for_review",
                    "category": category,
                }
            )

        return applied_rules

    def _load_rules(self) -> List[Dict[str, Any]]:
        """加载规则配置"""
        try:
            # 尝试从配置文件加载规则
            rules_file = self.config.get("rules", {}).get(
                "rules_file", "config/rules.yaml"
            )

            if Path(rules_file).exists():
                with open(rules_file, "r", encoding="utf-8") as f:
                    rules_config = yaml.safe_load(f)
                    return rules_config.get("rules", [])

        except Exception as e:
            self.logger.warning(f"加载规则文件失败: {e}")

        # 返回默认规则
        return []

    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """加载类别关键词"""
        # Stage 1 的基本关键词映射
        return {
            "工作": [
                "工作",
                "项目",
                "会议",
                "任务",
                "计划",
                "方案",
                "报告",
                "合同",
                "业务",
                "公司",
            ],
            "个人": [
                "个人",
                "家庭",
                "旅行",
                "生活",
                "日记",
                "照片",
                "朋友",
                "爱好",
                "娱乐",
                "购物",
            ],
            "财务": [
                "财务",
                "金额",
                "费用",
                "报销",
                "账单",
                "税务",
                "发票",
                "收据",
                "银行",
                "支付",
            ],
            "其他": ["其他", "杂项", "临时", "备份", "草稿", "测试"],
        }

    def get_rules_summary(self) -> Dict[str, Any]:
        """获取规则摘要"""
        return {
            "total_rules": len(self.rules),
            "category_keywords": {
                cat: len(keywords) for cat, keywords in self.category_keywords.items()
            },
            "rule_types": ["filename", "content", "keyword", "confidence"],
            "config_loaded": bool(self.rules),
        }
