#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from typing import Optional, Tuple


class Config:
    """应用配置"""
    
    # Telegram 配置
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Webhook 服务配置
    WEBHOOK_HOST: str = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    WEBHOOK_PORT: int = int(os.getenv('WEBHOOK_PORT', '5000'))
    
    # 聚合通知配置
    AGGREGATION_DELAY: int = int(os.getenv('AGGREGATION_DELAY', '10'))  # 聚合延迟时间（秒）
    
    # TMDB 配置（用于获取图片）
    TMDB_API_KEY: str = os.getenv('TMDB_API_KEY', '')  # TMDB API Key（可选，但推荐配置以获得更好的访问速度）
    TMDB_IMAGE_BASE_URL: str = os.getenv('TMDB_IMAGE_BASE_URL', 'https://image.tmdb.org/t/p/w500')  # TMDB 图片基础 URL
    
    @classmethod
    def validate(cls) -> Tuple[bool, Optional[str]]:
        """
        验证配置是否完整
        
        Returns:
            (is_valid, error_message)
        """
        if not cls.TELEGRAM_BOT_TOKEN:
            return False, "TELEGRAM_BOT_TOKEN 未设置"
        
        if not cls.TELEGRAM_CHAT_ID:
            return False, "TELEGRAM_CHAT_ID 未设置"
        
        return True, None
    
    @classmethod
    def is_telegram_configured(cls) -> bool:
        """检查 Telegram 是否已配置"""
        return bool(cls.TELEGRAM_BOT_TOKEN and cls.TELEGRAM_CHAT_ID)

