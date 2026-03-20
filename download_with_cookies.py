#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用cookies.txt下载YouTube视频
"""

import os
import sys
from pathlib import Path

def download_with_cookies(url: str, cookie_file: str, output_dir: str = './downloads'):
    """使用cookies下载视频"""
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--cookies', cookie_file,
        '-f', 'bestvideo+bestaudio/best',
        '-o', str(Path(output_dir) / '%(title)s.%(ext)s'),
        '--merge-output-format', 'mp4',
        url
    ]

    print(f"正在下载: {url}")
    print(f"使用cookies: {cookie_file}")
    print("-" * 50)

    import subprocess
    subprocess.run(cmd)

def main():
    if len(sys.argv) < 2:
        print("用法: python download_with_cookies.py <YouTube链接> [cookies.txt路径]")
        print("示例: python download_with_cookies.py https://www.youtube.com/watch?v=xxx cookies.txt")
        return

    url = sys.argv[1]
    cookie_file = sys.argv[2] if len(sys.argv) > 2 else 'cookies.txt'

    if not Path(cookie_file).exists():
        print(f"找不到cookies文件: {cookie_file}")
        print("\n获取cookies.txt的方法:")
        print("1. 安装Chrome扩展 'Get cookies.txt LOCALLY'")
        print("2. 访问 youtube.com 并登录")
        print("3. 点击扩展图标 → Export → 保存为cookies.txt")
        return

    download_with_cookies(url, cookie_file)

if __name__ == "__main__":
    main()
