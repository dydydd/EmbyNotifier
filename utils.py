#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import re
from typing import Optional


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
    
    Returns:
        格式化后的文件大小字符串，如 "1.23 GB"
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f} {size_names[i]}"


def extract_quality_from_filename(filename: str) -> str:
    """
    从文件名提取画质信息
    
    Args:
        filename: 文件名或路径
    
    Returns:
        画质信息字符串，如 "2160p (4K) HDR"
    """
    if not filename:
        return ""
    
    filename_lower = filename.lower()
    quality_patterns = [
        (r'2160p|4k', '2160p (4K)'),
        (r'1080p', '1080p'),
        (r'720p', '720p'),
        (r'hdr(?!10)', 'HDR'),
        (r'dolby.?vision|dv', 'Dolby Vision'),
        (r'imax', 'IMAX'),
    ]
    
    found = []
    for pattern, label in quality_patterns:
        if re.search(pattern, filename_lower):
            found.append(label)
    
    return ' '.join(found)

