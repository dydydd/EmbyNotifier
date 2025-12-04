#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emby 入库通知 Telegram Bot - 主应用
"""

import json
import logging
from typing import Optional
import requests

from flask import Flask, request, jsonify

from config import Config
from parser import EmbyDataParser
from telegram_client import TelegramClient
from templates import TemplateManager
from notification_aggregator import NotificationAggregator


def _get_tmdb_info(template_vars: dict) -> tuple[Optional[str], Optional[str]]:
    """
    从 TMDB 获取图片 URL 和中文简介
    
    Args:
        template_vars: 模板变量字典
    
    Returns:
        (image_url, overview_zh) 元组，如果获取失败则返回 (None, None)
    """
    tmdb_id = template_vars.get('tmdb_id')
    if not tmdb_id:
        return None, None
    
    media_type = template_vars.get('media_type', 'movie')  # 'tv' 或 'movie'
    
    try:
        # 使用 TMDB API 获取信息（优先中文）
        api_key = Config.TMDB_API_KEY
        if api_key:
            # 使用 API Key 访问（推荐）
            api_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}&language=zh-CN"
        else:
            # 无 API Key 访问（公开访问，但可能有限制）
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


def _build_image_url(template_vars: dict) -> Optional[str]:
    """
    从 TMDB 获取图片 URL（兼容旧接口）
    
    Args:
        template_vars: 模板变量字典
    
    Returns:
        图片 URL 或 None
    """
    image_url, _ = _get_tmdb_info(template_vars)
    return image_url

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化组件
parser = EmbyDataParser()
telegram_client = TelegramClient()
template_manager = TemplateManager()
aggregator = NotificationAggregator(
    telegram_client=telegram_client,
    template_manager=template_manager,
    parser=parser,
    aggregation_delay=Config.AGGREGATION_DELAY
)


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收 Emby webhook"""
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("收到空请求")
            return jsonify({'status': 'error', 'message': 'Empty request'}), 400
        
        logger.info(f"收到 webhook 数据: {json.dumps(data, ensure_ascii=False)[:200]}...")
        
        # 只处理 library.new 事件
        event = parser.get_event(data)
        
        if event != 'library.new':
            logger.info(f"忽略事件: {event}")
            return jsonify({'status': 'ignored', 'message': f'Event {event} ignored'}), 200
        
        # 解析数据获取基本信息
        template_vars = parser.parse(data)
        if template_vars:
            # 从 TMDB 获取图片和中文简介
            image_url, overview_zh = _get_tmdb_info(template_vars)
            if image_url:
                template_vars['_tmdb_image_url'] = image_url
            if overview_zh:
                template_vars['overview'] = overview_zh
                template_vars['overview_source'] = 'tmdb'
        
        # 使用聚合器处理通知（剧集会聚合，电影直接发送）
        # 将更新后的 template_vars 传递回去（通过重新解析，但保留 TMDB 信息）
        success = aggregator.add_notification(data, template_vars_override=template_vars if template_vars else None)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Notification queued'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process notification'}), 500
            
    except Exception as e:
        logger.exception(f"处理 webhook 时出错: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'telegram_configured': Config.is_telegram_configured()
    }), 200


@app.route('/', methods=['GET'])
def index():
    """首页"""
    return jsonify({
        'name': 'Emby Telegram Notifier',
        'version': '1.0.0',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)'
        }
    }), 200


def main():
    """主函数"""
    # 检查配置
    is_valid, error_msg = Config.validate()
    if not is_valid:
        logger.warning(f"警告：配置验证失败 - {error_msg}")
        logger.warning("程序将无法正常工作，请检查环境变量配置")
    
    logger.info(f"启动 Emby Telegram 通知服务，监听 {Config.WEBHOOK_HOST}:{Config.WEBHOOK_PORT}")
    app.run(host=Config.WEBHOOK_HOST, port=Config.WEBHOOK_PORT, debug=False)


if __name__ == '__main__':
    main()

