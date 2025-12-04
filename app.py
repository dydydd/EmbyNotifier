#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emby 入库通知 Telegram Bot - 主应用
"""

import json
import logging

from flask import Flask, request, jsonify

from config import Config
from parser import EmbyDataParser
from telegram_client import TelegramClient
from templates import TemplateManager
from notification_aggregator import NotificationAggregator

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
        
        # 使用聚合器处理通知（剧集会聚合，电影直接发送）
        success = aggregator.add_notification(data)
        
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

