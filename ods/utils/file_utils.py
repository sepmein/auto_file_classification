"""
文件工具函数

提供文件操作相关的工具函数
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List


def ensure_directory(directory_path: str) -> bool:
    """确保目录存在，如果不存在则创建"""
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def safe_filename(filename: str, max_length: int = 200) -> str:
    """生成安全的文件名，移除或替换非法字符"""
    import re

    # 移除或替换非法字符
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # 限制长度
    if len(safe_name) > max_length:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[: max_length - len(ext)] + ext

    return safe_name


def get_file_extension(file_path: str) -> str:
    """获取文件扩展名"""
    suffix = Path(file_path).suffix
    # 处理隐藏文件（以.开头的文件）
    if file_path.startswith(".") and "." not in file_path[1:]:
        return file_path
    return suffix.lower()


def is_supported_file(file_path: str, supported_extensions: List[str]) -> bool:
    """检查文件是否为支持的类型"""
    ext = get_file_extension(file_path)
    return ext in supported_extensions


def calculate_file_hash(file_path: str, algorithm: str = "md5") -> str | None:
    """计算文件哈希值"""
    try:
        hash_func = getattr(hashlib, algorithm)()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()
    except Exception:
        return None


def get_file_size_human_readable(file_path: str) -> str:
    """获取文件大小的人类可读格式"""
    try:
        size_bytes = os.path.getsize(file_path)

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0

        return f"{size_bytes:.1f} PB"
    except Exception:
        return "Unknown"


def get_file_info(file_path: str) -> dict:
    """获取文件信息"""
    try:
        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "size_human": get_file_size_human_readable(file_path),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "extension": get_file_extension(file_path),
            "hash": calculate_file_hash(file_path),
        }
    except Exception:
        return {}


def is_binary_file(file_path: str, sample_size: int = 1024) -> bool:
    """检查文件是否为二进制文件"""
    try:
        with open(file_path, "rb") as f:
            sample = f.read(sample_size)
            return b"\x00" in sample
    except Exception:
        return False


def get_file_encoding(file_path: str) -> str | None:
    """检测文件编码"""
    try:
        import chardet

        with open(file_path, "rb") as f:
            raw_data = f.read(10000)  # 读取前10KB进行检测
            result = chardet.detect(raw_data)
            return result["encoding"]
    except ImportError:
        # 如果没有chardet库，尝试常见编码
        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read()
                return encoding
            except UnicodeDecodeError:
                continue

        return None
    except Exception:
        return None


def copy_file_safe(source: str, destination: str, overwrite: bool = False) -> bool:
    """安全地复制文件"""
    try:
        source_path = Path(source)
        dest_path = Path(destination)

        if not source_path.exists():
            return False

        if dest_path.exists() and not overwrite:
            return False

        # 确保目标目录存在
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(source_path, dest_path)
        return True
    except Exception:
        return False


def move_file_safe(source: str, destination: str, overwrite: bool = False) -> bool:
    """安全地移动文件"""
    try:
        source_path = Path(source)
        dest_path = Path(destination)

        if not source_path.exists():
            return False

        if dest_path.exists() and not overwrite:
            return False

        # 确保目标目录存在
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.move(str(source_path), str(dest_path))
        return True
    except Exception:
        return False
