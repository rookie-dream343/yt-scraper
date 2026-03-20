#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日文字幕下载功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_video_downloader import SimpleVideoDownloader

def test_japanese_subtitle():
    """测试日文字幕下载"""
    print("测试日文字幕下载功能...")
    
    # 使用一个有日文字幕的视频进行测试
    test_url = "https://www.youtube.com/watch?v=2YYjPs8t8MI"
    
    downloader = SimpleVideoDownloader()
    
    try:
        # 尝试下载日文字幕
        success = downloader.download_srt_only(test_url, ['ja'])
        
        if success:
            print("✅ 日文字幕下载成功！")
        else:
            print("❌ 日文字幕下载失败")
            
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_japanese_subtitle() 