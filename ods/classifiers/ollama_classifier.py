"""
Ollama分类器

使用Ollama模型进行多标签文档分类
"""

import logging
import json
import requests
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time

from .enhanced_classifier import EnhancedClassifier


class OllamaClassifier:
    """Ollama分类器 - 基于本地LLM的多标签分类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Ollama配置
        self.ollama_config = config.get("ollama", {})
        self.base_url = self.ollama_config.get("base_url", "http://localhost:11434")
        self.model = self.ollama_config.get(
            "classifier_model", self.ollama_config.get("model", "qwen2.5:7b")
        )
        self.timeout = self.ollama_config.get("timeout", 120)
        self.max_retries = self.ollama_config.get("max_retries", 3)
        self.context_window = self.ollama_config.get("context_window", 4096)

        # 分类配置
        self.taxonomies = config.get("classification", {}).get("taxonomies", {})
        self.confidence_thresholds = config.get("classification", {}).get(
            "confidence_threshold", {}
        )

        # 增强分类器（用于规则处理）
        self.enhanced_classifier = EnhancedClassifier(config)

        # 减少初始化日志冗余
        if not hasattr(OllamaClassifier, "_init_logged"):
            self.logger.info(f"Ollama分类器初始化完成 - 模型: {self.model}")
            OllamaClassifier._init_logged = True

    def classify_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用Ollama进行文档分类

        Args:
            document_data: 文档数据，包含内容和元数据

        Returns:
            Dict[str, Any]: 分类结果
        """
        try:
            self.logger.info(
                f"使用Ollama分类文档: {document_data.get('file_path', '')}"
            )

            # 构建分类提示词
            prompt = self._build_classification_prompt(document_data)

            # 调用Ollama
            ollama_response = self._call_ollama(prompt)

            if not ollama_response:
                self.logger.warning("Ollama分类失败，使用增强分类器作为后备")
                return self.enhanced_classifier.classify_document(document_data)

            # 解析响应
            raw_classification = self._parse_classification_response(ollama_response)

            # 应用增强规则处理
            enhanced_result = self._apply_enhanced_rules(
                raw_classification, document_data
            )

            # 验证分类结果
            validation = self.enhanced_classifier.validate_classification_result(
                enhanced_result
            )

            if not validation["is_valid"]:
                self.logger.warning(f"分类结果验证失败: {validation['errors']}")

            return enhanced_result

        except Exception as e:
            self.logger.error(f"Ollama分类失败: {e}")
            # 回退到增强分类器
            return self.enhanced_classifier.classify_document(document_data)

    def _build_classification_prompt(self, document_data: Dict[str, Any]) -> str:
        """构建分类提示词"""
        filename = Path(document_data.get("file_path", "")).name
        content = document_data.get("text_content", "")
        ollama_content = document_data.get("ollama_content", {})

        # 构建标签体系描述
        taxonomy_descriptions = []
        for taxonomy_name, tags in self.taxonomies.items():
            taxonomy_descriptions.append(f"{taxonomy_name}: {', '.join(tags)}")

        # 使用Ollama增强内容（如果可用）
        enhanced_info = ""
        if ollama_content:
            enhanced_info = f"""
文档增强信息:
- 文档类型: {ollama_content.get('document_type', '未知')}
- 主要主题: {ollama_content.get('main_topic', '未知')}
- 情感倾向: {ollama_content.get('sentiment', '中性')}
- 复杂度: {ollama_content.get('complexity', '中等')}
- 关键词: {', '.join(ollama_content.get('keywords', []))}
"""

        # 截取内容（考虑上下文窗口限制）
        max_content_length = min(
            len(content), self.context_window // 4
        )  # 大约1/4上下文用于内容
        content_preview = content[:max_content_length]
        if len(content) > max_content_length:
            content_preview += "...(内容过长，已截断)"

        prompt = f"""你是一个专业的文档分类专家。请分析以下文档并进行多标签分类。

标签体系:
{chr(10).join(taxonomy_descriptions)}

文档信息:
- 文件名: {filename}
- 内容长度: {len(content)} 字符
{enhanced_info}

文档内容:
{content_preview}

请仔细分析文档内容，并返回JSON格式的分类结果:

{{
    "tags": ["标签1", "标签2", "标签3"],
    "confidence_scores": [0.9, 0.8, 0.7],
    "primary_tag": "主要标签",
    "reasoning": "详细的分类理由",
    "confidence_score": 0.85,
    "taxonomy_breakdown": {{
        "主类别": ["工作"],
        "文档类型": ["报告"],
        "敏感级别": ["内部"]
    }}
}}

分类要求:
1. 标签必须来自上述标签体系
2. 可以选择多个标签，但不超过5个
3. 置信度分数范围0.0-1.0
4. primary_tag应该是最重要的标签
5. reasoning要详细说明分类依据
6. taxonomy_breakdown要按标签体系分组

请只返回JSON结果，不要其他说明文字。"""

        return prompt

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """调用Ollama API进行分类"""
        try:
            url = f"{self.base_url}/api/generate"

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,  # 较低温度以提高一致性
                    "top_p": 0.9,
                    "num_predict": 1500,  # 足够的空间返回JSON
                    "repeat_penalty": 1.1,
                },
            }

            for attempt in range(self.max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=self.timeout)

                    if response.status_code == 200:
                        result = response.json()
                        return result.get("response", "")

                    else:
                        self.logger.warning(
                            f"Ollama分类调用失败 (尝试 {attempt + 1}/{self.max_retries}): {response.status_code}"
                        )
                        if attempt < self.max_retries - 1:
                            time.sleep(1)

                except requests.exceptions.RequestException as e:
                    self.logger.warning(
                        f"Ollama请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(2)

            return None

        except Exception as e:
            self.logger.error(f"Ollama调用错误: {e}")
            return None

    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """解析分类响应"""
        try:
            # 尝试提取JSON
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

                parsed = json.loads(json_str)

                # 标准化结果
                result = {
                    "tags": parsed.get("tags", []),
                    "confidence_scores": parsed.get("confidence_scores", []),
                    "primary_tag": parsed.get("primary_tag", ""),
                    "reasoning": parsed.get("reasoning", ""),
                    "confidence_score": float(parsed.get("confidence_score", 0.5)),
                    "taxonomy_breakdown": parsed.get("taxonomy_breakdown", {}),
                    "ollama_processed": True,
                }

                # 计算平均置信度（如果没有提供）
                if not result["confidence_score"] and result["confidence_scores"]:
                    result["confidence_score"] = sum(result["confidence_scores"]) / len(
                        result["confidence_scores"]
                    )

                return result

        except Exception as e:
            self.logger.warning(f"Ollama响应解析失败: {e}")

        # 解析失败时的默认返回
        return {
            "tags": [],
            "confidence_scores": [],
            "primary_tag": "",
            "reasoning": "响应解析失败",
            "confidence_score": 0.0,
            "taxonomy_breakdown": {},
            "ollama_processed": False,
        }

    def _apply_enhanced_rules(
        self, raw_result: Dict[str, Any], document_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用增强规则处理"""
        try:
            # 使用增强分类器进行规则处理
            enhanced_result = self.enhanced_classifier.apply_post_classification_rules(
                raw_result, document_data, {"pre_tags": [], "excluded": False}
            )

            # 合并Ollama特有的信息
            enhanced_result["ollama_processed"] = raw_result.get(
                "ollama_processed", False
            )
            enhanced_result["taxonomy_breakdown"] = raw_result.get(
                "taxonomy_breakdown", {}
            )

            return enhanced_result

        except Exception as e:
            self.logger.error(f"增强规则应用失败: {e}")
            return raw_result

    def batch_classify(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量分类文档"""
        results = []

        for i, doc_data in enumerate(documents):
            self.logger.info(f"批量分类进度: {i+1}/{len(documents)}")
            try:
                result = self.classify_document(doc_data)
                results.append(result)
            except Exception as e:
                self.logger.error(f"批量分类失败 (文档 {i+1}): {e}")
                results.append(
                    {
                        "status": "error",
                        "error": str(e),
                        "file_path": doc_data.get("file_path", ""),
                        "tags": [],
                        "confidence_score": 0.0,
                    }
                )

        return results

    def compare_with_enhanced(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """与增强分类器比较结果"""
        try:
            # 使用Ollama分类
            ollama_result = self.classify_document(document_data)

            # 使用增强分类器
            enhanced_result = self.enhanced_classifier.classify_document(document_data)

            return {
                "ollama_result": ollama_result,
                "enhanced_result": enhanced_result,
                "comparison": {
                    "ollama_tags": ollama_result.get("tags", []),
                    "enhanced_tags": enhanced_result.get("tags", []),
                    "ollama_confidence": ollama_result.get("confidence_score", 0),
                    "enhanced_confidence": enhanced_result.get("confidence_score", 0),
                    "ollama_primary": ollama_result.get("primary_tag", ""),
                    "enhanced_primary": enhanced_result.get("primary_tag", ""),
                    "agreement": set(ollama_result.get("tags", []))
                    == set(enhanced_result.get("tags", [])),
                },
            }

        except Exception as e:
            self.logger.error(f"分类器比较失败: {e}")
            return {"error": str(e)}

    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            url = f"{self.base_url}/api/show"
            payload = {"name": self.model}
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                model_info = response.json()
                return {
                    "model": self.model,
                    "base_url": self.base_url,
                    "available": self.is_available(),
                    "model_details": model_info,
                    "taxonomies": self.taxonomies,
                    "confidence_thresholds": self.confidence_thresholds,
                }
            else:
                return {
                    "model": self.model,
                    "base_url": self.base_url,
                    "available": False,
                    "error": f"获取模型信息失败: {response.status_code}",
                }

        except Exception as e:
            self.logger.error(f"获取模型信息失败: {e}")
            return {
                "model": self.model,
                "base_url": self.base_url,
                "available": False,
                "error": str(e),
            }

    def optimize_prompt(self, document_data: Dict[str, Any], feedback: str) -> str:
        """基于反馈优化提示词"""
        try:
            prompt = f"""请分析以下分类反馈，并优化分类提示词：

原始文档:
- 文件名: {Path(document_data.get('file_path', '')).name}
- 内容: {document_data.get('text_content', '')[:500]}...

用户反馈: {feedback}

请提供优化后的分类提示词:"""

            response = self._call_ollama(prompt)
            return response if response else "优化失败"

        except Exception as e:
            self.logger.error(f"提示词优化失败: {e}")
            return "优化失败"
