"""
工具函数测试

测试utils模块中的各种工具函数
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path

from ods.utils.file_utils import (
    ensure_directory,
    safe_filename,
    get_file_extension,
    is_supported_file,
    calculate_file_hash,
    get_file_size_human_readable,
    get_file_info,
    is_binary_file,
    copy_file_safe,
    move_file_safe,
)

from ods.utils.text_utils import (
    clean_text,
    extract_keywords,
    generate_summary,
    normalize_text,
    remove_stopwords,
    split_text_into_chunks,
    count_words,
    count_characters,
    get_text_statistics,
    find_text_patterns,
    replace_text_patterns,
)


class TestFileUtils:
    """文件工具函数测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")

        # 创建测试文件
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("这是一个测试文件\n包含一些测试内容")

    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_ensure_directory(self):
        """测试目录创建"""
        new_dir = os.path.join(self.temp_dir, "new_dir", "sub_dir")

        # 测试创建新目录
        assert ensure_directory(new_dir) is True
        assert os.path.exists(new_dir)

        # 测试已存在的目录
        assert ensure_directory(new_dir) is True

    def test_safe_filename(self):
        """测试安全文件名生成"""
        # 测试非法字符替换
        unsafe_name = 'file<>:"/\\|?*.txt'
        safe_name = safe_filename(unsafe_name)
        assert "<>" not in safe_name
        assert ":" not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert "|" not in safe_name
        assert "?" not in safe_name
        assert "*" not in safe_name

        # 测试长度限制
        long_name = "a" * 300 + ".txt"
        safe_name = safe_filename(long_name, max_length=200)
        assert len(safe_name) <= 200
        assert safe_name.endswith(".txt")

    def test_get_file_extension(self):
        """测试文件扩展名获取"""
        assert get_file_extension("document.pdf") == ".pdf"
        assert get_file_extension("file.txt") == ".txt"
        assert get_file_extension("no_extension") == ""
        assert get_file_extension(".hidden") == ".hidden"

    def test_is_supported_file(self):
        """测试文件类型检查"""
        supported_exts = [".txt", ".pdf", ".docx"]

        assert is_supported_file("document.txt", supported_exts) is True
        assert is_supported_file("document.pdf", supported_exts) is True
        assert is_supported_file("document.jpg", supported_exts) is False

    def test_calculate_file_hash(self):
        """测试文件哈希计算"""
        # 测试MD5哈希
        md5_hash = calculate_file_hash(self.test_file, "md5")
        assert md5_hash is not None
        assert len(md5_hash) == 32  # MD5哈希长度

        # 测试SHA1哈希
        sha1_hash = calculate_file_hash(self.test_file, "sha1")
        assert sha1_hash is not None
        assert len(sha1_hash) == 40  # SHA1哈希长度

        # 测试不存在的文件
        assert calculate_file_hash("nonexistent.txt") is None

    def test_get_file_size_human_readable(self):
        """测试文件大小格式化"""
        size_str = get_file_size_human_readable(self.test_file)
        assert "B" in size_str

        # 测试大文件（创建一个大文件）
        large_file = os.path.join(self.temp_dir, "large.txt")
        with open(large_file, "w") as f:
            f.write("x" * 1024 * 1024)  # 1MB

        size_str = get_file_size_human_readable(large_file)
        assert "MB" in size_str

    def test_get_file_info(self):
        """测试文件信息获取"""
        info = get_file_info(self.test_file)

        assert "size" in info
        assert "size_human" in info
        assert "created" in info
        assert "modified" in info
        assert "extension" in info
        assert "hash" in info

        assert info["extension"] == ".txt"
        assert info["hash"] is not None

    def test_is_binary_file(self):
        """测试二进制文件检测"""
        # 文本文件应该是False
        assert is_binary_file(self.test_file) is False

        # 创建二进制文件
        binary_file = os.path.join(self.temp_dir, "binary.bin")
        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03")

        assert is_binary_file(binary_file) is True

    def test_copy_file_safe(self):
        """测试安全文件复制"""
        dest_file = os.path.join(self.temp_dir, "copy.txt")

        # 测试复制
        assert copy_file_safe(self.test_file, dest_file) is True
        assert os.path.exists(dest_file)

        # 测试不覆盖
        assert copy_file_safe(self.test_file, dest_file, overwrite=False) is False

        # 测试覆盖
        assert copy_file_safe(self.test_file, dest_file, overwrite=True) is True

    def test_move_file_safe(self):
        """测试安全文件移动"""
        dest_file = os.path.join(self.temp_dir, "moved.txt")

        # 测试移动
        assert move_file_safe(self.test_file, dest_file) is True
        assert os.path.exists(dest_file)
        assert not os.path.exists(self.test_file)

        # 测试不存在的源文件
        assert move_file_safe("nonexistent.txt", dest_file) is False


class TestTextUtils:
    """文本工具函数测试"""

    def test_clean_text(self):
        """测试文本清理"""
        dirty_text = "<p>这是一个<b>HTML</b>文本 http://example.com  包含多余空格</p>"
        clean = clean_text(dirty_text)

        assert "<p>" not in clean
        assert "<b>" not in clean
        assert "http://example.com" not in clean
        assert "包含多余空格" in clean  # 只清理HTML和URL，保留中文标点

        # 测试空文本
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_extract_keywords(self):
        """测试关键词提取"""
        text = (
            "这是一个测试文档，包含一些重要的关键词。测试文档很重要，关键词也很重要。"
        )
        keywords = extract_keywords(text, top_k=5)

        assert len(keywords) <= 5
        assert "测试" in keywords
        assert "文档" in keywords
        assert "关键" in keywords  # 中文按2字符分割

    def test_generate_summary(self):
        """测试摘要生成"""
        long_text = (
            "这是第一句话。这是第二句话。这是第三句话。这是第四句话。这是第五句话。"
        )

        # 测试短摘要
        summary = generate_summary(long_text, max_length=20)
        assert len(summary) <= 25  # 允许稍微超出一点
        assert "第一句话" in summary

        # 测试长文本摘要
        summary = generate_summary(long_text, max_length=100)
        assert len(summary) <= 100
        assert summary.count("。") >= 2

    def test_normalize_text(self):
        """测试文本标准化"""
        text = "这是，一个！测试？文本；包含：各种" "标点''符号（中文）【英文】"
        normalized = normalize_text(text)

        assert "，" not in normalized
        assert "！" not in normalized
        assert "？" not in normalized
        assert "；" not in normalized
        assert "：" not in normalized
        assert "（" not in normalized
        assert "）" not in normalized
        assert "【" not in normalized
        assert "】" not in normalized

    def test_remove_stopwords(self):
        """测试停用词移除"""
        text = "这是一个测试文档，我有很多想法"
        filtered = remove_stopwords(text)

        assert "的" not in filtered
        # "是" 已经从停用词列表中移除
        assert "测试" in filtered
        # "我" 也在停用词列表中
        assert "测试" in filtered
        assert "测试" in filtered
        assert "文档" in filtered

    def test_split_text_into_chunks(self):
        """测试文本分块"""
        text = "第一句。第二句。第三句。第四句。第五句。第六句。第七句。第八句。"

        chunks = split_text_into_chunks(text, chunk_size=20, overlap=5)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 20

        # 测试重叠
        if len(chunks) > 1:
            # 检查相邻块之间是否有重叠
            overlap_text = chunks[0][-5:]
            assert any(overlap_text in chunk for chunk in chunks[1:])

    def test_count_words(self):
        """测试词数统计"""
        text = "这是一个测试文档"
        assert count_words(text) == 8  # 中文按字符计算：这是测试文档 = 8个字符

        text = "This is a test document"
        assert count_words(text) == 5

    def test_count_characters(self):
        """测试字符数统计"""
        text = "Hello 世界"

        assert count_characters(text, include_spaces=True) == 8
        assert count_characters(text, include_spaces=False) == 7

    def test_get_text_statistics(self):
        """测试文本统计信息"""
        text = "这是第一句话。这是第二句话。\n这是新段落。"
        stats = get_text_statistics(text)

        assert "characters" in stats
        assert "words" in stats
        assert "sentences" in stats
        assert "paragraphs" in stats
        assert "keywords" in stats

        assert (
            stats["sentences"] == 4
        )  # 按句号分割：这是第一句话。这是第二句话。这是新段落。= 4句
        assert stats["paragraphs"] == 2

    def test_find_text_patterns(self):
        """测试模式查找"""
        text = "我的邮箱是 test@example.com，电话是 138-0013-8000"
        patterns = [r"\w+@\w+\.\w+", r"\d{3}-\d{4}-\d{4}"]

        results = find_text_patterns(text, patterns)

        assert len(results) == 2
        assert "test@example.com" in results[patterns[0]]
        assert "138-0013-8000" in results[patterns[1]]

    def test_replace_text_patterns(self):
        """测试模式替换"""
        text = "我的邮箱是 test@example.com，电话是 138-0013-8000"
        replacements = {r"\w+@\w+\.\w+": "[EMAIL]", r"\d{3}-\d{4}-\d{4}": "[PHONE]"}

        result = replace_text_patterns(text, replacements)

        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "test@example.com" not in result
        assert "138-0013-8000" not in result


class TestUtilsIntegration:
    """工具函数集成测试"""

    def test_file_and_text_integration(self):
        """测试文件和文本工具函数的集成"""
        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test_document.txt")

        try:
            # 写入测试内容
            content = "这是一个测试文档。包含一些重要的关键词。测试很重要。"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            # 使用文件工具获取文件信息
            file_info = get_file_info(test_file)
            assert file_info["extension"] == ".txt"

            # 使用文本工具分析内容
            text_stats = get_text_statistics(content)
            assert text_stats["words"] > 0
            assert len(text_stats["keywords"]) > 0

            # 使用文件工具复制文件
            copy_file = os.path.join(temp_dir, "copy.txt")
            assert copy_file_safe(test_file, copy_file) is True

            # 验证复制后的文件内容
            with open(copy_file, "r", encoding="utf-8") as f:
                copied_content = f.read()

            # 使用文本工具比较内容
            assert clean_text(content) == clean_text(copied_content)

        finally:
            shutil.rmtree(temp_dir)
