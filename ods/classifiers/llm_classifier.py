"""
LLM分类器模块
负责调用LLM进行智能分类决策
"""

import logging
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import openai
from openai import OpenAI
import anthropic
from anthropic import Anthropic

from .retrieval_agent import RetrievalAgent


class LLMClassifier:
    """LLM分类器 - 通过LLM进行智能分类决策"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # LLM配置
        self.llm_config = config.get("llm", {})
        self.provider = self.llm_config.get("provider", "openai")
        self.model = self.llm_config.get("model", "gpt-4")
        self.api_key = self.llm_config.get("api_key")
        self.base_url = self.llm_config.get("base_url")
        self.temperature = self.llm_config.get("temperature", 0.1)
        self.max_tokens = self.llm_config.get("max_tokens", 1000)

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

        # 初始化LLM客户端
        self.llm_client = self._setup_llm_client()

        # 检索代理
        self.retrieval_agent = RetrievalAgent(config)

        # 提示模板
        self.prompt_templates = self._load_prompt_templates()

        # 减少初始化日志冗余
        if not hasattr(LLMClassifier, "_init_logged"):
            provider_name = (
                "Ollama" if self.provider == "ollama" else self.provider.title()
            )
            self.logger.info(f"LLM分类器初始化完成 - 提供商: {provider_name}")
            LLMClassifier._init_logged = True

    def _setup_llm_client(self):
        """设置LLM客户端"""
        try:
            # For Ollama or mock environments, API key is not required
            if (
                not self.api_key
                and self.provider != "ollama"
                and "test" not in str(self.model).lower()
            ):
                self.logger.warning("未提供API密钥，LLM分类器将无法工作")
                return None

            if self.provider == "openai":
                if self.base_url:
                    client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                else:
                    client = OpenAI(api_key=self.api_key)
                self.logger.info("OpenAI客户端设置成功")
                return client

            elif self.provider == "anthropic":
                client = Anthropic(api_key=self.api_key)
                self.logger.info("Anthropic客户端设置成功")
                return client

            elif self.provider == "ollama":
                # Ollama本地部署 - 使用OpenAI兼容的API
                base_url = self.base_url or "http://localhost:11434"
                if not base_url.endswith("/v1"):
                    base_url = base_url.rstrip("/") + "/v1"

                client = OpenAI(
                    api_key="ollama",  # Ollama doesn't require a real API key
                    base_url=base_url,
                )
                self.logger.info(f"Ollama客户端设置成功，端点: {base_url}")
                return client

            else:
                raise ValueError(f"不支持的LLM提供商: {self.provider}")

        except Exception as e:
            self.logger.error(f"LLM客户端设置失败: {e}")
            return None

    def _load_prompt_templates(self) -> Dict[str, str]:
        """加载提示模板"""
        templates = {
            "classification": """你是一个专业的文件分类助手。现在有一份新文档的内容摘要，以及数个相似的已分类文档供参考，请根据语义判断新文档属于哪些类别。

已有类别及示例:
{categories_with_examples}

新文档摘要: {document_summary}

请分析新文档内容，并给出分类建议。请按以下JSON格式返回结果：

{{
    "primary_category": "主要类别",
    "secondary_categories": ["次要类别1", "次要类别2"],
    "confidence_score": 0.95,
    "reasoning": "分类理由",
    "needs_review": false,
    "suggested_tags": ["标签1", "标签2"]
}}

注意事项：
1. 主要类别必须是已有类别中的一个
2. 次要类别可以是0-2个
3. 置信度分数范围0-1，低于{review_threshold}时需要人工复核
4. 如果内容跨多个领域，可以给出多个类别
5. 推理过程要清晰明确""",
            "category_examples": """类别: {category}
示例文档:
{examples}""",
            "confidence_assessment": """请评估以下分类结果的置信度，并给出是否需要人工复核的建议。

文档摘要: {document_summary}
分类结果: {classification_result}
相似文档: {similar_docs}

请返回JSON格式：
{{
    "confidence_score": 0.85,
    "needs_review": false,
    "review_reason": "分类理由充分，置信度较高",
    "suggested_improvements": ["可以考虑添加更多标签"]
}}""",
        }

        return templates

    def classify_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """分类文档"""
        try:
            if not self.llm_client:
                return self._fallback_classification(document_data)

            # 获取文档信息
            document_summary = document_data.get("summary", "")
            document_embedding = document_data.get("embedding")
            file_path = document_data.get("file_path", "")
            text_content = document_data.get("text_content", "")

            # 如果没有摘要，尝试生成一个简单的摘要
            if not document_summary and text_content:
                # 使用文本的前200个字符作为简单摘要
                document_summary = text_content[:200].replace("\n", " ").strip()
                if len(text_content) > 200:
                    document_summary += "..."
                self.logger.info(f"为文档生成简单摘要: {len(document_summary)} 字符")

            if not document_summary:
                self.logger.warning("文档摘要为空，无法进行分类")
                return self._create_uncategorized_result("文档摘要为空")

            # 检索相似文档
            similar_docs = []
            if document_embedding is not None:
                similar_docs = self.retrieval_agent.search_similar_documents(
                    document_embedding, top_k=5
                )

            # 获取类别示例
            categories_with_examples = self._get_categories_with_examples()

            # 构建提示
            prompt = self.prompt_templates["classification"].format(
                categories_with_examples=categories_with_examples,
                document_summary=document_summary,
                review_threshold=self.review_threshold,
            )

            # 调用LLM
            llm_response = self._call_llm(prompt)

            # 解析响应
            classification_result = self._parse_llm_response(llm_response)

            # 后处理
            final_result = self._post_process_classification(
                classification_result, document_data, similar_docs
            )

            # 记录分类结果
            self._log_classification_result(file_path, final_result)

            return final_result

        except Exception as e:
            self.logger.error(f"文档分类失败: {e}")
            return self._create_error_result(str(e))

    def _get_categories_with_examples(self) -> str:
        """获取类别及其示例"""
        categories_text = []

        for category in self.categories:
            examples = self.retrieval_agent.get_category_examples(category, top_k=2)

            if examples:
                examples_text = []
                for example in examples:
                    summary = example.get("text_chunk", "")[:200]
                    examples_text.append(f"- {summary}...")

                category_text = self.prompt_templates["category_examples"].format(
                    category=category, examples="\n".join(examples_text)
                )
            else:
                category_text = f"类别: {category}\n示例: 暂无示例文档"

            categories_text.append(category_text)

        return "\n\n".join(categories_text)

    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            if self.provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content

            elif self.provider == "anthropic":
                response = self.llm_client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text

            elif self.provider == "ollama":
                # Ollama使用不同的API格式
                try:
                    # 首先尝试OpenAI兼容格式
                    response = self.llm_client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    return response.choices[0].message.content
                except AttributeError:
                    # 如果不支持chat.completions，尝试直接调用
                    response = self.llm_client.generate(
                        model=self.model,
                        prompt=prompt,
                        options={
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                        },
                    )
                    return response.response

            else:
                raise ValueError(f"不支持的提供商: {self.provider}")

        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)

                # 验证必要字段
                required_fields = ["primary_category", "confidence_score"]
                for field in required_fields:
                    if field not in result:
                        result[field] = self._get_default_value(field)

                return result
            else:
                # 如果无法解析JSON，使用正则表达式提取信息
                return self._extract_info_from_text(response)

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}，尝试文本提取")
            return self._extract_info_from_text(response)
        except Exception as e:
            self.logger.error(f"响应解析失败: {e}")
            return self._get_default_classification()

    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取分类信息"""
        result = self._get_default_classification()

        # 尝试提取主要类别
        for category in self.categories:
            if category in text:
                result["primary_category"] = category
                break

        # 尝试提取置信度
        confidence_match = re.search(r"置信度[：:]\s*(\d+\.?\d*)", text)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                if 0 <= confidence <= 1:
                    result["confidence_score"] = confidence
            except ValueError:
                pass

        # 尝试提取推理
        reasoning_match = re.search(r"推理[：:]\s*(.+)", text)
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1).strip()

        return result

    def _post_process_classification(
        self,
        classification_result: Dict[str, Any],
        document_data: Dict[str, Any],
        similar_docs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """后处理分类结果"""
        try:
            # 确保主要类别在预定义类别中
            primary_category = classification_result.get("primary_category", "")
            if primary_category not in self.categories:
                # 尝试找到最相似的类别
                primary_category = self._find_most_similar_category(primary_category)
                classification_result["primary_category"] = primary_category

            # 验证次要类别
            secondary_categories = classification_result.get("secondary_categories", [])
            valid_secondary = [
                cat for cat in secondary_categories if cat in self.categories
            ]
            classification_result["secondary_categories"] = valid_secondary[
                : self.max_tags - 1
            ]

            # 计算最终置信度
            confidence_score = classification_result.get("confidence_score", 0.5)
            classification_result["confidence_score"] = max(
                0.0, min(1.0, confidence_score)
            )

            # 判断是否需要复核
            needs_review = confidence_score < self.review_threshold
            classification_result["needs_review"] = needs_review

            # 如果置信度太低，标记为未分类
            if confidence_score < self.confidence_threshold:
                classification_result["primary_category"] = "Uncategorized"
                classification_result["secondary_categories"] = []
                classification_result["needs_review"] = True

            # 添加元数据
            classification_result["similar_documents_count"] = len(similar_docs)
            classification_result["classification_timestamp"] = time.time()
            classification_result["model_used"] = self.model
            classification_result["provider"] = self.provider

            return classification_result

        except Exception as e:
            self.logger.error(f"后处理失败: {e}")
            return self._get_default_classification()

    def _find_most_similar_category(self, suggested_category: str) -> str:
        """找到最相似的预定义类别"""
        # 简单的字符串相似度匹配
        best_match = self.categories[0]
        best_score = 0

        for category in self.categories:
            # 计算简单的相似度（共同字符数）
            common_chars = len(set(suggested_category) & set(category))
            score = common_chars / max(len(suggested_category), len(category))

            if score > best_score:
                best_score = score
                best_match = category

        return best_match

    def _get_default_classification(self) -> Dict[str, Any]:
        """获取默认分类结果"""
        return {
            "primary_category": "Uncategorized",
            "secondary_categories": [],
            "confidence_score": 0.0,
            "reasoning": "无法确定分类",
            "needs_review": True,
            "suggested_tags": [],
            "similar_documents_count": 0,
            "classification_timestamp": time.time(),
            "model_used": self.model,
            "provider": self.provider,
        }

    def _get_default_value(self, field: str) -> Any:
        """获取字段的默认值"""
        defaults = {
            "primary_category": "Uncategorized",
            "secondary_categories": [],
            "confidence_score": 0.5,
            "reasoning": "LLM分类结果",
            "needs_review": False,
            "suggested_tags": [],
        }
        return defaults.get(field, "")

    def _fallback_classification(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """备用分类方法"""
        self.logger.info("使用备用分类方法")

        # 基于文件扩展名的简单分类
        file_path = document_data.get("file_path", "")
        file_ext = Path(file_path).suffix.lower()

        # 简单的扩展名分类规则
        ext_categories = {
            ".pdf": "文档",
            ".docx": "文档",
            ".doc": "文档",
            ".txt": "文本",
            ".md": "文本",
            ".jpg": "图片",
            ".png": "图片",
            ".xlsx": "表格",
            ".pptx": "演示",
        }

        category = ext_categories.get(file_ext, "其他")

        return {
            "primary_category": category,
            "secondary_categories": [],
            "confidence_score": 0.3,
            "reasoning": f"基于文件扩展名 {file_ext} 的简单分类",
            "needs_review": True,
            "suggested_tags": [file_ext[1:].upper()],
            "similar_documents_count": 0,
            "classification_timestamp": time.time(),
            "model_used": "fallback",
            "provider": "fallback",
        }

    def _create_uncategorized_result(self, reason: str) -> Dict[str, Any]:
        """创建未分类结果"""
        return {
            "primary_category": "Uncategorized",
            "secondary_categories": [],
            "confidence_score": 0.0,
            "reasoning": reason,
            "needs_review": True,
            "suggested_tags": [],
            "similar_documents_count": 0,
            "classification_timestamp": time.time(),
            "model_used": "none",
            "provider": "none",
        }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
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
        }

    def _log_classification_result(self, file_path: str, result: Dict[str, Any]):
        """记录分类结果"""
        self.logger.info(f"文档 {file_path} 分类完成:")
        self.logger.info(f"  主要类别: {result.get('primary_category')}")
        self.logger.info(f"  置信度: {result.get('confidence_score')}")
        self.logger.info(f"  需要复核: {result.get('needs_review')}")

        if result.get("secondary_categories"):
            self.logger.info(f"  次要类别: {', '.join(result['secondary_categories'])}")

    def test_connection(self) -> bool:
        """测试LLM连接"""
        try:
            if not self.llm_client:
                return False

            test_prompt = "请回复'连接测试成功'"
            response = self._call_llm(test_prompt)

            if "连接测试成功" in response or "success" in response.lower():
                self.logger.info("LLM连接测试成功")
                return True
            else:
                self.logger.warning("LLM连接测试失败：响应不符合预期")
                return False

        except Exception as e:
            self.logger.error(f"LLM连接测试失败: {e}")
            return False
