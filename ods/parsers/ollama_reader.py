"""
Ollama文档阅读器

使用Ollama模型进行文档内容提取、理解和摘要
"""

import logging
import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time


class OllamaReader:
    """Ollama文档阅读器 - 使用本地LLM进行文档理解"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Ollama配置
        self.ollama_config = config.get("ollama", {})
        self.base_url = self.ollama_config.get("base_url", "http://localhost:11434")
        self.model = self.ollama_config.get("model", "qwen3")
        self.timeout = self.ollama_config.get("timeout", 120)
        self.max_retries = self.ollama_config.get("max_retries", 3)
        self.max_content_length = self.ollama_config.get(
            "max_content_length", 8000
        )  # 最大处理内容长度

        # 功能配置
        self.enable_summary = config.get("text_processing", {}).get(
            "generate_summary", True
        )
        self.enable_keywords = config.get("text_processing", {}).get(
            "extract_keywords", True
        )
        self.max_summary_length = config.get("text_processing", {}).get(
            "max_summary_length", 200
        )
        self.max_keywords = config.get("text_processing", {}).get("max_keywords", 10)

        self.logger.info(f"Ollama阅读器初始化完成 - 模型: {self.model}")

    def read_document(self, file_path: str, raw_content: str) -> Dict[str, Any]:
        """
        使用Ollama读取和理解文档

        Args:
            file_path: 文件路径
            raw_content: 原始文本内容

        Returns:
            Dict[str, Any]: 增强的文档信息
        """
        try:
            self.logger.info(f"使用Ollama处理文档: {file_path}")

            # 构建提示词
            prompt = self._build_reading_prompt(file_path, raw_content)

            # 调用Ollama
            ollama_response = self._call_ollama(prompt)

            if not ollama_response:
                self.logger.warning("Ollama调用失败，返回原始内容")
                return self._fallback_result(raw_content)

            # 解析响应
            enhanced_content = self._parse_response(ollama_response, raw_content)

            # 合并结果
            result = {
                "original_content": raw_content,
                "enhanced_content": enhanced_content,
                "ollama_processed": True,
                "model_used": self.model,
                "processing_time": time.time(),
            }

            self.logger.info(
                f"Ollama文档处理完成 - 摘要长度: {len(enhanced_content.get('summary', ''))}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Ollama文档阅读失败: {e}")
            return self._fallback_result(raw_content)

    def _build_reading_prompt(self, file_path: str, content: str) -> str:
        """构建文档阅读提示词"""
        filename = Path(file_path).name

        # 截取内容片段（避免超出模型上下文限制）
        max_length = min(self.max_content_length, 8000)  # 限制在配置的最大长度内
        content_preview = content[:max_length] if len(content) > max_length else content

        if len(content) > max_length:
            self.logger.info(
                f"内容过长 ({len(content)} 字符)，截取前 {max_length} 字符进行处理"
            )

        prompt = f"""你是一个专业的文档分析助手。请仔细阅读以下文档内容，并提供结构化的分析结果。

文档信息:
- 文件名: {filename}
- 内容长度: {len(content)} 字符
- 内容预览: {content_preview}

请分析文档并返回JSON格式的结果，包含以下字段:

{{
    "document_type": "文档类型（如：报告、合同、发票、手册等）",
    "main_topic": "文档主要主题（1-2句话）",
    "summary": "文档摘要（{self.max_summary_length}字以内）",
    "key_points": ["要点1", "要点2", "要点3"],
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "sentiment": "整体情感（积极/中性/消极）",
    "complexity": "内容复杂度（简单/中等/复杂）",
    "language": "主要语言",
    "confidence": "分析置信度（0.0-1.0）"
}}

注意事项：
1. 摘要要客观准确，突出重点
2. 关键词不超过{self.max_keywords}个
3. 如果内容不完整，请在摘要中注明
4. 保持JSON格式的规范性

请只返回JSON结果，不要其他说明文字。"""

        return prompt

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """调用Ollama API"""
        try:
            url = f"{self.base_url}/api/generate"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1000},
            }

            for attempt in range(self.max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=self.timeout)

                    if response.status_code == 200:
                        result = response.json()
                        return result.get("response", "")

                    else:
                        self.logger.warning(
                            f"Ollama调用失败 (尝试 {attempt + 1}/{self.max_retries}): {response.status_code}"
                        )
                        if attempt < self.max_retries - 1:
                            time.sleep(1)  # 等待1秒后重试

                except requests.exceptions.RequestException as e:
                    self.logger.warning(
                        f"Ollama请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(2)  # 等待2秒后重试

            return None

        except Exception as e:
            self.logger.error(f"Ollama调用错误: {e}")
            return None

    def _parse_response(self, response: str, original_content: str) -> Dict[str, Any]:
        """解析Ollama响应"""
        try:
            # 尝试提取JSON
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

                parsed = json.loads(json_str)

                # 验证和标准化结果
                result = {
                    "document_type": parsed.get("document_type", "未知"),
                    "main_topic": parsed.get("main_topic", "无主题"),
                    "summary": parsed.get(
                        "summary", self._generate_simple_summary(original_content)
                    ),
                    "key_points": parsed.get("key_points", []),
                    "keywords": parsed.get("keywords", [])[: self.max_keywords],
                    "sentiment": parsed.get("sentiment", "中性"),
                    "complexity": parsed.get("complexity", "中等"),
                    "language": parsed.get("language", "中文"),
                    "confidence": float(parsed.get("confidence", 0.7)),
                }

                return result

        except Exception as e:
            self.logger.warning(f"Ollama响应解析失败: {e}")

        # 解析失败时的回退
        return {
            "document_type": "未知",
            "main_topic": "内容解析失败",
            "summary": self._generate_simple_summary(original_content),
            "key_points": [],
            "keywords": [],
            "sentiment": "中性",
            "complexity": "未知",
            "language": "未知",
            "confidence": 0.3,
        }

    def _generate_simple_summary(self, content: str) -> str:
        """生成简单摘要（作为Ollama失败时的后备）"""
        try:
            # 简单的文本摘要逻辑
            sentences = content.split("。")
            if len(sentences) > 2:
                summary = "。".join(sentences[:2]) + "。"
            else:
                summary = content[:200] + ("..." if len(content) > 200 else "")

            return summary

        except Exception:
            return "内容摘要生成失败"

    def _fallback_result(self, raw_content: str) -> Dict[str, Any]:
        """Ollama失败时的后备结果"""
        return {
            "original_content": raw_content,
            "enhanced_content": {
                "document_type": "未知",
                "main_topic": "Ollama处理失败",
                "summary": self._generate_simple_summary(raw_content),
                "key_points": [],
                "keywords": [],
                "sentiment": "未知",
                "complexity": "未知",
                "language": "未知",
                "confidence": 0.0,
            },
            "ollama_processed": False,
            "model_used": self.model,
            "processing_time": time.time(),
        }

    def extract_document_insights(self, content: str) -> Dict[str, Any]:
        """提取文档洞察信息"""
        try:
            prompt = f"""请分析以下文档内容，提取关键洞察信息：

{content[:1500]}...

请返回JSON格式：
{{
    "entities": ["实体1", "实体2"],
    "relationships": ["关系1", "关系2"],
    "action_items": ["行动项1", "行动项2"],
    "important_dates": ["日期1", "日期2"],
    "numbers_and_amounts": ["数字1", "数字2"]
}}"""

            response = self._call_ollama(prompt)
            if response:
                return self._parse_insights_response(response)
            else:
                return {
                    "entities": [],
                    "relationships": [],
                    "action_items": [],
                    "important_dates": [],
                    "numbers_and_amounts": [],
                }

        except Exception as e:
            self.logger.error(f"文档洞察提取失败: {e}")
            return {}

    def _parse_insights_response(self, response: str) -> Dict[str, Any]:
        """解析洞察响应"""
        try:
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

                parsed = json.loads(json_str)
                return {
                    "entities": parsed.get("entities", []),
                    "relationships": parsed.get("relationships", []),
                    "action_items": parsed.get("action_items", []),
                    "important_dates": parsed.get("important_dates", []),
                    "numbers_and_amounts": parsed.get("numbers_and_amounts", []),
                }

        except Exception as e:
            self.logger.warning(f"洞察响应解析失败: {e}")

        return {
            "entities": [],
            "relationships": [],
            "action_items": [],
            "important_dates": [],
            "numbers_and_amounts": [],
        }

    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            else:
                return []

        except Exception as e:
            self.logger.error(f"获取模型列表失败: {e}")
            return []

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "available": self.is_available(),
            "available_models": self.get_available_models(),
            "features": {
                "summary": self.enable_summary,
                "keywords": self.enable_keywords,
                "insights": True,
            },
        }
