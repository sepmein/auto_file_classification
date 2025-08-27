"""
增强分类器 - Step 2 多标签支持

支持多标签分类、置信度阈值、审核机制等高级功能
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

from .classifier import DocumentClassifier
from .llm_classifier import LLMClassifier
from .retrieval_agent import RetrievalAgent
from ..rules.enhanced_rule_engine import EnhancedRuleEngine


class EnhancedClassifier:
    """增强分类器 - 支持多标签分类和审核机制"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.base_classifier = DocumentClassifier(config)
        self.llm_classifier = LLMClassifier(config)
        self.retrieval_agent = RetrievalAgent(config)
        self.rule_engine = EnhancedRuleEngine(config)

        # 获取配置
        self.confidence_thresholds = config.get("classification", {}).get(
            "confidence_threshold", {}
        )
        self.taxonomies = config.get("classification", {}).get("taxonomies", {})
        self.tag_rules = config.get("classification", {}).get("tag_rules", {})

        self.logger.info("增强分类器初始化完成")

    def classify_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分类文档 - 支持多标签分类

        Args:
            document_data: 文档数据

        Returns:
            Dict[str, Any]: 分类结果，包含标签、置信度、审核状态等
        """
        try:
            self.logger.info(f"开始分类文档: {document_data.get('file_path', '')}")

            # 步骤1: 应用预分类规则
            pre_result = self.rule_engine.apply_pre_classification_rules(document_data)

            if pre_result.get("excluded"):
                return {
                    "status": "excluded",
                    "reason": "文件被规则排除",
                    "rule_applied": pre_result.get("applied_rules", []),
                    "needs_review": False,
                }

            # 步骤2: 基础分类（向量相似度 + LLM）
            base_classification = self._perform_base_classification(document_data)

            # 验证基础分类结果
            if not isinstance(base_classification, dict):
                self.logger.error(f"基础分类返回的不是字典: {base_classification}")
                return {
                    "tags": [],
                    "confidence_score": 0.0,
                    "reasoning": "基础分类失败",
                    "primary_tag": "",
                    "status": "error",
                    "needs_review": True,
                    "review_reason": "基础分类结果格式错误",
                }

            # 步骤3: 应用后分类规则
            final_result = self.rule_engine.apply_post_classification_rules(
                base_classification, document_data, pre_result
            )

            # 验证后分类结果
            if not isinstance(final_result, dict):
                self.logger.error(f"后分类规则返回的不是字典: {final_result}")
                final_result = base_classification.copy()  # 使用基础分类结果

            # 步骤4: 确定分类状态和审核需求
            classification_status = self._determine_classification_status(final_result)
            final_result.update(classification_status)

            # 步骤5: 记录分类过程
            final_result["classification_process"] = {
                "pre_classification": pre_result,
                "base_classification": base_classification,
                "rule_engine": "enhanced",
            }

            self.logger.info(
                f"文档分类完成: {final_result.get('primary_tag', '未知')} "
                f"(置信度: {final_result.get('confidence_score', 0):.2f})"
            )

            return final_result

        except Exception as e:
            self.logger.error(f"文档分类失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "needs_review": True,
                "tags": [],
                "primary_tag": "分类失败",
            }

    def _perform_base_classification(
        self, document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行基础分类（向量相似度 + LLM）"""
        try:
            # 获取向量嵌入（来自文档数据）
            embedding = document_data.get("embedding")
            if not embedding:
                self.logger.warning("文档缺少嵌入向量，使用基础分类器")
                return self.base_classifier.classify_document(document_data)

            # 查找相似文档
            similar_docs = self.retrieval_agent.search_similar_documents(
                embedding, top_k=5
            )

            # 使用LLM进行分类
            llm_result = self._classify_with_llm(document_data, similar_docs)

            # 合并结果
            result = {
                "tags": llm_result.get("tags", []),
                "confidence_score": llm_result.get("confidence_score", 0.0),
                "reasoning": llm_result.get("reasoning", ""),
                "similar_documents": similar_docs,
                "embedding_used": True,
            }

            return result

        except Exception as e:
            self.logger.error(f"基础分类失败: {e}")
            # 回退到基础分类器
            return self.base_classifier.classify_document(document_data)

    def _classify_with_llm(
        self, document_data: Dict[str, Any], similar_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """使用LLM进行分类"""
        try:
            # 构建提示词
            prompt = self._build_classification_prompt(document_data, similar_docs)

            # 调用LLM
            llm_response = self.llm_classifier.classify_with_prompt(prompt)

            # 解析响应
            parsed_result = self._parse_llm_response(llm_response)

            return parsed_result

        except Exception as e:
            self.logger.error(f"LLM分类失败: {e}")
            return {
                "tags": [],
                "confidence_score": 0.0,
                "reasoning": f"LLM分类失败: {e}",
            }

    def _build_classification_prompt(
        self, document_data: Dict[str, Any], similar_docs: List[Dict[str, Any]]
    ) -> str:
        """构建分类提示词"""
        # 获取所有可用的标签
        all_tags = []
        for taxonomy_name, tags in self.taxonomies.items():
            all_tags.extend([f"{taxonomy_name}: {', '.join(tags)}"])

        # 构建相似文档信息
        similar_docs_info = ""
        if similar_docs:
            similar_docs_info = "\n\n相似文档示例:\n"
            for i, doc in enumerate(similar_docs[:3], 1):
                similar_docs_info += (
                    f"{i}. {doc.get('filename', '未知')} -> {doc.get('tags', [])}\n"
                )

        prompt = f"""你是一个专业的文档分类助手。请根据文档内容将其分类到合适的标签中。

可用标签体系:
{chr(10).join(all_tags)}

文档信息:
- 文件名: {Path(document_data.get('file_path', '')).name}
- 内容摘要: {document_data.get('text_content', '')[:500]}...
- 文件大小: {document_data.get('file_size', '未知')}
{similar_docs_info}

请分析文档内容并给出:
1. 主要标签列表（最多5个）
2. 每个标签的置信度（0.0-1.0）
3. 分类理由

请以JSON格式返回，格式如下:
{{
    "tags": ["标签1", "标签2"],
    "confidence_scores": [0.9, 0.7],
    "reasoning": "分类理由",
    "primary_tag": "主要标签"
}}

只返回JSON，不要其他内容。"""

        return prompt

    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            if "{" in llm_response and "}" in llm_response:
                start = llm_response.find("{")
                end = llm_response.rfind("}") + 1
                json_str = llm_response[start:end]

                parsed = json.loads(json_str)

                # 验证和标准化结果
                result = {
                    "tags": parsed.get("tags", []),
                    "confidence_scores": parsed.get("confidence_scores", []),
                    "reasoning": parsed.get("reasoning", ""),
                    "primary_tag": parsed.get("primary_tag", ""),
                }

                # 计算平均置信度
                if result["confidence_scores"]:
                    result["confidence_score"] = sum(result["confidence_scores"]) / len(
                        result["confidence_scores"]
                    )
                else:
                    result["confidence_score"] = 0.0

                return result

        except Exception as e:
            self.logger.warning(f"LLM响应解析失败: {e}")

        # 解析失败时的默认返回
        return {
            "tags": [],
            "confidence_score": 0.0,
            "reasoning": "响应解析失败",
            "primary_tag": "",
        }

    def _determine_classification_status(
        self, classification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """确定分类状态和审核需求"""
        try:
            # 确保 classification_result 是字典
            if not isinstance(classification_result, dict):
                self.logger.error(f"分类结果不是字典: {classification_result}")
                return {
                    "status": "error",
                    "needs_review": True,
                    "review_reason": "分类结果格式错误",
                }

            confidence = classification_result.get("confidence_score", 0.0)
            auto_threshold = self.confidence_thresholds.get("auto", 0.85)
            review_threshold = self.confidence_thresholds.get("review", 0.6)

            # 确定状态
            if confidence >= auto_threshold:
                status = "auto_classified"
                needs_review = False
                review_reason = None
            elif confidence >= review_threshold:
                status = "needs_review"
                needs_review = True
                review_reason = "置信度不足，需要人工审核"
            else:
                status = "uncertain"
                needs_review = True
                review_reason = "置信度过低，无法确定分类"

            # 检查是否有特殊标签需要审核
            tags = classification_result.get("tags", [])
            if "机密" in tags or "内部" in tags:
                needs_review = True
                review_reason = "包含敏感标签，需要人工审核"
                status = "needs_review"

            return {
                "status": status,
                "needs_review": needs_review,
                "review_reason": review_reason,
                "confidence_level": self._get_confidence_level(confidence),
            }

        except Exception as e:
            self.logger.error(f"分类状态确定失败: {e}")
            return {
                "status": "error",
                "needs_review": True,
                "review_reason": f"状态确定失败: {e}",
                "confidence_level": "unknown",
            }

    def _get_confidence_level(self, confidence: float) -> str:
        """获取置信度等级"""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.8:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        elif confidence >= 0.6:
            return "low"
        else:
            return "very_low"

    def get_classification_summary(self) -> Dict[str, Any]:
        """获取分类摘要"""
        return {
            "taxonomies": self.taxonomies,
            "confidence_thresholds": self.confidence_thresholds,
            "tag_rules": self.tag_rules,
            "components": {
                "base_classifier": "DocumentClassifier",
                "llm_classifier": "LLMClassifier",
                "retrieval_agent": "RetrievalAgent",
                "rule_engine": "EnhancedRuleEngine",
            },
        }

    def validate_classification_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证分类结果"""
        validation = {"is_valid": True, "errors": [], "warnings": []}

        # 检查必要字段
        required_fields = ["tags", "primary_tag", "confidence_score"]
        for field in required_fields:
            if field not in result:
                validation["is_valid"] = False
                validation["errors"].append(f"缺少必要字段: {field}")

        # 检查标签有效性
        if "tags" in result:
            tags = result["tags"]
            if not isinstance(tags, list):
                validation["is_valid"] = False
                validation["errors"].append("标签必须是列表")
            else:
                # 检查标签是否在预定义体系中
                all_valid_tags = []
                for taxonomy_tags in self.taxonomies.values():
                    all_valid_tags.extend(taxonomy_tags)

                invalid_tags = [tag for tag in tags if tag not in all_valid_tags]
                if invalid_tags:
                    validation["warnings"].append(f"发现未定义的标签: {invalid_tags}")

        # 检查置信度范围
        if "confidence_score" in result:
            confidence = result["confidence_score"]
            if (
                not isinstance(confidence, (int, float))
                or confidence < 0
                or confidence > 1
            ):
                validation["is_valid"] = False
                validation["errors"].append("置信度必须在0-1之间")

        return validation
