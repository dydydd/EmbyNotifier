#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emby 数据解析模块
"""

from typing import Dict, Any, Optional
from utils import format_size, extract_quality_from_filename


class EmbyDataParser:
    """Emby webhook 数据解析器"""
    
    @staticmethod
    def parse(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Emby webhook 数据并转换为模板变量
        
        Args:
            data: Emby webhook 原始数据
        
        Returns:
            模板变量字典
        """
        # 处理数组格式（模板文件格式）或单个对象格式
        items = EmbyDataParser._extract_items(data)
        
        if not items:
            return {}
        
        # 取第一个项目（通常 webhook 只发送一个）
        item_data = items[0]
        
        # 提取 Item 对象
        item = item_data.get('Item', {})
        server = item_data.get('Server', {})
        
        # 媒体类型
        item_type = item.get('Type', '')
        is_episode = item_type == 'Episode'
        
        # 基本信息
        # 对于剧集，使用 SeriesName；对于电影，使用 Name
        if is_episode:
            series_name = item.get('SeriesName', '')
            episode_name = item.get('Name', '')
            
            # 优先使用 SeriesName，如果为空则使用 Name
            name = series_name or episode_name
            
            # 如果只有单集名称（通常以"第"、"Episode"等开头），记录警告
            if not series_name and episode_name:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"剧集缺少 SeriesName，仅使用 Name: {episode_name}")
        else:
            name = item.get('Name', '')
        
        production_year = item.get('ProductionYear', 0)
        
        # 对于剧集，如果名称看起来像是单集名称（如"第1集"、"Episode 2"），不添加年份
        # 因为这说明 SeriesName 缺失，添加年份会很奇怪
        is_episode_name_only = False
        if is_episode and name:
            # 检查是否是纯集名称（以"第"开头、或"Episode"开头、或纯数字）
            import re
            if re.match(r'^(第\s*\d+\s*集|Episode\s+\d+|\d+)$', name.strip(), re.IGNORECASE):
                is_episode_name_only = True
        
        # 如果名称中已经包含年份（格式如 "剧名 (YYYY)"），则不重复添加
        # 如果是纯集名称，也不添加年份
        if production_year and not is_episode_name_only and not (f"({production_year})" in name or f"（{production_year}）" in name):
            title_year = f"{name} ({production_year})"
        else:
            title_year = name
        
        # 剧集信息
        season_episode, season_fmt = EmbyDataParser._extract_season_info(item, is_episode)
        
        # Provider IDs
        provider_ids = item.get('ProviderIds', {})
        tmdb_id = provider_ids.get('Tmdb') or provider_ids.get('MovieDb')
        imdb_id = provider_ids.get('Imdb')
        douban_id = None  # Emby 通常不提供豆瓣 ID
        
        # 评分
        vote_average = EmbyDataParser._extract_rating(item)
        
        # 类型/分类
        genres = item.get('Genres', [])
        category = ' / '.join(genres) if genres else None
        
        # 文件信息
        filename = item.get('FileName', '')
        file_path = item.get('Path', '')
        resource_quality = extract_quality_from_filename(filename) or extract_quality_from_filename(file_path)
        
        # 视频尺寸
        video_width = item.get('Width', 0)
        video_height = item.get('Height', 0)
        
        # 文件大小
        file_size = item.get('Size', 0)
        total_size = format_size(file_size) if file_size else None
        
        # 文件数量（单个文件）
        file_count = 1
        
        # 简介
        overview = item.get('Overview') or item_data.get('Description', '')
        
        # 图片信息
        image_tags = item.get('ImageTags', {})
        primary_image_tag = image_tags.get('Primary')
        item_id = item.get('Id')
        series_id_for_image = item.get('SeriesId') if is_episode else None
        
        # 构建模板变量字典
        template_vars = {
            'title_year': title_year,
            'season_episode': season_episode,
            'season_fmt': season_fmt,
            'tmdbid': tmdb_id,
            'tmdb_id': tmdb_id,
            'imdbid': imdb_id,
            'imdb_id': imdb_id,
            'doubanid': douban_id,
            'douban_id': douban_id,
            'media_type': 'tv' if is_episode else 'movie',
            'type': item_type.lower(),
            'tmdb_type': 'tv' if is_episode else 'movie',
            'tmdb_media_type': 'tv' if is_episode else 'movie',
            'vote_average': vote_average,
            'category': category,
            'resource_term': resource_quality,
            'resource_quality': resource_quality,
            'video_width': video_width,
            'video_height': video_height,
            'file_count': file_count,
            'total_size': total_size,
            'overview': overview,
            'overview_source': 'emby',  # 标记简介来源
            'item_id': item_id,
            'primary_image_tag': primary_image_tag,
            'series_id': series_id_for_image,
        }
        
        return template_vars
    
    @staticmethod
    def _extract_items(data: Dict[str, Any]) -> list:
        """从数据中提取项目列表"""
        if 'tv' in data:
            return data['tv']
        elif 'mv' in data:
            return data['mv']
        elif isinstance(data, list):
            return data
        else:
            # 单个对象格式
            return [data]
    
    @staticmethod
    def _extract_season_info(item: Dict[str, Any], is_episode: bool) -> tuple[Optional[str], Optional[str]]:
        """提取剧集信息"""
        season_episode = None
        season_fmt = None
        
        if is_episode:
            index_number = item.get('IndexNumber')
            parent_index_number = item.get('ParentIndexNumber')
            if index_number is not None and parent_index_number is not None:
                season_episode = f"S{parent_index_number:02d}E{index_number:02d}"
            season_name = item.get('SeasonName', '')
            if season_name:
                season_fmt = season_name
        
        return season_episode, season_fmt
    
    @staticmethod
    def _extract_rating(item: Dict[str, Any]) -> Optional[float]:
        """提取评分"""
        community_rating = item.get('CommunityRating')
        critic_rating = item.get('CriticRating')
        return community_rating or (critic_rating / 10 if critic_rating else None)
    
    @staticmethod
    def get_event(data: Dict[str, Any]) -> Optional[str]:
        """
        从数据中提取事件类型
        
        Args:
            data: Emby webhook 原始数据
        
        Returns:
            事件类型，如 'library.new'
        """
        if isinstance(data, dict):
            if 'Event' in data:
                return data['Event']
            elif 'tv' in data and len(data['tv']) > 0:
                return data['tv'][0].get('Event')
            elif 'mv' in data and len(data['mv']) > 0:
                return data['mv'][0].get('Event')
        return None

