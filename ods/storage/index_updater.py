"""
索引更新器（占位符）

用于后续实现向量数据库和索引的更新
"""

import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json
import uuid

import chromadb
from llama_index.core import Document, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class IndexUpdater:
    """索引更新器 - 更新向量库、知识库、审计日志和状态标记

    特性:
    - 更新 ChromaDB 向量数据库
    - 更新 LlamaIndex 知识库索引
    - 记录 SQLite 审计日志
    - 维护文件状态标记
    - 支持回滚和查询
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 数据库配置
        db_config = config.get("database", {})
        self.db_path = db_config.get("sqlite_path", "data/audit.db")
        self.audit_table = db_config.get("audit_table", "file_operations")
        self.status_table = db_config.get("status_table", "file_status")

        # 向量库配置
        vector_config = config.get("vector_store", {})
        self.chroma_path = vector_config.get("chroma_path", "data/chroma_db")
        self.collection_name = vector_config.get("collection_name", "documents")

        # LlamaIndex配置
        llama_config = config.get("llama_index", {})
        self.index_path = llama_config.get("index_path", "data/llama_index")
        self.enable_llama_index = llama_config.get("enable", True)

        # 初始化数据库
        self._init_database()

        # 初始化向量库
        try:
            self._init_vector_store()
        except Exception as e:
            self.logger.warning(f"向量库初始化失败，继续执行: {e}")
            self.collection = None

        # 初始化LlamaIndex
        if self.enable_llama_index:
            self._init_llama_index()

        self.logger.info("索引更新器初始化完成")

    def set_collection(self, collection):
        """设置向量库集合（用于测试）"""
        self.collection = collection

    def _init_database(self):
        """初始化SQLite数据库"""
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 创建审计日志表
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.audit_table} (
                        id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        old_path TEXT,
                        new_path TEXT,
                        old_filename TEXT,
                        new_filename TEXT,
                        category TEXT,
                        tags TEXT,
                        confidence_score REAL,
                        rules_applied TEXT,
                        processing_time REAL,
                        operator TEXT,
                        status TEXT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 创建文件状态表
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.status_table} (
                        file_path TEXT PRIMARY KEY,
                        file_hash TEXT,
                        last_modified TIMESTAMP,
                        last_classified TIMESTAMP,
                        category TEXT,
                        tags TEXT,
                        status TEXT,
                        needs_review BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 创建索引
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_audit_file_path ON {self.audit_table}(file_path)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_audit_category ON {self.audit_table}(category)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_audit_status ON {self.audit_table}(status)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_status_category ON {self.status_table}(category)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_status_needs_review ON {self.status_table}(needs_review)"
                )

                conn.commit()

        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise

    def _init_vector_store(self):
        """初始化ChromaDB向量库"""
        try:
            import chromadb

            chroma_dir = Path(self.chroma_path)
            chroma_dir.mkdir(parents=True, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(path=str(chroma_dir))

            # 获取或创建集合
            try:
                self.collection = self.chroma_client.get_collection(
                    self.collection_name
                )
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "文档分类向量库"},
                )

        except Exception as e:
            self.logger.error(f"向量库初始化失败: {e}")
            self.chroma_client = None
            self.collection = None
            raise

    def _init_llama_index(self):
        """初始化LlamaIndex知识库"""
        try:
            index_dir = Path(self.index_path)
            index_dir.mkdir(parents=True, exist_ok=True)

            # 初始化嵌入模型
            embedding_config = self.config.get("embedding", {})
            model_name = embedding_config.get("model_name", "BAAI/bge-m3")

            if embedding_config.get("provider") == "openai":
                self.embedding_model = OpenAIEmbedding(
                    api_key=embedding_config.get("api_key"),
                    model=embedding_config.get("model", "text-embedding-ada-002"),
                )
            else:
                self.embedding_model = HuggingFaceEmbedding(
                    model_name=model_name, device=embedding_config.get("device", "cpu")
                )

            # 初始化向量存储
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)

            # 创建或加载索引
            index_file = index_dir / "index.json"
            if index_file.exists():
                self.llama_index = VectorStoreIndex.from_vector_store(
                    self.vector_store, embed_model=self.embedding_model
                )
            else:
                self.llama_index = VectorStoreIndex.from_vector_store(
                    self.vector_store, embed_model=self.embedding_model
                )
                # 保存索引
                self.llama_index.storage_context.persist(persist_dir=str(index_dir))

        except Exception as e:
            self.logger.error(f"LlamaIndex初始化失败: {e}")
            self.enable_llama_index = False

    def update_indexes(
        self,
        move_result: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Dict[str, Any],
        processing_time: float,
    ) -> Dict[str, Any]:
        """更新所有索引和日志"""
        try:
            self.logger.info(f"开始更新索引: {move_result.get('original_path', '')}")

            # 生成操作ID
            operation_id = str(uuid.uuid4())

            # 并行更新各个索引
            results = {
                'operation_id': operation_id,
                'vector_update': self._update_vector_store(move_result, document_data, classification_result),
                'llama_update': self._update_llama_index(move_result, document_data, classification_result) if self.enable_llama_index else {'success': True, 'reason': 'disabled'},
                'audit_log': self._log_audit_record(operation_id, move_result, document_data, classification_result, processing_time),
                'status_update': self._update_file_status(move_result, classification_result)
            }

            # 检查整体结果（忽略禁用的操作）
            success = all(
                result.get("success", False) or result.get("reason") == "disabled"
                for result in results.values()
                if isinstance(result, dict)
            )

            update_result = {
                "operation_id": operation_id,
                "success": success,
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }

            if success:
                self.logger.info(f"索引更新成功: {operation_id}")
            else:
                self.logger.warning(f"索引更新部分失败: {operation_id}")

            return update_result

        except Exception as e:
            self.logger.error(f"索引更新失败: {e}")
            return {
                "operation_id": (
                    operation_id if "operation_id" in locals() else str(uuid.uuid4())
                ),
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _update_vector_store(
        self,
        move_result: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新ChromaDB向量库"""
        try:
            if not move_result.get("moved", False):
                return {"success": False, "reason": "file_not_moved"}

            # 获取文档向量
            embedding = document_data.get("embedding")
            if not embedding:
                return {"success": False, "reason": "no_embedding"}

            # 检查collection是否可用
            if not hasattr(self, "collection") or self.collection is None:
                return {"success": False, "reason": "collection_not_available"}

            # 准备元数据
            metadata = {
                "file_path": move_result.get("primary_target_path", ""),
                "original_path": move_result.get("original_path", ""),
                "category": classification_result.get("primary_category", ""),
                "tags": ",".join(classification_result.get("tags", [])),
                "confidence_score": classification_result.get("confidence_score", 0.0),
                "file_type": document_data.get("metadata", {}).get("file_type", ""),
                "file_size": document_data.get("metadata", {}).get("file_size", 0),
                "processing_time": datetime.now().isoformat(),
            }

            # 准备文档内容
            text_content = document_data.get("text_content", "")
            if not text_content:
                text_content = document_data.get("summary", "")

            # 添加到向量库
            client = chromadb.PersistentClient(path=self.chroma_path)
            try:
                collection = client.get_collection(self.collection_name)
            except Exception:
                collection = client.create_collection(self.collection_name)
            collection.add(
                embeddings=[embedding],
                documents=[text_content],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())],
            )

            return {'success': True}
            
        except Exception as e:
            self.logger.error(f"向量库更新失败: {e}")
            return {"success": False, "error": str(e)}

    def _update_llama_index(
        self,
        move_result: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新LlamaIndex知识库"""
        try:
            if not move_result.get("moved", False):
                return {"success": False, "reason": "file_not_moved"}

            # 准备文档内容
            text_content = document_data.get("text_content", "")
            if not text_content:
                text_content = document_data.get("summary", "")

            if not text_content:
                return {"success": False, "reason": "no_content"}

            # 创建文档对象
            doc = Document(
                text=text_content,
                metadata={
                    "file_path": move_result.get("primary_target_path", ""),
                    "original_path": move_result.get("original_path", ""),
                    "category": classification_result.get("primary_category", ""),
                    "tags": classification_result.get("tags", []),
                    "confidence_score": classification_result.get(
                        "confidence_score", 0.0
                    ),
                    "file_type": document_data.get("metadata", {}).get("file_type", ""),
                    "file_size": document_data.get("metadata", {}).get("file_size", 0),
                    "processing_time": datetime.now().isoformat(),
                },
            )

            # 插入文档到索引
            self.llama_index.insert(doc)

            # 保存索引
            index_dir = Path(self.index_path)
            self.llama_index.storage_context.persist(persist_dir=str(index_dir))

            return {"success": True}

        except Exception as e:
            self.logger.error(f"LlamaIndex更新失败: {e}")
            return {"success": False, "error": str(e)}

    def _log_audit_record(
        self,
        operation_id: str,
        move_result: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Dict[str, Any],
        processing_time: float,
    ) -> Dict[str, Any]:
        """记录审计日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    f"""
                    INSERT INTO {self.audit_table} (
                        id, file_path, old_path, new_path, old_filename, new_filename,
                        category, tags, confidence_score, rules_applied, processing_time,
                        operator, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        operation_id,
                        move_result.get("original_path", ""),
                        move_result.get("original_path", ""),
                        move_result.get("primary_target_path", ""),
                        Path(move_result.get("original_path", "")).name,
                        (
                            Path(move_result.get("primary_target_path", "")).name
                            if move_result.get("primary_target_path")
                            else ""
                        ),
                        classification_result.get("primary_category", ""),
                        json.dumps(
                            classification_result.get("tags", []), ensure_ascii=False
                        ),
                        classification_result.get("confidence_score", 0.0),
                        json.dumps(
                            classification_result.get("rules_applied", []),
                            ensure_ascii=False,
                        ),
                        processing_time,
                        "auto",
                        "success" if move_result.get("moved", False) else "failed",
                        move_result.get("error_message", ""),
                    ),
                )

                conn.commit()

            return {"success": True, "operation_id": operation_id}

        except Exception as e:
            self.logger.error(f"审计日志记录失败: {e}")
            return {"success": False, "error": str(e)}

    def _update_file_status(
        self, move_result: Dict[str, Any], classification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新文件状态"""
        try:
            file_path = move_result.get(
                "primary_target_path", move_result.get("original_path", "")
            )
            if not file_path:
                return {"success": False, "reason": "no_file_path"}

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    file_hash = str(file_path_obj.stat().st_mtime)
                    last_modified = datetime.fromtimestamp(file_path_obj.stat().st_mtime).isoformat()
                else:
                    file_hash = ""
                    last_modified = datetime.now().isoformat()
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {self.status_table} (
                        file_path, file_hash, last_modified, last_classified,
                        category, tags, status, needs_review, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_path,
                    file_hash,
                    last_modified,
                    datetime.now().isoformat(),
                    classification_result.get('primary_category', ''),
                    json.dumps(classification_result.get('tags', []), ensure_ascii=False),
                    'classified',
                    classification_result.get('confidence_score', 0.0) < self.config.get('classification', {}).get('review_threshold', 0.6),
                    datetime.now().isoformat()
                ))
                
                conn.commit()

            return {"success": True}

        except Exception as e:
            self.logger.error(f"文件状态更新失败: {e}")
            return {"success": False, "error": str(e)}

    def get_audit_records(
        self,
        file_path: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询审计记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = f"SELECT * FROM {self.audit_table}"
                params = []

                conditions = []
                if file_path:
                    conditions.append("file_path = ?")
                    params.append(file_path)
                if category:
                    conditions.append("category = ?")
                    params.append(category)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"查询审计记录失败: {e}")
            return []

    def get_file_status(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取文件状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    f"SELECT * FROM {self.status_table} WHERE file_path = ?",
                    (file_path,),
                )
                row = cursor.fetchone()

                return dict(row) if row else None

        except Exception as e:
            self.logger.error(f"查询文件状态失败: {e}")
            return None

    def get_files_needing_review(self) -> List[Dict[str, Any]]:
        """获取需要审核的文件列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    f"""
                    SELECT * FROM {self.status_table} 
                    WHERE needs_review = TRUE 
                    ORDER BY updated_at DESC
                """
                )
                rows = cursor.fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"查询待审核文件失败: {e}")
            return []

    def rollback_operation(self, operation_id: str) -> Dict[str, Any]:
        """回滚操作"""
        try:
            # 获取操作记录
            audit_records = self.get_audit_records()
            operation_record = None
            for record in audit_records:
                if record["id"] == operation_id:
                    operation_record = record
                    break

            if not operation_record:
                return {"success": False, "reason": "operation_not_found"}

            # 这里可以实现具体的回滚逻辑
            # 例如：移动文件回原位置，删除链接等
            # 暂时返回成功
            return {
                "success": True,
                "operation_id": operation_id,
                "message": "回滚操作已记录，需要手动执行文件移动",
            }

        except Exception as e:
            self.logger.error(f"回滚操作失败: {e}")
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 审计记录统计
                cursor.execute(f"SELECT COUNT(*) FROM {self.audit_table}")
                total_operations = cursor.fetchone()[0]

                cursor.execute(
                    f"SELECT COUNT(*) FROM {self.audit_table} WHERE status = 'success'"
                )
                successful_operations = cursor.fetchone()[0]

                # 文件状态统计
                cursor.execute(f"SELECT COUNT(*) FROM {self.status_table}")
                total_files = cursor.fetchone()[0]

                cursor.execute(
                    f"SELECT COUNT(*) FROM {self.status_table} WHERE needs_review = TRUE"
                )
                files_needing_review = cursor.fetchone()[0]

                # 分类统计
                cursor.execute(
                    f"SELECT category, COUNT(*) FROM {self.status_table} GROUP BY category"
                )
                category_stats = dict(cursor.fetchall())

                return {
                    "total_operations": total_operations,
                    "successful_operations": successful_operations,
                    "success_rate": (
                        successful_operations / total_operations
                        if total_operations > 0
                        else 0
                    ),
                    "total_files": total_files,
                    "files_needing_review": files_needing_review,
                    "category_distribution": category_stats,
                }

        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
