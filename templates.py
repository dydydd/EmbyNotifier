#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息模板管理模块
"""

from jinja2 import Template, Environment, BaseLoader
from urllib.parse import quote


class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        """初始化模板管理器"""
        # 创建 Jinja2 环境并添加 urlencode 过滤器
        self.env = Environment(loader=BaseLoader())
        self.env.filters['urlencode'] = lambda u: quote(str(u), safe='')
        
        # 初始化模板
        self.title_template = self._create_title_template()
        self.text_template = self._create_text_template()
    
    def _create_title_template(self) -> Template:
        """创建标题模板"""
        template_str = (
            "🎬 {{ title_year }}"
            "{% if season_episode %} {{ season_episode }}"
            "{% elif season_fmt %} {{ season_fmt }}"
            "{% endif %} 已入库"
        )
        return self.env.from_string(template_str)
    
    def _create_text_template(self) -> Template:
        """创建正文模板"""
        template_str = """{% set tmdb_actual = tmdbid|default(tmdb_id, true) %}
{% set imdb_actual = imdbid|default(imdb_id, true) %}
{% set douban_actual = doubanid|default(douban_id, true) %}
# 媒体类型自动判定
{% set mt_raw = media_type|default(type, true)|default(tmdb_type, true)|default(tmdb_media_type, true)|default('', true) %}
{% set looks_like_tv = (season_fmt or season_episode) or (category and ('剧' in category or '番' in category)) %}
{% set mt_label = ('剧集' if (mt_raw|string)|lower in ['tv','电视剧','剧集','television','episode'] or looks_like_tv else '电影') %}
{% set mt_type = 'tv' if mt_label == '剧集' else 'movie' %}
# 画质信息组合
{% set rq_input = resource_term|default(resource_quality, true)|default('', true) %}
{% set rq_lower = rq_input|lower %}
{% set vw = (video_width|default(0))|int %}
{% set vh = (video_height|default(0))|int %}
{% if vw >= 3800 or vh >= 2000 %}{% set res_label = '2160p (4K)' %}
{% elif vw >= 1900 or vh >= 1000 %}{% set res_label = '1080p' %}
{% elif vw >= 1200 or vh >= 700 %}{% set res_label = '720p' %}
{% elif '4k' in rq_lower or '2160p' in rq_lower %}{% set res_label = '2160p (4K)' %}
{% elif '1080p' in rq_lower %}{% set res_label = '1080p' %}
{% elif '720p' in rq_lower %}{% set res_label = '720p' %}
{% else %}{% set res_label = '' %}{% endif %}
{% set hdrs = [] %}
{% if 'hdr' in rq_lower and not ('dv' in rq_lower) %}{% set _ = hdrs.append('HDR10') %}{% endif %}
{% if 'dolby vision' in rq_lower or 'dv' in rq_lower %}{% set _ = hdrs.append('Dolby Vision') %}{% endif %}
{% if 'imax' in rq_lower %}{% set _ = hdrs.append('IMAX') %}{% endif %}
{% set hdr_text = '｜'.join(hdrs) %}
# 输出主体
📢 媒体库：Emby
{% if vote_average %}⭐️ 评分：{{ vote_average }}/10
{% endif %}
{{ '📺' if mt_label == '剧集' else '🎦' }} 媒体类型：{{ mt_label }}
{% if category %}🏷 归类：{{ category }}
{% endif %}
{% if res_label or hdr_text %}🖼 质量：{{ res_label }}{% if hdr_text %}｜{{ hdr_text }}{% endif %}
{% endif %}
{% if file_count %}📂 文件：{{ file_count }} 个
{% endif %}
{% if total_size %}💾 大小：{{ total_size }}
{% endif %}
{% if tmdb_actual %}🍿 TMDB ID：{{ tmdb_actual }}
{% endif %}
{% if overview %}

📝 简介：{{ overview[:160] }}{% if overview|length > 160 %}…{% endif %}
{% endif %}

🌐 链接：
{% if tmdb_actual %} 🔗 [TMDB](https://www.themoviedb.org/{{ mt_type }}/{{ tmdb_actual }}){% endif %}
{% if douban_actual %} | 🎬 [豆瓣](https://movie.douban.com/subject/{{ douban_actual }}/)
{% elif imdb_actual %} | 🎬 [豆瓣](https://www.douban.com/search?cat=1002&q={{ imdb_actual }})
{% elif title_year %} | 🎬 [豆瓣](https://www.douban.com/search?cat=1002&q={{ title_year | urlencode }}){% endif %}
{% if imdb_actual %} | 🌟 [IMDb](https://www.imdb.com/title/{{ imdb_actual }}/){% endif %}"""
        
        return self.env.from_string(template_str)
    
    def render(self, template_vars: dict) -> tuple[str, str]:
        """
        渲染模板
        
        Args:
            template_vars: 模板变量字典
        
        Returns:
            (title, text) 元组
        """
        title = self.title_template.render(**template_vars)
        text = self.text_template.render(**template_vars)
        return title, text

