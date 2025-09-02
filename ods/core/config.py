"""
配置管理模块

负责加载、验证和管理系统配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import logging


@dataclass
class LLMConfig:
    """LLM配置"""

    provider: str = "openai"  # openai, claude, ollama
    api_key: Optional[str] = None
    model: str = "gpt-4"
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 1000


@dataclass
class EmbeddingConfig:
    """嵌入模型配置"""

    model: str = "BAAI/bge-large-en-v1.5"
    device: str = "cpu"
    max_length: int = 512


@dataclass
class DatabaseConfig:
    """数据库配置"""

    type: str = "sqlite"
    path: str = ".ods/db.sqlite"
    vector_db_path: str = ".ods/vector_db"


@dataclass
class ClassificationConfig:
    """分类配置"""

    categories: List[str] = field(
        default_factory=lambda: ["工作", "个人", "财务", "其他"]
    )
    confidence_threshold: float = 0.8
    review_threshold: float = 0.6
    max_tags: int = 3


@dataclass
class FileConfig:
    """文件处理配置"""

    source_directory: str = ""
    target_directory: str = "分类"
    supported_extensions: List[str] = field(
        default_factory=lambda: [
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".txt",
            ".md",
        ]
    )
    max_file_size: int = 100 * 1024 * 1024  # 100MB


@dataclass
class SystemConfig:
    """系统配置"""

    log_level: str = "INFO"
    log_file: str = ".ods/ods.log"
    temp_directory: str = ".ods/temp"
    backup_enabled: bool = True
    dry_run: bool = False


class Config:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.logger = logging.getLogger(__name__)

        # 默认配置
        self.llm = LLMConfig()
        self.embedding = EmbeddingConfig()
        self.database = DatabaseConfig()
        self.classification = ClassificationConfig()
        self.file = FileConfig()
        self.system = SystemConfig()

        # Ollama配置默认值
        self.ollama_config = {
            "base_url": "http://localhost:11434",
            "model": "qwen3",
            "reader_model": "qwen3",
            "classifier_model": "qwen3",
            "timeout": 300,
            "max_retries": 3,
            "enable_reader": True,
            "enable_insights": True,
            "context_window": 4096
        }

        # 加载配置
        if self.config_path and os.path.exists(self.config_path):
            self.load_config()
        else:
            self.create_default_config()

    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            "config/rules.yaml",
            "rules.yaml",
            "config.yaml",
            ".ods/config.yaml",
            os.path.expanduser("~/.ods/config.yaml"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return "config/rules.yaml"

    def load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                self.logger.warning("配置文件为空，使用默认配置")
                return

            # 加载LLM配置
            if "llm" in config_data:
                llm_data = config_data["llm"]
                self.llm.provider = llm_data.get("provider", self.llm.provider)
                self.llm.api_key = llm_data.get("api_key", self.llm.api_key)
                self.llm.model = llm_data.get("model", self.llm.model)
                self.llm.base_url = llm_data.get("base_url", self.llm.base_url)
                self.llm.temperature = llm_data.get("temperature", self.llm.temperature)
                self.llm.max_tokens = llm_data.get("max_tokens", self.llm.max_tokens)

            # 加载Ollama配置
            if "ollama" in config_data:
                # 将ollama配置存储为字典，因为Config类没有专门的OllamaConfig类
                self.ollama_config = config_data["ollama"]

            # 加载嵌入模型配置
            if "embedding" in config_data:
                embedding_data = config_data["embedding"]
                self.embedding.model = embedding_data.get("model", self.embedding.model)
                self.embedding.device = embedding_data.get(
                    "device", self.embedding.device
                )
                self.embedding.max_length = embedding_data.get(
                    "max_length", self.embedding.max_length
                )

            # 加载数据库配置
            if "database" in config_data:
                db_data = config_data["database"]
                self.database.type = db_data.get("type", self.database.type)
                self.database.path = db_data.get("path", self.database.path)
                self.database.vector_db_path = db_data.get(
                    "vector_db_path", self.database.vector_db_path
                )

            # 加载分类配置
            if "classification" in config_data:
                classification_data = config_data["classification"]
                self.classification.categories = classification_data.get(
                    "categories", self.classification.categories
                )
                self.classification.confidence_threshold = classification_data.get(
                    "confidence_threshold", self.classification.confidence_threshold
                )
                self.classification.review_threshold = classification_data.get(
                    "review_threshold", self.classification.review_threshold
                )
                self.classification.max_tags = classification_data.get(
                    "max_tags", self.classification.max_tags
                )

            # 加载文件配置
            if "file" in config_data:
                file_data = config_data["file"]
                self.file.source_directory = file_data.get(
                    "source_directory", self.file.source_directory
                )
                self.file.target_directory = file_data.get(
                    "target_directory", self.file.target_directory
                )
                self.file.supported_extensions = file_data.get(
                    "supported_extensions", self.file.supported_extensions
                )
                self.file.max_file_size = file_data.get(
                    "max_file_size", self.file.max_file_size
                )

            # 加载系统配置
            if "system" in config_data:
                system_data = config_data["system"]
                self.system.log_level = system_data.get(
                    "log_level", self.system.log_level
                )
                self.system.log_file = system_data.get("log_file", self.system.log_file)
                self.system.temp_directory = system_data.get(
                    "temp_directory", self.system.temp_directory
                )
                self.system.backup_enabled = system_data.get(
                    "backup_enabled", self.system.backup_enabled
                )
                self.system.dry_run = system_data.get("dry_run", self.system.dry_run)

            self.logger.info(f"配置加载成功: {self.config_path}")

        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            self.logger.info("使用默认配置")

    def create_default_config(self) -> None:
        """创建默认配置文件"""
        default_config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.1,
                "max_tokens": 1000,
            },
            "embedding": {
                "model": "BAAI/bge-large-en-v1.5",
                "device": "cpu",
                "max_length": 512,
            },
            "database": {
                "type": "sqlite",
                "path": ".ods/db.sqlite",
                "vector_db_path": ".ods/vector_db",
            },
            "classification": {
                "categories": ["工作", "个人", "财务", "其他"],
                "confidence_threshold": 0.8,
                "review_threshold": 0.6,
                "max_tags": 3,
            },
            "file": {
                "source_directory": "",
                "target_directory": "分类",
                "supported_extensions": [
                    ".pdf",
                    ".docx",
                    ".doc",
                    ".pptx",
                    ".ppt",
                    ".txt",
                    ".md",
                ],
                "max_file_size": 104857600,
            },
            "system": {
                "log_level": "INFO",
                "log_file": ".ods/ods.log",
                "temp_directory": ".ods/temp",
                "backup_enabled": True,
                "dry_run": False,
            },
        }

        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    default_config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )

            self.logger.info(f"默认配置文件已创建: {self.config_path}")

        except Exception as e:
            self.logger.error(f"创建默认配置文件失败: {e}")

    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            "llm": self.llm.__dict__,
            "ollama": self.ollama_config,
            "embedding": self.embedding.__dict__,
            "database": self.database.__dict__,
            "classification": self.classification.__dict__,
            "file": self.file.__dict__,
            "system": self.system.__dict__,
        }

    def validate(self) -> bool:
        """验证配置有效性"""
        errors = []

        # 检查必要的目录
        if self.file.source_directory and not os.path.exists(
            self.file.source_directory
        ):
            errors.append(f"源目录不存在: {self.file.source_directory}")

        # 检查LLM配置
        if self.llm.provider == "openai" and not self.llm.api_key:
            errors.append("OpenAI API密钥未设置")

        # 检查文件扩展名
        if not self.file.supported_extensions:
            errors.append("未配置支持的文件扩展名")

        if errors:
            for error in errors:
                self.logger.error(error)
            return False

        return True

    def save(self) -> None:
        """保存配置到文件"""
        try:
            config_data = self.get_config_dict()
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )
            self.logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
