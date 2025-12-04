#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 客户端模块
"""

import logging
from typing import Optional
import requests

from config import Config

logger = logging.getLogger(__name__)


class TelegramClient:
    """Telegram Bot 客户端"""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化 Telegram 客户端
        
        Args:
            bot_token: Telegram Bot Token，如果为 None 则从 Config 读取
            chat_id: Telegram Chat ID，如果为 None 则从 Config 读取
        """
        self.bot_token = bot_token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, title: str, text: str, parse_mode: str = 'Markdown') -> bool:
        """
        发送消息到 Telegram
        
        Args:
            title: 消息标题
            text: 消息正文
            parse_mode: 解析模式，默认为 'Markdown'
        
        Returns:
            是否发送成功
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Telegram 配置缺失：BOT_TOKEN 或 CHAT_ID 未设置")
            return False
        
        # 组合完整消息
        full_message = f"{title}\n\n{text}"
        
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': full_message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"消息已发送到 Telegram: {title[:50]}...")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"发送 Telegram 消息失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应内容: {e.response.text}")
            return False
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.bot_token and self.chat_id)

