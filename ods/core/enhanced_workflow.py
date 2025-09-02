"""
增强工作流 - Step 2 Ollama集成

集成Ollama文档阅读和分类的多标签工作流
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime

import requests

from ..parsers.document_parser import DocumentParser
from ..parsers.ollama_reader import OllamaReader
from ..embeddings.embedder import Embedder
from ..classifiers.enhanced_classifier import EnhancedClassifier
from ..classifiers.ollama_classifier import OllamaClassifier
from ..path_planner.path_planner import PathPlanner
from ..naming.renamer import Renamer
from ..rules.enhanced_rule_engine import EnhancedRuleEngine
from ..storage.file_mover import FileMover
from ..storage.index_updater import IndexUpdater


class EnhancedWorkflow:
    """增强工作流 - 集成Ollama的多标签文档处理"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化各个模块
        self.document_parser = DocumentParser(config)
        self.ollama_reader = (
            OllamaReader(config)
            if config.get("ollama", {}).get("enable_reader", True)
            else None
        )
        self.embedder = Embedder(config)
        self.enhanced_classifier = EnhancedClassifier(config)
        self.ollama_classifier = (
            OllamaClassifier(config) if self._ollama_available() else None
        )
        self.path_planner = PathPlanner(config)
        self.renamer = Renamer(config)
        self.rule_engine = EnhancedRuleEngine(config)
        self.file_mover = FileMover(config)
        self.index_updater = IndexUpdater(config)

        self.logger.info("增强工作流初始化完成")
        if self.ollama_reader:
            self.logger.info("Ollama阅读器已启用")
        if self.ollama_classifier:
            self.logger.info("Ollama分类器已启用")

    def _ollama_available(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            ollama_config = self.config.get("ollama", {})
            if not ollama_config.get("enable_reader", True):
                return False

            base_url = ollama_config.get("base_url", "http://localhost:11434")
            url = f"{base_url}/api/tags"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _validate_workflow_state(
        self, state: Dict[str, Any], required_keys: List[str]
    ) -> None:
        """
        验证工作流状态是否包含必需的键

        Args:
            state: 工作流状态字典
            required_keys: 必需的键列表

        Raises:
            ValueError: 如果缺少必需的键
        """
        missing_keys = [key for key in required_keys if key not in state]
        if missing_keys:
            error_msg = f"工作流状态缺少必需键: {missing_keys}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _create_error_state(
        self, file_path: str, error: str, status: str = "error"
    ) -> Dict[str, Any]:
        """
        创建错误状态

        Args:
            file_path: 文件路径
            error: 错误信息
            status: 状态类型

        Returns:
            Dict[str, Any]: 错误状态字典
        """
        return {
            "file_path": file_path,
            "status": status,
            "error": error,
            "processing_end": datetime.now().isoformat(),
            "success": False,
        }

    def _time_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        计时操作执行时间

        Args:
            operation_name: 操作名称
            operation_func: 要执行的操作函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Tuple[Any, float]: (操作结果, 执行时间秒数)
        """
        start_time = datetime.now()
        try:
            result = operation_func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            return result, duration
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            raise e

    def _record_step_time(self, state: Dict[str, Any], step_name: str, duration: float):
        """
        记录步骤执行时间

        Args:
            state: 工作流状态
            step_name: 步骤名称
            duration: 执行时间（秒）
        """
        if "performance" not in state:
            state["performance"] = {"step_times": {}}
        if "step_times" not in state["performance"]:
            state["performance"]["step_times"] = {}

        state["performance"]["step_times"][step_name] = duration
        self.logger.debug(f"步骤 '{step_name}' 耗时: {duration:.2f}秒")

    def _finalize_performance_metrics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        完成性能指标计算

        Args:
            state: 工作流状态

        Returns:
            Dict[str, Any]: 包含性能指标的状态
        """
        if "performance" not in state:
            return state

        perf = state["performance"]
        start_time = perf.get("start_time")

        if start_time:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            perf["total_duration"] = total_duration
            perf["end_time"] = end_time

            # 计算各步骤时间占比
            step_times = perf.get("step_times", {})
            if step_times:
                perf["step_breakdown"] = {}
                for step, duration in step_times.items():
                    perf["step_breakdown"][step] = {
                        "duration": duration,
                        "percentage": (
                            (duration / total_duration * 100)
                            if total_duration > 0
                            else 0
                        ),
                    }

        # 添加系统资源信息（如果可用）
        try:
            import psutil

            perf["memory_usage"] = {
                "rss": psutil.Process().memory_info().rss / 1024 / 1024,  # MB
                "vms": psutil.Process().memory_info().vms / 1024 / 1024,  # MB
                "cpu_percent": psutil.cpu_percent(interval=0.1),
            }
        except ImportError:
            perf["memory_usage"] = None

        return state

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        处理单个文件

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.logger.info(f"开始处理文件: {file_path}")

            # 初始化状态和性能监控
            processing_start = datetime.now()
            state = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "processing_start": processing_start.isoformat(),
                "status": "processing",
                "performance": {
                    "start_time": processing_start,
                    "step_times": {},
                    "component_times": {},
                    "memory_usage": None,
                },
            }

            # 执行工作流步骤
            try:
                self._validate_workflow_state(state, ["file_path", "processing_start"])
                # 步骤1: 解析文档
                try:
                    state, parse_duration = self._time_operation(
                        "parse_document", self._parse_document, state
                    )
                    self._record_step_time(state, "parse", parse_duration)

                    if not state.get("parse_success"):
                        error_msg = (
                            f"文档解析失败: {state.get('parse_error', '未知错误')}"
                        )
                        self.logger.error(error_msg)
                        return self._create_error_state(
                            str(file_path), error_msg, "parse_failed"
                        )
                except Exception as parse_error:
                    error_msg = f"文档解析异常: {str(parse_error)}"
                    self.logger.error(error_msg)
                    return self._create_error_state(
                        str(file_path), error_msg, "parse_error"
                    )

                # 步骤2: Ollama阅读（如果可用）
                try:
                    state = self._ollama_read_document(state)
                except Exception as ollama_error:
                    self.logger.warning(f"Ollama阅读异常，但继续处理: {ollama_error}")
                    # Ollama失败不影响整体流程

                # 步骤3: 生成嵌入
                try:
                    state, embedding_duration = self._time_operation(
                        "generate_embedding", self._generate_embedding, state
                    )
                    self._record_step_time(state, "embedding", embedding_duration)

                    if not state.get("embedding_success"):
                        self.logger.warning(
                            f"嵌入生成失败，但继续处理: {state.get('embedding_error', '未知错误')}"
                        )
                except Exception as embedding_error:
                    self.logger.warning(f"嵌入生成异常，但继续处理: {embedding_error}")

                # 步骤4: 分类文档
                try:
                    state, classify_duration = self._time_operation(
                        "classify_document", self._classify_document, state
                    )
                    self._record_step_time(state, "classification", classify_duration)

                    if not state.get("classification"):
                        error_msg = "文档分类失败: 未返回分类结果"
                        self.logger.error(error_msg)
                        return self._create_error_state(
                            str(file_path), error_msg, "classification_failed"
                        )
                except Exception as classify_error:
                    error_msg = f"文档分类异常: {str(classify_error)}"
                    self.logger.error(error_msg)
                    return self._create_error_state(
                        str(file_path), error_msg, "classification_error"
                    )

                # 步骤5: 路径规划
                try:
                    state = self._plan_path(state)
                except Exception as path_error:
                    error_msg = f"路径规划异常: {str(path_error)}"
                    self.logger.error(error_msg)
                    return self._create_error_state(
                        str(file_path), error_msg, "path_planning_error"
                    )

                # 步骤6: 重命名文件
                try:
                    state = self._rename_file(state)
                except Exception as rename_error:
                    self.logger.warning(f"文件重命名异常，但继续处理: {rename_error}")

                # 步骤7: 移动文件
                try:
                    state = self._move_file(state)
                    if not state.get("move_success"):
                        error_msg = (
                            f"文件移动失败: {state.get('move_error', '未知错误')}"
                        )
                        self.logger.error(error_msg)
                        return self._create_error_state(
                            str(file_path), error_msg, "move_failed"
                        )
                except Exception as move_error:
                    error_msg = f"文件移动异常: {str(move_error)}"
                    self.logger.error(error_msg)
                    return self._create_error_state(
                        str(file_path), error_msg, "move_error"
                    )

                # 步骤8: 更新索引
                try:
                    state = self._update_index(state)
                except Exception as index_error:
                    self.logger.warning(f"索引更新异常，但文件处理成功: {index_error}")

                # 完成性能指标计算
                state = self._finalize_performance_metrics(state)

                # 成功完成
                state["status"] = "completed"
                state["success"] = True

                # 记录性能摘要
                perf = state.get("performance", {})
                total_time = perf.get("total_duration", 0)
                self.logger.info(
                    f"文件处理完成: {file_path} (耗时: {total_time:.2f}秒)"
                )

            except Exception as workflow_error:
                state["status"] = "failed"
                state["error"] = str(workflow_error)
                state["success"] = False
                self.logger.error(f"工作流执行失败: {workflow_error}")
                return state

            # 添加最终状态
            state["processing_end"] = datetime.now().isoformat()
            state["processing_duration"] = (
                datetime.fromisoformat(state["processing_end"])
                - datetime.fromisoformat(state["processing_start"])
            ).total_seconds()

            return state

        except Exception as e:
            self.logger.error(f"文件处理异常: {e}")
            return self._create_error_state(str(file_path), str(e), "processing_error")

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        获取工作流执行摘要

        Returns:
            Dict[str, Any]: 工作流摘要信息
        """
        return {
            "workflow_type": "enhanced",
            "ollama_reader_enabled": self.ollama_reader is not None,
            "ollama_classifier_enabled": self.ollama_classifier is not None,
            "ollama_available": self._ollama_available(),
            "components": {
                "document_parser": type(self.document_parser).__name__,
                "ollama_reader": (
                    type(self.ollama_reader).__name__ if self.ollama_reader else None
                ),
                "embedder": type(self.embedder).__name__,
                "enhanced_classifier": type(self.enhanced_classifier).__name__,
                "ollama_classifier": (
                    type(self.ollama_classifier).__name__
                    if self.ollama_classifier
                    else None
                ),
                "path_planner": type(self.path_planner).__name__,
                "renamer": type(self.renamer).__name__,
                "file_mover": type(self.file_mover).__name__,
                "index_updater": type(self.index_updater).__name__,
            },
            "capabilities": {
                "ollama_integration": self._ollama_available(),
                "embedding_generation": True,
                "multi_label_classification": True,
                "file_organization": True,
                "index_management": True,
            },
        }

    def _parse_document(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """解析文档内容"""
        try:
            file_path = state["file_path"]
            self.logger.info(f"解析文档: {file_path}")

            # 使用文档解析器
            parse_result = self.document_parser.parse(file_path)

            if parse_result.success:
                state["text_content"] = parse_result.content.text
                state["parse_success"] = True
                state["document_metadata"] = {
                    "title": parse_result.content.title,
                    "word_count": parse_result.content.word_count,
                    "page_count": getattr(parse_result.content, "page_count", None),
                    "language": getattr(parse_result.content, "language", None),
                }
                self.logger.info(f"文档解析成功: {len(state['text_content'])} 字符")
            else:
                state["parse_success"] = False
                state["parse_error"] = parse_result.error
                self.logger.error(f"文档解析失败: {parse_result.error}")

            return state

        except Exception as e:
            self.logger.error(f"文档解析异常: {e}")
            state["parse_success"] = False
            state["parse_error"] = str(e)
            return state

    def _ollama_read_document(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """使用Ollama阅读和理解文档"""
        try:
            if not self.ollama_reader or not self.ollama_reader.is_available():
                self.logger.info("Ollama阅读器不可用，跳过Ollama阅读步骤")
                return state

            file_path = state["file_path"]
            text_content = state.get("text_content", "")

            self.logger.info(f"使用Ollama阅读文档: {file_path}")

            # 使用Ollama阅读文档
            ollama_result = self.ollama_reader.read_document(file_path, text_content)

            if ollama_result.get("ollama_processed"):
                state["ollama_content"] = ollama_result["enhanced_content"]
                state["ollama_summary"] = ollama_result["enhanced_content"].get(
                    "summary", ""
                )
                state["ollama_keywords"] = ollama_result["enhanced_content"].get(
                    "keywords", []
                )
                state["ollama_insights"] = self.ollama_reader.extract_document_insights(
                    text_content
                )
                self.logger.info("Ollama文档阅读完成")
            else:
                self.logger.warning("Ollama阅读失败，使用原始内容")
                state["ollama_content"] = ollama_result.get("enhanced_content", {})

            return state

        except Exception as e:
            self.logger.error(f"Ollama阅读异常: {e}")
            return state

    def _generate_embedding(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成文档嵌入"""
        try:
            if not state.get("parse_success"):
                self.logger.warning("文档解析失败，跳过嵌入生成")
                return state

            text_content = state.get("text_content", "")
            self.logger.info(f"生成文档嵌入: {len(text_content)} 字符")

            # 检查文本内容是否足够生成嵌入
            if not text_content or len(text_content.strip()) < 10:
                state["embedding_success"] = False
                state["embedding_error"] = "文本内容过短或为空，无法生成嵌入"
                self.logger.warning("文本内容过短，跳过嵌入生成")
                return state

            # 准备文档数据
            document_data = {
                "text_content": text_content,
                "file_path": state.get("file_path"),
                "document_metadata": state.get("document_metadata", {}),
            }

            # 生成嵌入
            embedding_result = self.embedder.process_document(document_data)

            if embedding_result.get("status") == "success":
                embedding = embedding_result.get("embedding")
                if embedding is not None:
                    state["embedding"] = embedding
                    state["embedding_dimension"] = embedding_result.get(
                        "embedding_dimension",
                        len(embedding) if hasattr(embedding, "__len__") else 0,
                    )
                    state["embedding_success"] = True
                    state["document_summary"] = embedding_result.get("summary")
                    state["document_keywords"] = embedding_result.get("keywords")
                    self.logger.info(
                        f"文档嵌入生成成功，维度: {state['embedding_dimension']}"
                    )
                else:
                    state["embedding_success"] = False
                    state["embedding_error"] = "嵌入向量为空"
                    self.logger.error("嵌入向量为空")
            elif embedding_result.get("status") == "error":
                state["embedding_success"] = False
                state["embedding_error"] = embedding_result.get(
                    "error_message", "嵌入生成失败"
                )
                self.logger.error(f"嵌入生成失败: {state['embedding_error']}")
            else:
                state["embedding_success"] = False
                state["embedding_error"] = f"未知状态: {embedding_result.get('status')}"
                self.logger.error(f"嵌入生成未知状态: {embedding_result.get('status')}")

            return state

        except Exception as e:
            self.logger.error(f"嵌入生成异常: {e}")
            state["embedding_success"] = False
            state["embedding_error"] = str(e)
            return state

    def _classify_document(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """分类文档"""
        try:
            if not state.get("parse_success"):
                self.logger.warning("文档解析失败，跳过分类")
                return state

            # 验证必要数据
            text_content = state.get("text_content", "").strip()
            if not text_content or len(text_content) < 10:
                state["classification"] = {
                    "tags": [],
                    "confidence_score": 0.0,
                    "reasoning": "文档内容过短或为空，无法进行分类",
                    "primary_tag": "",
                    "status": "error",
                    "needs_review": True,
                    "review_reason": "文档内容不足",
                }
                self.logger.warning("文档内容过短，跳过分类")
                return state

            # 准备文档数据用于分类
            document_data = {
                "file_path": state["file_path"],
                "text_content": text_content,
                "ollama_content": state.get("ollama_content", {}),
                "embedding": state.get("embedding"),
                "summary": state.get("document_summary", ""),  # 添加文档摘要
                "document_metadata": state.get("document_metadata", {}),
            }

            self.logger.info(f"开始分类文档: {state['file_path']}")

            # 选择分类器：优先使用Ollama分类器
            try:
                if self.ollama_classifier and self.ollama_classifier.is_available():
                    classification_result = self.ollama_classifier.classify_document(
                        document_data
                    )
                    state["classifier_used"] = "ollama"
                else:
                    classification_result = self.enhanced_classifier.classify_document(
                        document_data
                    )
                    state["classifier_used"] = "enhanced"

                # 验证分类结果
                if not isinstance(classification_result, dict):
                    raise ValueError(f"分类器返回的不是字典: {classification_result}")

            except Exception as classifier_error:
                self.logger.error(f"分类器调用失败: {classifier_error}")
                classification_result = {
                    "tags": [],
                    "confidence_score": 0.0,
                    "reasoning": f"分类失败: {str(classifier_error)}",
                    "primary_tag": "",
                    "status": "error",
                    "needs_review": True,
                    "review_reason": "分类器调用失败",
                }

            # 保存分类结果
            state["classification"] = classification_result
            state["tags"] = classification_result.get("tags", [])
            state["primary_tag"] = classification_result.get("primary_tag", "")
            state["confidence_score"] = classification_result.get(
                "confidence_score", 0.0
            )
            state["needs_review"] = classification_result.get("needs_review", False)

            self.logger.info(
                f"文档分类完成: {state['primary_tag']} "
                f"(置信度: {state['confidence_score']:.2f})"
            )

            return state

        except Exception as e:
            self.logger.error(f"文档分类异常: {e}")
            state["classification"] = {
                "error": str(e),
                "tags": [],
                "confidence_score": 0.0,
            }
            state["tags"] = []
            state["primary_tag"] = "分类失败"
            state["confidence_score"] = 0.0
            return state

    def _plan_path(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """规划文件路径"""
        try:
            if not state.get("parse_success"):
                self.logger.warning("文档解析失败，跳过路径规划")
                return state

            # 使用路径规划器
            path_plan = self.path_planner.plan_file_path(
                state["classification"],
                state["file_path"],
                state.get("document_metadata", {}),
            )

            state["path_plan"] = path_plan
            state["target_path"] = path_plan.get("primary_path", "")

            self.logger.info(f"路径规划完成: {state['target_path']}")
            return state

        except Exception as e:
            self.logger.error(f"路径规划异常: {e}")
            return state

    def _rename_file(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """重命名文件"""
        try:
            if not state.get("parse_success"):
                self.logger.warning("文档解析失败，跳过重命名")
                return state

            # 使用重命名器
            naming_result = self.renamer.generate_filename(
                state["path_plan"],
                state["classification"],
                state.get("ollama_content", {}),
            )

            state["naming_result"] = naming_result
            state["final_name"] = naming_result.get("new_name", "")

            self.logger.info(f"文件重命名完成: {state['final_name']}")
            return state

        except Exception as e:
            self.logger.error(f"文件重命名异常: {e}")
            return state

    def _move_file(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        try:
            if not state.get("parse_success"):
                self.logger.warning("文档解析失败，跳过移动")
                return state

            # 使用文件移动器
            move_result = self.file_mover.move_file(
                state["path_plan"], state["naming_result"]
            )

            state["move_result"] = move_result
            state["move_success"] = move_result.get("moved", False)
            state["final_path"] = move_result.get("final_path", "")

            if state["move_success"]:
                self.logger.info(f"文件移动完成: {state['final_path']}")
            else:
                self.logger.error(
                    f"文件移动失败: {move_result.get('error', '未知错误')}"
                )

            return state

        except Exception as e:
            self.logger.error(f"文件移动异常: {e}")
            state["move_success"] = False
            state["move_error"] = str(e)
            return state

    def _update_index(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """更新索引"""
        try:
            if not state.get("move_success"):
                self.logger.warning("文件移动失败，跳过索引更新")
                return state

            # 验证必需的状态数据
            required_keys = [
                "move_result",
                "classification",
                "file_path",
                "processing_start",
            ]
            missing_keys = [key for key in required_keys if key not in state]
            if missing_keys:
                self.logger.error(f"索引更新缺少必需数据: {missing_keys}")
                state["index_success"] = False
                state["index_error"] = f"缺少必需数据: {missing_keys}"
                return state

            # 计算处理时间
            try:
                processing_time = datetime.now() - datetime.fromisoformat(
                    state["processing_start"]
                )
            except (ValueError, TypeError) as time_error:
                self.logger.warning(f"处理时间计算失败，使用默认值: {time_error}")
                processing_time = datetime.now() - datetime.now()  # 0时间差

            # 准备索引更新数据（按照IndexUpdater期望的参数顺序）
            move_result = state["move_result"]  # 第一参数：移动结果
            document_data = {
                "file_path": state.get("final_path", state["file_path"]),
                "original_path": state["file_path"],
                "content": state.get("text_content", ""),
                "embedding": state.get("embedding"),
                "ollama_content": state.get("ollama_content", {}),
                "metadata": state.get("document_metadata", {}),
            }  # 第二参数：文档数据
            classification_result = state["classification"]  # 第三参数：分类结果

            # 更新索引
            index_result = self.index_updater.update_indexes(
                move_result,  # 第一参数：移动结果
                document_data,  # 第二参数：文档数据
                classification_result,  # 第三参数：分类结果
                processing_time.total_seconds(),  # 第四参数：处理时间（秒）
            )

            state["index_result"] = index_result
            state["index_success"] = index_result.get("success", False)

            if state["index_success"]:
                self.logger.info("索引更新完成")
            else:
                self.logger.error(
                    f"索引更新失败: {index_result.get('error', '未知错误')}"
                )

            return state

        except Exception as e:
            self.logger.error(f"索引更新异常: {e}")
            state["index_success"] = False
            state["index_error"] = str(e)
            return state

        finally:
            # 在工作流结束时处理审核集成
            state = self._handle_review_integration(state)

    def _handle_review_integration(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理审核集成逻辑

        Args:
            state: 工作流状态

        Returns:
            Dict[str, Any]: 更新后的状态
        """
        try:
            # 检查是否需要审核
            classification_result = state.get("classification", {})
            needs_review = classification_result.get("needs_review", False)

            if needs_review:
                self.logger.info("文件需要人工审核，已标记为待审核状态")

                # 在状态中记录审核信息
                state["review_required"] = True
                state["review_reason"] = classification_result.get(
                    "review_reason", "置信度不足"
                )

                # 记录到数据库的review状态
                try:
                    from ..core.database import Database

                    database = Database(self.config)

                    # 更新文件状态为需要审核
                    file_path = state.get("file_path", "")
                    if file_path:
                        database.update_file_review_status(file_path, True)
                        self.logger.debug(f"已标记文件为需要审核: {file_path}")
                except Exception as db_e:
                    self.logger.warning(f"更新审核状态失败: {db_e}")

            return state

        except Exception as e:
            self.logger.error(f"处理审核集成失败: {e}")
            return state

    def get_pending_reviews_summary(self) -> Dict[str, Any]:
        """
        获取待审核文件摘要

        Returns:
            Dict[str, Any]: 待审核文件摘要
        """
        try:
            from ..review.review_manager import ReviewManager

            review_manager = ReviewManager(self.config)

            stats = review_manager.get_review_statistics()

            return {
                "pending_reviews": stats.get("pending_reviews", 0),
                "review_sessions": stats.get("total_sessions", 0),
                "has_pending_work": stats.get("pending_reviews", 0) > 0,
                "recommend_review": stats.get("pending_reviews", 0) > 0,
            }

        except Exception as e:
            self.logger.error(f"获取审核摘要失败: {e}")
            return {
                "pending_reviews": 0,
                "review_sessions": 0,
                "has_pending_work": False,
                "recommend_review": False,
            }

    def get_workflow_summary(self) -> Dict[str, Any]:
        """获取工作流摘要"""
        return {
            "workflow_type": "enhanced",
            "ollama_reader_enabled": self.ollama_reader is not None,
            "ollama_classifier_enabled": self.ollama_classifier is not None,
            "ollama_available": self._ollama_available(),
            "components": {
                "document_parser": "DocumentParser",
                "ollama_reader": "OllamaReader" if self.ollama_reader else None,
                "embedder": "Embedder",
                "enhanced_classifier": "EnhancedClassifier",
                "ollama_classifier": (
                    "OllamaClassifier" if self.ollama_classifier else None
                ),
                "path_planner": "PathPlanner",
                "renamer": "Renamer",
                "rule_engine": "EnhancedRuleEngine",
                "file_mover": "FileMover",
                "index_updater": "IndexUpdater",
            },
        }
