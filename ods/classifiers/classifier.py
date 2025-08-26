"""
文档分类器主模块
整合检索代理、LLM分类器和规则检查器
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .retrieval_agent import RetrievalAgent
from .llm_classifier import LLMClassifier
from .rule_checker import RuleChecker


class DocumentClassifier:
    """文档分类器 - 整合所有分类组件"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 分类配置
        self.classification_config = config.get("classification", {})
        self.categories = self.classification_config.get(
            "categories", ["工作", "个人", "财务", "其他"]
        )
        self.confidence_threshold = self.classification_config.get(
            "confidence_threshold", 0.8
        )
        self.review_threshold = self.classification_config.get("review_threshold", 0.6)
        self.max_tags = self.classification_config.get("max_tags", 3)

        # 初始化组件
        self.retrieval_agent = RetrievalAgent(config)
        self.llm_classifier = LLMClassifier(config)
        self.rule_checker = RuleChecker(config)

        self.logger.info("文档分类器初始化完成")

    def classify_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """分类文档的主要方法"""
        try:
            start_time = time.time()
            file_path = document_data.get("file_path", "")

            self.logger.info(f"开始分类文档: {file_path}")

            # 1. LLM分类
            llm_result = self.llm_classifier.classify_document(document_data)

            # 2. 规则检查和应用
            final_result = self.rule_checker.apply_rules(llm_result, document_data)

            # 3. 添加分类元数据
            final_result["classification_method"] = "llm_with_rules"
            final_result["total_processing_time"] = time.time() - start_time
            final_result["file_path"] = file_path

            # 4. 如果分类成功，添加到向量数据库
            if (
                final_result.get("primary_category")
                and final_result.get("primary_category") != "Uncategorized"
            ):
                self._add_to_vector_database(document_data, final_result)

            self.logger.info(
                f"文档分类完成: {file_path} -> {final_result.get('primary_category')}"
            )
            return final_result

        except Exception as e:
            self.logger.error(f"文档分类失败: {e}")
            return self._create_error_result(str(e), document_data)

    def _add_to_vector_database(
        self, document_data: Dict[str, Any], classification_result: Dict[str, Any]
    ) -> bool:
        """将分类后的文档添加到向量数据库"""
        try:
            # 准备元数据
            metadata = {
                "category": classification_result["primary_category"],
                "secondary_categories": classification_result.get(
                    "secondary_categories", []
                ),
                "confidence_score": classification_result.get("confidence_score", 0.0),
                "needs_review": classification_result.get("needs_review", False),
                "classification_timestamp": classification_result.get(
                    "classification_timestamp", time.time()
                ),
                "file_path": document_data.get("file_path", ""),
                "file_size": document_data.get("metadata", {}).get("size", 0),
                "file_type": Path(document_data.get("file_path", "")).suffix.lower(),
            }

            # 获取嵌入向量
            embedding = document_data.get("embedding")
            if embedding is None:
                self.logger.warning("文档没有嵌入向量，跳过向量数据库添加")
                return False

            # 获取文本摘要
            text_chunk = document_data.get("summary", "")[:1000]  # 限制长度

            # 生成文档ID
            doc_id = (
                f"{int(time.time())}_{Path(document_data.get('file_path', '')).stem}"
            )

            # 添加到向量数据库
            success = self.retrieval_agent.add_document(
                doc_id=doc_id,
                embedding=embedding,
                metadata=metadata,
                text_chunk=text_chunk,
            )

            if success:
                self.logger.info(f"文档已添加到向量数据库: {doc_id}")
            else:
                self.logger.warning(f"文档添加到向量数据库失败: {doc_id}")

            return success

        except Exception as e:
            self.logger.error(f"添加文档到向量数据库失败: {e}")
            return False

    def batch_classify(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量分类文档"""
        results = []

        for i, document in enumerate(documents):
            try:
                self.logger.info(
                    f"处理文档 {i+1}/{len(documents)}: {document.get('file_path', '')}"
                )
                result = self.classify_document(document)
                results.append(result)

                # 添加进度信息
                result["batch_index"] = i
                result["batch_total"] = len(documents)

            except Exception as e:
                self.logger.error(f"批量分类文档失败: {e}")
                error_result = self._create_error_result(str(e), document)
                error_result["batch_index"] = i
                error_result["batch_total"] = len(documents)
                results.append(error_result)

        return results

    def get_classification_statistics(self) -> Dict[str, Any]:
        """获取分类统计信息"""
        try:
            # 获取向量数据库统计
            vector_stats = self.retrieval_agent.get_collection_stats()

            # 获取规则统计
            rules_summary = self.rule_checker.get_rules_summary()

            # 统计分类结果
            stats = {
                "vector_database": vector_stats,
                "rules": rules_summary,
                "categories": self.categories,
                "confidence_threshold": self.confidence_threshold,
                "review_threshold": self.review_threshold,
                "max_tags": self.max_tags,
            }

            return stats

        except Exception as e:
            self.logger.error(f"获取分类统计失败: {e}")
            return {}

    def update_document_classification(
        self, doc_id: str, new_classification: Dict[str, Any]
    ) -> bool:
        """更新文档分类"""
        try:
            # 更新向量数据库中的元数据
            success = self.retrieval_agent.update_document(
                doc_id=doc_id,
                new_metadata={
                    "category": new_classification.get("primary_category"),
                    "secondary_categories": new_classification.get(
                        "secondary_categories", []
                    ),
                    "confidence_score": new_classification.get("confidence_score", 0.0),
                    "needs_review": new_classification.get("needs_review", False),
                    "last_updated": time.time(),
                },
            )

            if success:
                self.logger.info(f"文档分类已更新: {doc_id}")
            else:
                self.logger.warning(f"文档分类更新失败: {doc_id}")

            return success

        except Exception as e:
            self.logger.error(f"更新文档分类失败: {e}")
            return False

    def search_similar_documents(
        self, query_embedding, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            return self.retrieval_agent.search_similar_documents(query_embedding, top_k)
        except Exception as e:
            self.logger.error(f"搜索相似文档失败: {e}")
            return []

    def get_category_examples(
        self, category: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """获取类别示例"""
        try:
            return self.retrieval_agent.get_category_examples(category, top_k)
        except Exception as e:
            self.logger.error(f"获取类别示例失败: {e}")
            return []

    def test_all_components(self) -> Dict[str, bool]:
        """测试所有组件"""
        test_results = {}

        try:
            # 测试向量数据库
            vector_stats = self.retrieval_agent.get_collection_stats()
            test_results["vector_database"] = bool(vector_stats)

            # 测试LLM分类器
            test_results["llm_classifier"] = self.llm_classifier.test_connection()

            # 测试规则检查器
            rules_summary = self.rule_checker.get_rules_summary()
            test_results["rule_checker"] = bool(rules_summary)

            self.logger.info("组件测试完成")

        except Exception as e:
            self.logger.error(f"组件测试失败: {e}")
            test_results["error"] = str(e)

        return test_results

    def _create_error_result(
        self, error_message: str, document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "primary_category": "Error",
            "secondary_categories": [],
            "confidence_score": 0.0,
            "reasoning": f"分类过程中出现错误: {error_message}",
            "needs_review": True,
            "suggested_tags": ["ERROR"],
            "similar_documents_count": 0,
            "classification_timestamp": time.time(),
            "model_used": "none",
            "provider": "none",
            "file_path": document_data.get("file_path", ""),
            "classification_method": "error",
            "total_processing_time": 0.0,
        }

    def export_classification_data(self, export_path: str) -> bool:
        """导出分类数据"""
        try:
            return self.retrieval_agent.export_collection(export_path)
        except Exception as e:
            self.logger.error(f"导出分类数据失败: {e}")
            return False

    def reset_classification_database(self) -> bool:
        """重置分类数据库"""
        try:
            return self.retrieval_agent.reset_collection()
        except Exception as e:
            self.logger.error(f"重置分类数据库失败: {e}")
            return False
