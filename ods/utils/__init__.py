"""
工具函数模块

提供项目中常用的工具函数和辅助功能
"""

from .file_utils import (
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

from .text_utils import (
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

__all__ = [
    # 文件工具
    "ensure_directory",
    "safe_filename",
    "get_file_extension",
    "is_supported_file",
    "calculate_file_hash",
    "get_file_size_human_readable",
    "get_file_info",
    "is_binary_file",
    "copy_file_safe",
    "move_file_safe",
    # 文本工具
    "clean_text",
    "extract_keywords",
    "generate_summary",
    "normalize_text",
    "remove_stopwords",
    "split_text_into_chunks",
    "count_words",
    "count_characters",
    "get_text_statistics",
    "find_text_patterns",
    "replace_text_patterns",
]
