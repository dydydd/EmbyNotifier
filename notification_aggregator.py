#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知聚合器模块
用于聚合同一部剧的多集通知
"""

import logging
import re
import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from parser import EmbyDataParser
from telegram_client import TelegramClient
from templates import TemplateManager
from config import Config
from utils import find_tmdb_id
import requests

logger = logging.getLogger(__name__)


class NotificationAggregator:
    """通知聚合器
    
    聚合同一部剧的多集通知，电影直接发送不聚合
    """
    
    def __init__(self, 
                 telegram_client: TelegramClient,
                 template_manager: TemplateManager,
                 parser: EmbyDataParser,
                 aggregation_delay: int = 10):
        """
        初始化聚合器
        
        Args:
            telegram_client: Telegram 客户端
            template_manager: 模板管理器
            parser: 数据解析器
            aggregation_delay: 聚合延迟时间（秒），默认 10 秒
        """
        self.telegram_client = telegram_client
        self.template_manager = template_manager
        self.parser = parser
        self.aggregation_delay = aggregation_delay
        
        # 存储待聚合的通知
        # key: (series_id, season_id) 或 movie_id
        # value: List[template_vars]
        self.pending_notifications: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 存储定时器
        # key: (series_id, season_id) 或 movie_id
        # value: threading.Timer
        self.timers: Dict[str, threading.Timer] = {}
        
        # 锁，保护共享数据
        self.lock = threading.Lock()
    
    def add_notification(self, data: Dict[str, Any], template_vars_override: Optional[Dict[str, Any]] = None) -> bool:
        """
        添加通知到聚合队列
        
        Args:
            data: Emby webhook 数据
        
        Returns:
            是否成功添加
        """
        try:
            # 解析数据（如果提供了覆盖的 template_vars，使用它）
            if template_vars_override:
                template_vars = template_vars_override
            else:
                template_vars = self.parser.parse(data)
                if template_vars:
                    # 如果没有提供覆盖，尝试从 TMDB 获取中文简介
                    image_url, overview_zh = self._get_tmdb_info(template_vars)
                    if image_url:
                        template_vars['_tmdb_image_url'] = image_url
                    if overview_zh:
                        template_vars['overview'] = overview_zh
                        template_vars['overview_source'] = 'tmdb'
            
            if not template_vars:
                return False
            
            # 判断是电影还是剧集
            is_episode = template_vars.get('media_type') == 'tv'
            
            if is_episode:
                # 剧集：需要聚合
                return self._add_episode_notification(data, template_vars)
            else:
                # 电影：直接发送
                return self._send_movie_notification(template_vars)
        
        except Exception as e:
            logger.exception(f"添加通知时出错: {e}")
            return False
    
    def _add_episode_notification(self, 
                                   data: Dict[str, Any], 
                                   template_vars: Dict[str, Any]) -> bool:
        """添加剧集通知到聚合队列"""
        try:
            # 提取剧集和季信息
            # 使用反射调用静态方法
            items = EmbyDataParser._extract_items(data)
            if not items:
                return False
            
            item = items[0].get('Item', {})
            series_id = item.get('SeriesId')
            season_id = item.get('SeasonId')
            
            if not series_id or not season_id:
                logger.warning("无法获取 SeriesId 或 SeasonId，直接发送通知")
                return self._send_episode_notification(template_vars)
            
            # 使用 (series_id, season_id) 作为聚合键
            # 这样可以确保：
            # 1. 不同剧（不同的 series_id）不会聚合在一起
            # 2. 同一部剧的不同季（不同的 season_id）不会聚合在一起
            aggregation_key = f"{series_id}_{season_id}"
            
            logger.debug(
                f"准备聚合通知 - SeriesId: {series_id}, SeasonId: {season_id}, "
                f"聚合键: {aggregation_key}, 剧名: {template_vars.get('title_year', 'Unknown')}"
            )
            
            with self.lock:
                # 添加到待聚合列表
                self.pending_notifications[aggregation_key].append({
                    'template_vars': template_vars,
                    'data': data,
                    'timestamp': datetime.now()
                })
                
                # 如果已有定时器，取消它
                if aggregation_key in self.timers:
                    self.timers[aggregation_key].cancel()
                
                # 创建新的定时器
                timer = threading.Timer(
                    self.aggregation_delay,
                    self._send_aggregated_notification,
                    args=(aggregation_key,)
                )
                timer.start()
                self.timers[aggregation_key] = timer
                
                logger.info(f"添加剧集通知到聚合队列: {aggregation_key}, 当前队列长度: {len(self.pending_notifications[aggregation_key])}")
            
            return True
        
        except Exception as e:
            logger.exception(f"添加剧集通知时出错: {e}")
            return False
    
    def _send_movie_notification(self, template_vars: Dict[str, Any]) -> bool:
        """直接发送电影通知"""
        try:
            title, text = self.template_manager.render(template_vars)
            photo_url = self._build_image_url(template_vars)
            return self.telegram_client.send_message(title, text, photo_url=photo_url)
        except Exception as e:
            logger.exception(f"发送电影通知时出错: {e}")
            return False
    
    def _send_episode_notification(self, template_vars: Dict[str, Any]) -> bool:
        """发送单集通知（用于无法聚合的情况）"""
        try:
            title, text = self.template_manager.render(template_vars)
            photo_url = self._build_image_url(template_vars)
            return self.telegram_client.send_message(title, text, photo_url=photo_url)
        except Exception as e:
            logger.exception(f"发送剧集通知时出错: {e}")
            return False
    
    def _send_aggregated_notification(self, aggregation_key: str):
        """发送聚合通知"""
        try:
            with self.lock:
                if aggregation_key not in self.pending_notifications:
                    return
                
                notifications = self.pending_notifications.pop(aggregation_key, [])
                if aggregation_key in self.timers:
                    del self.timers[aggregation_key]
            
            if not notifications:
                return
            
            # 验证所有通知是否属于同一部剧和同一季（防御性检查）
            if not self._validate_notifications_consistency(notifications, aggregation_key):
                # 如果不一致，分别发送
                logger.warning(f"聚合键 {aggregation_key} 的通知不一致，分别发送")
                for notif in notifications:
                    template_vars = notif['template_vars']
                    title, text = self.template_manager.render(template_vars)
                    self.telegram_client.send_message(title, text)
                return
            
            # 如果只有一条，直接发送
            if len(notifications) == 1:
                template_vars = notifications[0]['template_vars']
                title, text = self.template_manager.render(template_vars)
                photo_url = self._build_image_url(template_vars)
                self.telegram_client.send_message(title, text, photo_url=photo_url)
                logger.info(f"发送单集通知: {aggregation_key}")
                return
            
            # 多条：生成聚合通知
            aggregated_title, aggregated_text = self._create_aggregated_message(notifications)
            # 使用第一条的图片
            photo_url = self._build_image_url(notifications[0]['template_vars'])
            self.telegram_client.send_message(aggregated_title, aggregated_text, photo_url=photo_url)
            
            logger.info(f"发送聚合通知: {aggregation_key}, 共 {len(notifications)} 集")
        
        except Exception as e:
            logger.exception(f"发送聚合通知时出错: {e}")
    
    def _validate_notifications_consistency(self, 
                                            notifications: List[Dict[str, Any]], 
                                            aggregation_key: str) -> bool:
        """
        验证通知的一致性（确保所有通知属于同一部剧和同一季）
        
        Args:
            notifications: 通知列表
            aggregation_key: 聚合键
        
        Returns:
            是否一致
        """
        if len(notifications) <= 1:
            return True
        
        try:
            # 提取第一条的 series_id 和 season_id
            first_data = notifications[0].get('data', {})
            first_items = EmbyDataParser._extract_items(first_data)
            if not first_items:
                return False
            
            first_item = first_items[0].get('Item', {})
            expected_series_id = first_item.get('SeriesId')
            expected_season_id = first_item.get('SeasonId')
            
            if not expected_series_id or not expected_season_id:
                return False
            
            # 验证所有通知的 series_id 和 season_id 是否一致
            for notif in notifications[1:]:
                notif_data = notif.get('data', {})
                notif_items = EmbyDataParser._extract_items(notif_data)
                if not notif_items:
                    logger.warning(f"通知数据格式异常，聚合键: {aggregation_key}")
                    return False
                
                notif_item = notif_items[0].get('Item', {})
                series_id = notif_item.get('SeriesId')
                season_id = notif_item.get('SeasonId')
                
                if series_id != expected_series_id or season_id != expected_season_id:
                    logger.error(
                        f"聚合键 {aggregation_key} 包含不同剧集的通知！"
                        f"期望: SeriesId={expected_series_id}, SeasonId={expected_season_id}, "
                        f"实际: SeriesId={series_id}, SeasonId={season_id}"
                    )
                    return False
            
            return True
        
        except Exception as e:
            logger.exception(f"验证通知一致性时出错: {e}")
            return False
    
    def _create_aggregated_message(self, notifications: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        创建聚合消息
        
        Args:
            notifications: 通知列表
        
        Returns:
            (title, text) 元组
        """
        if not notifications:
            return "", ""
        
        # 获取第一条通知作为基础信息
        first_vars = notifications[0]['template_vars']
        
        # 提取所有集数
        episodes = []
        for notif in notifications:
            season_episode = notif['template_vars'].get('season_episode')
            if season_episode:
                episodes.append(season_episode)
        
        # 排序集数
        episodes.sort()
        
        # 生成集数范围字符串
        if len(episodes) == 1:
            episode_str = episodes[0]
        else:
            # 尝试合并连续集数
            episode_ranges = self._merge_episode_ranges(episodes)
            episode_str = ', '.join(episode_ranges)
        
        # 构建标题
        title_year = first_vars.get('title_year', '')
        title = f"🎬 {title_year} {episode_str} 已入库（共 {len(notifications)} 集）"
        
        # 构建正文
        # 使用第一条的详细信息，但更新集数和文件信息
        total_size = 0
        total_files = len(notifications)
        
        # 计算总大小
        for notif in notifications:
            size_str = notif['template_vars'].get('total_size', '')
            if size_str:
                # 简单解析大小（这里可以改进）
                try:
                    size_value, size_unit = size_str.split()
                    size_value = float(size_value)
                    if size_unit == 'GB':
                        total_size += size_value * 1024 * 1024 * 1024
                    elif size_unit == 'MB':
                        total_size += size_value * 1024 * 1024
                    elif size_unit == 'KB':
                        total_size += size_value * 1024
                    else:
                        total_size += size_value
                except:
                    pass
        
        from utils import format_size
        total_size_str = format_size(int(total_size)) if total_size > 0 else None
        
        # 构建聚合消息正文
        text_parts = [
            "📢 媒体库：Emby",
        ]
        
        # 评分
        vote_average = first_vars.get('vote_average')
        if vote_average:
            text_parts.append(f"⭐️ 评分：{vote_average}/10")
        
        # 媒体类型
        text_parts.append("📺 媒体类型：剧集")
        
        # 归类
        category = first_vars.get('category')
        if category:
            text_parts.append(f"🏷 归类：{category}")
        
        # 质量（使用第一条的质量信息）
        res_label = ""
        hdr_text = ""
        # 这里可以改进，合并所有集的质量信息
        resource_quality = first_vars.get('resource_quality', '')
        video_width = first_vars.get('video_width', 0)
        video_height = first_vars.get('video_height', 0)
        
        if video_width >= 3800 or video_height >= 2000:
            res_label = '2160p (4K)'
        elif video_width >= 1900 or video_height >= 1000:
            res_label = '1080p'
        elif video_width >= 1200 or video_height >= 700:
            res_label = '720p'
        
        if resource_quality:
            rq_lower = resource_quality.lower()
            hdrs = []
            if 'hdr' in rq_lower and 'dv' not in rq_lower:
                hdrs.append('HDR10')
            if 'dolby vision' in rq_lower or 'dv' in rq_lower:
                hdrs.append('Dolby Vision')
            if 'imax' in rq_lower:
                hdrs.append('IMAX')
            hdr_text = '｜'.join(hdrs)
        
        if res_label or hdr_text:
            quality_str = res_label
            if hdr_text:
                quality_str = f"{quality_str}｜{hdr_text}" if quality_str else hdr_text
            text_parts.append(f"🖼 质量：{quality_str}")
        
        # 文件信息
        text_parts.append(f"📂 文件：{total_files} 个")
        
        if total_size_str:
            text_parts.append(f"💾 总大小：{total_size_str}")
        
        # TMDB ID
        tmdb_id = first_vars.get('tmdb_id')
        if tmdb_id:
            text_parts.append(f"🍿 TMDB ID：{tmdb_id}")
        
        # 简介（使用第一条）
        overview = first_vars.get('overview')
        if overview:
            overview_short = overview[:160] + ('…' if len(overview) > 160 else '')
            text_parts.append(f"\n📝 简介：{overview_short}")
        
        # 链接
        links = []
        if tmdb_id:
            links.append(f"🔗 [TMDB](https://www.themoviedb.org/tv/{tmdb_id})")
        
        imdb_id = first_vars.get('imdb_id')
        douban_id = first_vars.get('douban_id')
        title_year = first_vars.get('title_year', '')
        
        if douban_id:
            links.append(f"🎬 [豆瓣](https://movie.douban.com/subject/{douban_id}/)")
        elif imdb_id:
            links.append(f"🎬 [豆瓣](https://www.douban.com/search?cat=1002&q={imdb_id})")
        elif title_year:
            from urllib.parse import quote
            links.append(f"🎬 [豆瓣](https://www.douban.com/search?cat=1002&q={quote(title_year)})")
        
        if imdb_id:
            links.append(f"🌟 [IMDb](https://www.imdb.com/title/{imdb_id}/)")
        
        if links:
            text_parts.append("\n🌐 链接：")
            text_parts.append(' | '.join(links))
        
        text = '\n'.join(text_parts)
        
        return title, text
    
    def _merge_episode_ranges(self, episodes: List[str]) -> List[str]:
        """
        合并连续的集数范围
        
        例如: ['S01E01', 'S01E02', 'S01E03', 'S01E05'] -> ['S01E01-E03', 'S01E05']
        """
        if not episodes:
            return []
        
        # 解析集数
        parsed = []
        for ep in episodes:
            try:
                # 格式: S01E02
                parts = ep.split('E')
                season = int(parts[0][1:])
                episode = int(parts[1])
                parsed.append((season, episode, ep))
            except:
                parsed.append((0, 0, ep))
        
        # 按季和集排序
        parsed.sort()
        
        # 合并连续集数
        ranges = []
        current_range_start = None
        current_range_end = None
        current_season = None
        
        for season, episode, ep_str in parsed:
            if current_range_start is None:
                current_range_start = episode
                current_range_end = episode
                current_season = season
            elif season == current_season and episode == current_range_end + 1:
                # 连续，扩展范围
                current_range_end = episode
            else:
                # 不连续，保存当前范围，开始新范围
                if current_range_start == current_range_end:
                    ranges.append(f"S{current_season:02d}E{current_range_start:02d}")
                else:
                    ranges.append(f"S{current_season:02d}E{current_range_start:02d}-E{current_range_end:02d}")
                
                current_range_start = episode
                current_range_end = episode
                current_season = season
        
        # 保存最后一个范围
        if current_range_start is not None:
            if current_range_start == current_range_end:
                ranges.append(f"S{current_season:02d}E{current_range_start:02d}")
            else:
                ranges.append(f"S{current_season:02d}E{current_range_start:02d}-E{current_range_end:02d}")
        
        return ranges
    
    def _get_tmdb_info(self, template_vars: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        从 TMDB 获取图片 URL 和中文简介
        
        Args:
            template_vars: 模板变量字典
        
        Returns:
            (image_url, overview_zh) 元组
        """
        tmdb_id = template_vars.get('tmdb_id')
        
        # 如果没有 TMDB ID，尝试通过其他信息查找
        if not tmdb_id:
            imdb_id = template_vars.get('imdb_id')
            title_year = template_vars.get('title_year', '')
            # 从 title_year 中提取标题和年份（格式如 "剧名 (2023)"）
            title = title_year
            year = None
            if '(' in title_year and ')' in title_year:
                # 尝试提取年份
                match = re.search(r'\((\d{4})\)', title_year)
                if match:
                    year = int(match.group(1))
                    title = title_year[:title_year.rfind('(')].strip()
            
            media_type = template_vars.get('media_type', 'movie')
            found_tmdb_id = find_tmdb_id(
                imdb_id=imdb_id,
                title=title if title else None,
                year=year,
                media_type=media_type,
                api_key=Config.TMDB_API_KEY
            )
            
            if found_tmdb_id:
                tmdb_id = found_tmdb_id
                # 更新 template_vars 以便后续使用
                template_vars['tmdb_id'] = found_tmdb_id
                template_vars['tmdbid'] = found_tmdb_id
        
        if not tmdb_id:
            return None, None
        
        media_type = template_vars.get('media_type', 'movie')
        
        try:
            api_key = Config.TMDB_API_KEY
            if api_key:
                api_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}&language=zh-CN"
            else:
                api_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?language=zh-CN"
            
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # 获取图片 URL
                image_url = None
                poster_path = data.get('poster_path')
                if poster_path:
                    base_url = Config.TMDB_IMAGE_BASE_URL.rstrip('/')
                    image_url = f"{base_url}{poster_path}"
                
                # 获取中文简介（必须是中文，如果没有中文简介则不使用）
                overview_zh = data.get('overview')
                # 只使用中文简介，如果没有中文简介则返回 None（使用 Emby 的简介）
                
                return image_url, overview_zh
        except Exception as e:
            logger.warning(f"从 TMDB 获取信息失败: {e}")
        
        return None, None
    
    def _build_image_url(self, template_vars: Dict[str, Any]) -> Optional[str]:
        """
        从 TMDB 获取图片 URL（兼容接口）
        
        Args:
            template_vars: 模板变量字典
        
        Returns:
            图片 URL 或 None
        """
        # 如果已经有缓存的图片 URL，直接返回
        if '_tmdb_image_url' in template_vars:
            return template_vars['_tmdb_image_url']
        
        # 否则调用 API 获取
        image_url, _ = self._get_tmdb_info(template_vars)
        return image_url
    
    def flush_all(self):
        """立即发送所有待聚合的通知（用于程序关闭时）"""
        with self.lock:
            keys = list(self.pending_notifications.keys())
            for key in keys:
                # 取消定时器
                if key in self.timers:
                    self.timers[key].cancel()
                # 立即发送
                self._send_aggregated_notification(key)

