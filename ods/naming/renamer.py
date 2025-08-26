import logging
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import yaml
from jinja2 import Template, Environment, BaseLoader


class Renamer:
    """命名生成器 - 根据文档内容和元数据生成有意义的文件名"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 命名配置
        self.naming_config = config.get("naming", {})
        self.default_template = self.naming_config.get(
            "default_template", "{{category}}-{{title}}-{{date}}.{{ext}}"
        )
        self.max_filename_length = self.naming_config.get("max_filename_length", 200)
        self.enable_llm_title = self.naming_config.get("enable_llm_title", True)
        self.title_max_length = self.naming_config.get("title_max_length", 50)
        self.conflict_resolution = self.naming_config.get(
            "conflict_resolution", "suffix"
        )

        # 特殊字符处理
        self.invalid_chars = self.naming_config.get("invalid_chars", r'[<>:"/\\|?*]')
        self.replacement_char = self.naming_config.get("replacement_char", "_")

        # 加载命名模板
        self.templates = self._load_naming_templates()

        # 初始化Jinja2环境
        self.jinja_env = Environment(loader=BaseLoader())
        self.jinja_env.filters["strftime"] = self._strftime_filter
        self.jinja_env.filters["truncate"] = self._truncate_filter
        self.jinja_env.filters["clean_filename"] = self._clean_filename_filter

        self.logger.info("命名生成器初始化完成")

    def generate_filename(
        self,
        path_plan: Dict[str, Any],
        document_data: Dict[str, Any],
        classification_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成文件名"""
        try:
            self.logger.info(f"开始生成文件名: {path_plan.get('original_path', '')}")

            # 获取基础信息
            original_path = path_plan.get("original_path", "")
            primary_path = path_plan.get("primary_path", "")
            category = path_plan.get("category", "")

            # 提取文档信息
            document_info = self._extract_document_info(
                document_data, classification_result
            )

            # 选择命名模板
            template = self._select_naming_template(category, document_info)

            # 生成标题（如果需要）
            if self.enable_llm_title and not document_info.get("title"):
                document_info["title"] = self._generate_title_with_llm(document_data)

            # 应用模板生成文件名
            filename = self._apply_naming_template(template, document_info)

            # 清理文件名
            clean_filename = self._clean_filename(filename)

            # 检查长度限制
            if len(clean_filename) > self.max_filename_length:
                clean_filename = self._truncate_filename(clean_filename)

            # 构建新路径
            new_path = self._build_new_path(primary_path, clean_filename)

            # 检查冲突
            conflict_info = self._check_filename_conflicts(new_path, original_path)

            # 生成命名结果
            naming_result = {
                "original_path": original_path,
                "new_path": new_path,
                "original_filename": Path(original_path).name,
                "new_filename": clean_filename,
                "template_used": template,
                "document_info": document_info,
                "conflict_info": conflict_info,
                "naming_time": datetime.now().isoformat(),
                "status": "generated",
            }

            self.logger.info(
                f"文件名生成完成: {Path(original_path).name} -> {clean_filename}"
            )
            return naming_result

        except Exception as e:
            self.logger.error(f"文件名生成失败: {e}")
            return self._create_error_naming(path_plan, str(e))

    def _extract_document_info(
        self, document_data: Dict[str, Any], classification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取文档信息"""
        info = {}

        # 基本信息
        info["category"] = classification_result.get("primary_category", "")
        info["tags"] = classification_result.get("tags", [])
        info["confidence_score"] = classification_result.get("confidence_score", 0.0)

        # 文件信息
        if "file_path" in document_data:
            file_path = Path(document_data["file_path"])
            info["ext"] = file_path.suffix.lower().lstrip(".")
            info["original_name"] = file_path.stem
            info["full_path"] = str(file_path)

        # 内容信息
        if "text_content" in document_data:
            text_content = document_data["text_content"]
            info["content_length"] = len(text_content)
            info["title"] = self._extract_title_from_content(text_content)
            info["summary"] = document_data.get("summary", "")

        # 元数据
        if "metadata" in document_data:
            metadata = document_data["metadata"]
            info.update(metadata)

        # 时间信息
        now = datetime.now()
        info["date"] = now.strftime("%Y%m%d")
        info["time"] = now.strftime("%H%M%S")
        info["timestamp"] = now.strftime("%Y%m%d_%H%M%S")
        info["year"] = str(now.year)
        info["month"] = f"{now.month:02d}"
        info["day"] = f"{now.day:02d}"

        return info

    def _extract_title_from_content(self, content: str) -> str:
        """从内容中提取标题"""
        if not content:
            return ""

        # 尝试从第一行提取标题
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) > 2 and len(line) < 100:
                # 检查是否像标题（允许中英文、数字、基本标点，长度适中）
                # 标题通常不会太长，且不会包含太多标点符号
                if (
                    re.match(r"^[\w\s\-_\.\u4e00-\u9fff\(\)（）]+$", line, re.UNICODE)
                    and len(line) < 30
                    and line.count("。") == 0
                    and line.count("，") == 0
                    and line.count("：") == 0
                    and line.count("...") == 0
                ):
                    return line[: self.title_max_length]

        # 如果没有找到合适的标题，返回空字符串
        return ""

    def _generate_title_with_llm(self, document_data: Dict[str, Any]) -> str:
        """使用LLM生成标题"""
        try:
            # 这里应该调用LLM服务，暂时返回一个简单的标题
            text_content = document_data.get("text_content", "")
            if text_content:
                # 简单的标题生成逻辑
                words = text_content[:200].split()
                if len(words) > 3:
                    title = " ".join(words[:5])
                    return title[: self.title_max_length]

            return "未命名文档"

        except Exception as e:
            self.logger.warning(f"LLM标题生成失败: {e}")
            return "未命名文档"

    def _select_naming_template(
        self, category: str, document_info: Dict[str, Any]
    ) -> str:
        """选择命名模板"""
        # 检查是否有类别特定的模板
        if category in self.templates:
            return self.templates[category]

        # 检查文件类型特定的模板
        file_ext = document_info.get("ext", "")
        if file_ext in self.templates:
            return self.templates[file_ext]

        # 使用默认模板
        return self.default_template

    def _apply_naming_template(
        self, template: str, document_info: Dict[str, Any]
    ) -> str:
        """应用命名模板"""
        try:
            # 使用Jinja2渲染模板
            jinja_template = self.jinja_env.from_string(template)
            filename = jinja_template.render(**document_info)

            # 清理多余的空白字符
            filename = re.sub(r"\s+", " ", filename).strip()

            return filename

        except Exception as e:
            self.logger.warning(f"模板应用失败: {e}")
            # 回退到简单替换
            return self._simple_template_replace(template, document_info)

    def _simple_template_replace(
        self, template: str, document_info: Dict[str, Any]
    ) -> str:
        """简单的模板替换（回退方案）"""
        result = template
        for key, value in document_info.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def _clean_filename(self, filename: str) -> str:
        """清理文件名"""
        if not filename:
            return "未命名文件"

        # 替换无效字符
        clean_name = re.sub(self.invalid_chars, self.replacement_char, filename)

        # 移除首尾的点和空格
        clean_name = clean_name.strip(". ")

        # 确保文件名不为空
        if not clean_name:
            clean_name = "未命名文件"

        return clean_name

    def _truncate_filename(self, filename: str) -> str:
        """截断过长的文件名"""
        if len(filename) <= self.max_filename_length:
            return filename

        # 保留扩展名
        name_parts = filename.rsplit(".", 1)
        if len(name_parts) > 1:
            stem, ext = name_parts
            max_stem_length = (
                self.max_filename_length - len(ext) - 1 - 3
            )  # -3 for "..."
            if max_stem_length > 10:
                return f"{stem[:max_stem_length]}...{ext}"

        # 没有扩展名或扩展名太长
        return filename[: self.max_filename_length - 3] + "..."

    def _build_new_path(self, primary_path: str, new_filename: str) -> str:
        """构建新路径"""
        primary_path_obj = Path(primary_path)
        new_path = str(primary_path_obj.parent / new_filename)
        # 统一使用正斜杠以确保跨平台兼容性
        return new_path.replace("\\", "/")

    def _check_filename_conflicts(
        self, new_path: str, original_path: str
    ) -> Dict[str, Any]:
        """检查文件名冲突"""
        new_path_obj = Path(new_path)

        conflict_info = {
            "has_conflict": False,
            "conflict_type": None,
            "resolution": None,
            "final_path": new_path,
        }

        # 检查文件是否已存在
        if new_path_obj.exists():
            conflict_info["has_conflict"] = True
            conflict_info["conflict_type"] = "file_exists"

            # 应用冲突解决策略
            if self.conflict_resolution == "suffix":
                resolved_path = self._resolve_filename_conflict_with_suffix(new_path)
                conflict_info["resolution"] = "suffix"
                conflict_info["final_path"] = resolved_path
            elif self.conflict_resolution == "timestamp":
                resolved_path = self._resolve_filename_conflict_with_timestamp(new_path)
                conflict_info["resolution"] = "timestamp"
                conflict_info["final_path"] = resolved_path

        return conflict_info

    def _resolve_filename_conflict_with_suffix(self, path: str) -> str:
        """通过添加后缀解决文件名冲突"""
        path_obj = Path(path)
        counter = 1

        while path_obj.exists():
            stem = path_obj.stem
            suffix = path_obj.suffix
            new_name = f"{stem}_{counter}{suffix}"
            path_obj = path_obj.parent / new_name
            counter += 1

        return str(path_obj)

    def _resolve_filename_conflict_with_timestamp(self, path: str) -> str:
        """通过添加时间戳解决文件名冲突"""
        path_obj = Path(path)
        timestamp = datetime.now().strftime("%H%M%S")
        stem = path_obj.stem
        suffix = path_obj.suffix
        new_name = f"{stem}_{timestamp}{suffix}"

        return str(path_obj.parent / new_name)

    def _create_error_naming(
        self, path_plan: Dict[str, Any], error_message: str
    ) -> Dict[str, Any]:
        """创建错误命名结果"""
        original_path = path_plan.get("original_path", "")
        original_filename = Path(original_path).name if original_path else "未知文件"

        return {
            "original_path": original_path,
            "new_path": original_path,  # 保持原路径
            "original_filename": original_filename,
            "new_filename": original_filename,  # 保持原文件名
            "template_used": "error",
            "document_info": {},
            "conflict_info": {"has_conflict": False},
            "naming_time": datetime.now().isoformat(),
            "status": "error",
            "error_message": error_message,
        }

    def _load_naming_templates(self) -> Dict[str, str]:
        """加载命名模板"""
        templates_file = self.naming_config.get(
            "templates_file", "config/naming_templates.yaml"
        )

        try:
            if Path(templates_file).exists():
                with open(templates_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.warning(f"加载命名模板失败: {e}")

        return {}

    def _strftime_filter(self, value, format_str="%Y%m%d"):
        """Jinja2过滤器：格式化日期"""
        if isinstance(value, datetime):
            return value.strftime(format_str)
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime(format_str)
            except:
                return value
        return value

    def _truncate_filter(self, value, length=50):
        """Jinja2过滤器：截断字符串"""
        if isinstance(value, str) and len(value) > length:
            return value[: length - 3] + "..."
        return value

    def _clean_filename_filter(self, value):
        """Jinja2过滤器：清理文件名"""
        if isinstance(value, str):
            return self._clean_filename(value)
        return value

    def add_naming_template(self, category: str, template: str) -> bool:
        """添加命名模板"""
        try:
            self.templates[category] = template
            self._save_naming_templates()
            self.logger.info(f"添加命名模板成功: {category}")
            return True
        except Exception as e:
            self.logger.error(f"添加命名模板失败: {e}")
            return False

    def remove_naming_template(self, category: str) -> bool:
        """移除命名模板"""
        try:
            if category in self.templates:
                del self.templates[category]
                self._save_naming_templates()
                self.logger.info(f"移除命名模板成功: {category}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除命名模板失败: {e}")
            return False

    def _save_naming_templates(self) -> bool:
        """保存命名模板"""
        templates_file = self.naming_config.get(
            "templates_file", "config/naming_templates.yaml"
        )

        try:
            templates_file_path = Path(templates_file)
            templates_file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(templates_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.templates, f, default_flow_style=False, allow_unicode=True
                )

            return True
        except Exception as e:
            self.logger.error(f"保存命名模板失败: {e}")
            return False

    def get_naming_templates(self) -> Dict[str, str]:
        """获取所有命名模板"""
        return self.templates.copy()

    def validate_naming_result(self, naming_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证命名结果"""
        validation_result = {"is_valid": True, "errors": [], "warnings": []}

        # 检查必要字段
        required_fields = ["original_path", "new_path", "new_filename", "status"]
        for field in required_fields:
            if field not in naming_result:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"缺少必要字段: {field}")

        # 检查文件名长度
        new_filename = naming_result.get("new_filename", "")
        if len(new_filename) > self.max_filename_length:
            validation_result["warnings"].append(
                f"文件名长度超过限制: {len(new_filename)} > {self.max_filename_length}"
            )

        # 检查文件名是否包含无效字符
        if re.search(self.invalid_chars, new_filename):
            validation_result["errors"].append("文件名包含无效字符")

        # 检查路径格式
        new_path = naming_result.get("new_path", "")
        try:
            Path(new_path)
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"新路径格式错误: {e}")

        return validation_result

    def get_naming_statistics(self) -> Dict[str, Any]:
        """获取命名统计信息"""
        return {
            "default_template": self.default_template,
            "max_filename_length": self.max_filename_length,
            "enable_llm_title": self.enable_llm_title,
            "title_max_length": self.title_max_length,
            "conflict_resolution": self.conflict_resolution,
            "templates_count": len(self.templates),
            "invalid_chars_pattern": self.invalid_chars,
            "replacement_char": self.replacement_char,
        }
