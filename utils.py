#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import re
import logging
from typing import Optional, Tuple
from urllib.parse import quote
import requests

logger = logging.getLogger(__name__)


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


def find_tmdb_id(imdb_id: Optional[str] = None, 
                 title: Optional[str] = None, 
                 year: Optional[int] = None,
                 media_type: str = 'movie',
                 api_key: Optional[str] = None) -> Optional[int]:
    """
    通过 TMDB API 查找 TMDB ID
    
    优先使用 IMDb ID 查找，如果没有则使用标题和年份搜索
    
    Args:
        imdb_id: IMDb ID（如 "tt1234567"）
        title: 标题
        year: 年份
        media_type: 媒体类型，'movie' 或 'tv'
        api_key: TMDB API Key（可选）
    
    Returns:
        TMDB ID，如果找不到则返回 None
    """
    try:
        # 方法1：通过 IMDb ID 查找（最准确）
        if imdb_id:
            try:
                if api_key:
                    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={api_key}&external_source=imdb_id"
                else:
                    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}?external_source=imdb_id"
                
                response = requests.get(find_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # 查找结果可能在 'movie_results' 或 'tv_results' 中
                    results = data.get(f'{media_type}_results', [])
                    if results and len(results) > 0:
                        tmdb_id = results[0].get('id')
                        if tmdb_id:
                            logger.info(f"通过 IMDb ID {imdb_id} 找到 TMDB ID: {tmdb_id}")
                            return tmdb_id
            except Exception as e:
                logger.debug(f"通过 IMDb ID 查找失败: {e}")
        
        # 方法2：通过标题和年份搜索
        if title and year:
            try:
                search_type = 'movie' if media_type == 'movie' else 'tv'
                if api_key:
                    search_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={api_key}&query={quote(title)}&year={year}&language=zh-CN"
                else:
                    search_url = f"https://api.themoviedb.org/3/search/{search_type}?query={quote(title)}&year={year}&language=zh-CN"
                
                response = requests.get(search_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    if results and len(results) > 0:
                        # 取第一个结果（通常是最匹配的）
                        tmdb_id = results[0].get('id')
                        if tmdb_id:
                            logger.info(f"通过标题 '{title}' ({year}) 找到 TMDB ID: {tmdb_id}")
                            return tmdb_id
            except Exception as e:
                logger.debug(f"通过标题搜索查找失败: {e}")
        
        # 方法3：仅通过标题搜索（没有年份）
        if title and not year:
            try:
                search_type = 'movie' if media_type == 'movie' else 'tv'
                if api_key:
                    search_url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={api_key}&query={quote(title)}&language=zh-CN"
                else:
                    search_url = f"https://api.themoviedb.org/3/search/{search_type}?query={quote(title)}&language=zh-CN"
                
                response = requests.get(search_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    if results and len(results) > 0:
                        tmdb_id = results[0].get('id')
                        if tmdb_id:
                            logger.info(f"通过标题 '{title}' 找到 TMDB ID: {tmdb_id}")
                            return tmdb_id
            except Exception as e:
                logger.debug(f"通过标题搜索查找失败: {e}")
    
    except Exception as e:
        logger.warning(f"查找 TMDB ID 时出错: {e}")
    
    return None

