#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
请在此处配置您的API密钥和工具路径
"""

from pathlib import Path

# ==================== DeepL API 配置 ====================
# 请在此处填入您的DeepL API密钥
# 获取方式: https://www.deepl.com/pro-api
# 免费版每月可翻译50万字符
DEEPL_API_KEY = "e7d81b65-e92c-42db-bc9f-07c1ccc965e3:fx"  # 请填入您的API密钥

# ==================== 工具路径配置 ====================
# FFmpeg路径
FFMPEG_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

# Deno路径 (用于yt-dlp的JavaScript运行时)
DENO_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe\deno.exe"

# Cookies文件路径
COOKIES_FILE = "cookies.txt"

# 网络代理设置（如果需要）
# 留空则不使用代理
# HTTP代理示例: "http://127.0.0.1:7890"
# SOCKS5代理示例: "socks5://127.0.0.1:7890"
PROXY_URL = ""  # 请填入您的代理地址（如果需要）

# 网络超时设置（秒）
NETWORK_TIMEOUT = 60

# 从浏览器自动获取cookies
# 支持的浏览器: chrome, edge, firefox, opera, brave, vivaldi
# 设为 None 或空字符串 则使用cookies.txt文件
COOKIES_FROM_BROWSER = ""  # 留空使用cookies.txt，手动导出更稳定

# ==================== 字幕样式配置 ====================
# 硬字幕样式
SUBTITLE_STYLE = {
    'FontName': 'Microsoft YaHei,Arial',  # 字体（中英文）
    'FontSize': 18,                       # 字体大小
    'PrimaryColour': '&HFFFFFF',          # 字体颜色（白色）
    'OutlineColour': '&H000000',          # 描边颜色（黑色）
    'Outline': 2,                         # 描边宽度
    'Alignment': 2,                       # 对齐方式：2=底部居中
    'MarginV': 30,                        # 底部边距
    'BorderStyle': 1,                     # 边框样式：1=描边
}

# ==================== 字幕语言配置 ====================
# 优先尝试的字幕语言
SUBTITLE_LANGUAGES = ['en']  # 英文（手动字幕优先）

# 翻译目标语言
DEEPL_TARGET_LANG = 'ZH-HANS'  # 简体中文

# ==================== 输出目录 ====================
DOWNLOAD_DIR = Path('./downloads')
SUBTITLE_DIR = Path('./subtitles')

# ==================== 文件命名模板 ====================
# 原始视频：%(title)s.%(ext)s
# 英文字幕：%(title)s.en.srt
# 中英对照字幕：%(title)s.zh_cn.srt
# 硬字幕视频：%(title)s_zh_cn.%(ext)s
