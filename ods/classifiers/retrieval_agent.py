"""
检索代理模块
负责与Chroma向量数据库交互，检索相似文档
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
import json
import time

from ..embeddings.embedder import Embedder


class RetrievalAgent:
    """检索代理 - 负责向量检索和相似文档查找"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 向量数据库配置
        self.vector_db_path = config.get("database", {}).get(
            "vector_db_path", ".ods/vector_db"
        )
        self.collection_name = config.get("collection_name", "documents")
        self.top_k = config.get("top_k", 5)
        self.similarity_threshold = config.get("similarity_threshold", 0.7)

        # 初始化ChromaDB
        self.client = None
        self.collection = None
        self._setup_vector_db()

        # 嵌入模型（用于查询向量化）
        self.embedder = Embedder(config)

    def _setup_vector_db(self):
        """设置向量数据库"""
        try:
            # 确保目录存在
            Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)

            # 连接ChromaDB
            self.client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True),
            )

            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(self.collection_name)
                self.logger.info(f"连接到现有集合: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "文档分类向量数据库"},
                )
                self.logger.info(f"创建新集合: {self.collection_name}")

        except Exception as e:
            self.logger.error(f"向量数据库设置失败: {e}")
            raise

    def add_document(
        self,
        doc_id: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any],
        text_chunk: str = "",
    ) -> bool:
        """添加文档到向量数据库"""
        try:
            # 准备元数据
            doc_metadata = {
                "doc_id": doc_id,
                "timestamp": time.time(),
                "text_chunk": text_chunk[:1000],  # 限制长度
                **self._sanitize_metadata(metadata),
            }
            
            emb = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            self.collection.add(
                embeddings=[emb],
                metadatas=[doc_metadata],
                ids=[doc_id]
            )

            self.logger.info(f"文档 {doc_id} 已添加到向量数据库")
            return True

        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            return False

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """清理元数据，确保所有值都是ChromaDB兼容的类型"""
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            elif isinstance(value, list):
                # 将列表转换为字符串
                sanitized[key] = str(value)
            elif isinstance(value, dict):
                # 将字典转换为字符串
                sanitized[key] = str(value)
            else:
                # 其他类型转换为字符串
                sanitized[key] = str(value)
        return sanitized

    def search_similar_documents(
        self,
        query_embedding: np.ndarray,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            if top_k is None:
                top_k = self.top_k

            # 执行向量搜索
            # 确保query_embedding是列表格式
            if isinstance(query_embedding, list):
                query_embedding_list = query_embedding
            elif hasattr(query_embedding, "tolist"):
                query_embedding_list = query_embedding.tolist()
            else:
                query_embedding_list = list(query_embedding)

            results = self.collection.query(
                query_embeddings=[query_embedding_list],
                n_results=top_k,
                where=filter_metadata,
                include=["metadatas", "distances", "documents"],
            )

            # 处理结果
            similar_docs = []
            ids = results.get('ids', [])
            metadatas = results.get('metadatas', [])
            distances = results.get('distances', [])
            if ids and ids[0]:
                metadata_container = metadatas[0] if metadatas else []
                for i in range(len(ids[0])):
                    # 兼容Chroma不同版本返回的结构：可能是列表也可能是字典
                    if isinstance(metadata_container, dict):
                        metadata = metadata_container.get(ids[0][i], {})
                    else:
                        metadata = metadata_container[i]
                    distance = distances[0][i] if distances and distances[0] else 0
                    doc_info = {
                        'doc_id': ids[0][i],
                        'metadata': metadata,
                        'distance': distance,
                        'similarity_score': 1 - distance,
                        'text_chunk': metadata.get('text_chunk', '')
                    }

                    # 过滤低相似度结果
                    if doc_info["similarity_score"] >= self.similarity_threshold:
                        similar_docs.append(doc_info)

            self.logger.info(f"找到 {len(similar_docs)} 个相似文档")
            return similar_docs

        except Exception as e:
            self.logger.error(f"搜索相似文档失败: {e}")
            return []

    def get_category_examples(
        self, category: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """获取特定类别的示例文档"""
        try:
            # 按类别过滤
            filter_metadata = {"category": category}

            # 获取该类别的所有文档
            results = self.collection.get(where=filter_metadata, limit=top_k)

            examples = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    example = {
                        "doc_id": results["ids"][i],
                        "metadata": results["metadatas"][i],
                        "text_chunk": results["metadatas"][i].get("text_chunk", ""),
                    }
                    examples.append(example)

            self.logger.info(f"类别 {category} 找到 {len(examples)} 个示例")
            return examples

        except Exception as e:
            self.logger.error(f"获取类别示例失败: {e}")
            return []

    def get_all_categories(self) -> List[str]:
        """获取所有已存在的类别"""
        try:
            # 获取所有文档的元数据
            results = self.collection.get(limit=10000)  # 假设文档数量不超过10000

            categories = set()
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    if "category" in metadata:
                        categories.add(metadata["category"])

            return list(categories)

        except Exception as e:
            self.logger.error(f"获取所有类别失败: {e}")
            return []

    def update_document(self, doc_id: str, new_metadata: Dict[str, Any]) -> bool:
        """更新文档元数据"""
        try:
            # 获取现有文档
            results = self.collection.get(ids=[doc_id])
            if not results["ids"]:
                self.logger.warning(f"文档 {doc_id} 不存在")
                return False

            # 更新元数据
            updated_metadata = {**results["metadatas"][0], **new_metadata}

            # 删除旧文档
            self.collection.delete(ids=[doc_id])

            # 重新添加（保持相同的embedding）
            self.collection.add(
                embeddings=results["embeddings"],
                metadatas=[updated_metadata],
                ids=[doc_id],
            )

            self.logger.info(f"文档 {doc_id} 元数据已更新")
            return True

        except Exception as e:
            self.logger.error(f"更新文档失败: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            self.collection.delete(ids=[doc_id])
            self.logger.info(f"文档 {doc_id} 已删除")
            return True

        except Exception as e:
            self.logger.error(f"删除文档失败: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            count = self.collection.count()
            categories = self.get_all_categories()

            stats = {
                "total_documents": count,
                "categories_count": len(categories),
                "categories": categories,
                "collection_name": self.collection_name,
                "vector_db_path": self.vector_db_path,
            }

            return stats

        except Exception as e:
            self.logger.error(f"获取集合统计失败: {e}")
            return {}

    def reset_collection(self) -> bool:
        """重置集合"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "文档分类向量数据库"},
            )
            self.logger.info(f"集合 {self.collection_name} 已重置")
            return True

        except Exception as e:
            self.logger.error(f"重置集合失败: {e}")
            return False

    def export_collection(self, export_path: str) -> bool:
        """导出集合数据"""
        try:
            # 获取所有数据
            results = self.collection.get(limit=10000)

            export_data = {
                "collection_name": self.collection_name,
                "export_timestamp": time.time(),
                "documents": [],
            }

            if results["ids"]:
                for i in range(len(results["ids"])):
                    doc_data = {
                        "id": results["ids"][i],
                        "metadata": results["metadatas"][i],
                        "embedding": (
                            results["embeddings"][i].tolist()
                            if results["embeddings"]
                            else None
                        ),
                    }
                    export_data["documents"].append(doc_data)

            # 保存到文件
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"集合数据已导出到: {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出集合失败: {e}")
            return False
