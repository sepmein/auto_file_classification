"""
文本工具函数

提供文本处理相关的工具函数
"""

import re
from typing import List, Optional, Dict, Any
from collections import Counter


def clean_text(text: str, remove_html: bool = True, remove_urls: bool = True) -> str:
    """清理文本内容"""
    if not text:
        return ""

    # 移除HTML标签
    if remove_html:
        text = re.sub(r"<[^>]+>", "", text)

    # 移除URL
    if remove_urls:
        text = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )

    # 移除多余的空白字符
    text = re.sub(r"\s+", " ", text)

    # 移除特殊字符，但保留中文标点
    text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？；：""' "（）【】]", "", text)

    return text.strip()


def extract_keywords(text: str, top_k: int = 10, min_length: int = 2) -> List[str]:
    """提取关键词"""
    if not text:
        return []

    # 清理文本
    text = clean_text(text)

    # 分词（简单按空格分割，中文按字符分割）
    words = []
    for word in text.split():
        if len(word) >= min_length:
            # 处理中文
            if re.search(r"[\u4e00-\u9fff]", word):
                # 对于中文，尝试按词分割而不是按字符
                if len(word) >= 4:  # 长词按字符分割
                    words.extend([word[i : i + 2] for i in range(0, len(word), 2)])
                else:
                    words.append(word)
            else:
                words.append(word)

    # 统计词频
    word_counts = Counter(words)

    # 返回top_k个关键词
    return [word for word, _ in word_counts.most_common(top_k)]


def generate_summary(text: str, max_length: int = 200) -> str:
    """生成文本摘要"""
    if not text:
        return ""

    # 清理文本
    text = clean_text(text)

    # 如果文本长度小于等于最大长度，直接返回
    if len(text) <= max_length:
        return text

    # 按句子分割
    sentences = re.split(r"[。！？.!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 选择前几个句子，直到达到最大长度
    summary = ""
    for sentence in sentences:
        if len(summary + sentence) <= max_length:
            summary += sentence + "。"
        else:
            break

    # 如果没有生成摘要，返回前max_length个字符
    if not summary:
        summary = text[:max_length]
        if len(text) > max_length:
            summary += "..."

    return summary.strip()


def normalize_text(text: str) -> str:
    """标准化文本"""
    if not text:
        return ""

    # 转换为小写（英文）
    text = text.lower()

    # 标准化空白字符
    text = re.sub(r"\s+", " ", text)

    # 标准化标点符号
    text = re.sub(r'[，。！？；：""' "（）【】]", "", text)

    return text.strip()


def remove_stopwords(text: str, stopwords: List[str] | None = None) -> str:
    """移除停用词"""
    if not text:
        return ""

    if stopwords is None:
        # 默认停用词列表
        stopwords = [
            "的",
            "了",
            "在",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
        ]

    # 分词
    words = text.split()

    # 过滤停用词
    filtered_words = [word for word in words if word not in stopwords]

    return " ".join(filtered_words)


def split_text_into_chunks(
    text: str, chunk_size: int = 1000, overlap: int = 100
) -> List[str]:
    """将文本分割成块"""
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # 如果不是最后一块，尝试在句子边界分割
        if end < len(text):
            # 寻找最近的句子结束位置
            for i in range(end, max(start + chunk_size - 200, start), -1):
                if text[i] in "。！？.!?":
                    end = i + 1
                    break

        chunks.append(text[start:end])
        start = end - overlap

        # 避免无限循环
        if start >= len(text):
            break

    return chunks


def count_words(text: str) -> int:
    """统计词数"""
    if not text:
        return 0

    # 清理文本
    text = clean_text(text)

    # 分词（中文按字符，英文按空格）
    words = []
    for word in text.split():
        if re.search(r"[\u4e00-\u9fff]", word):
            # 中文按字符计算
            words.extend(list(word))
        else:
            # 英文按单词计算
            words.append(word)

    return len(words)


def count_characters(text: str, include_spaces: bool = True) -> int:
    """统计字符数"""
    if not text:
        return 0

    if include_spaces:
        return len(text)
    else:
        return len(text.replace(" ", ""))


def get_text_statistics(text: str) -> Dict[str, Any]:
    """获取文本统计信息"""
    if not text:
        return {
            "characters": 0,
            "characters_no_spaces": 0,
            "words": 0,
            "sentences": 0,
            "paragraphs": 0,
            "keywords": [],
        }

    # 清理文本
    cleaned_text = clean_text(text)

    # 统计信息
    stats = {
        "characters": count_characters(text, include_spaces=True),
        "characters_no_spaces": count_characters(text, include_spaces=False),
        "words": count_words(cleaned_text),
        "sentences": len(re.split(r"[。！？.!?]", text)),
        "paragraphs": len([p for p in text.split("\n") if p.strip()]),
        "keywords": extract_keywords(cleaned_text, top_k=5),
    }

    return stats


def find_text_patterns(text: str, patterns: List[str]) -> Dict[str, List[str]]:
    """查找文本中的模式"""
    if not text or not patterns:
        return {}

    results = {}

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            results[pattern] = matches

    return results


def replace_text_patterns(text: str, replacements: Dict[str, str]) -> str:
    """替换文本中的模式"""
    if not text or not replacements:
        return text

    result = text

    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
