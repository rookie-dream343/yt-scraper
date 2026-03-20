#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频下载工具
需要: cookies.txt, deno
"""

import os
import sys
import subprocess
from pathlib import Path

# Deno路径
DENO_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe\deno.exe"
# Ffmpeg路径
FFMPEG_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
COOKIES_FILE = "cookies.txt"

def download_video(url: str, output_dir: str = './downloads', quality: str = 'best'):
    """下载视频"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 检查cookies
    cookies_path = Path(COOKIES_FILE)
    cookies_arg = []
    if cookies_path.exists():
        cookies_arg = ['--cookies', str(cookies_path)]
    else:
        print(f"警告: 未找到 {COOKIES_FILE}，可能无法下载")

    # 检查deno
    deno_arg = []
    if os.path.exists(DENO_PATH):
        deno_arg = ['--js-runtimes', f'deno:{DENO_PATH}']
    else:
        print(f"警告: 未找到 deno")

    # 检查ffmpeg
    ffmpeg_arg = []
    if os.path.exists(FFMPEG_PATH):
        ffmpeg_arg = ['--ffmpeg-location', FFMPEG_PATH]
    else:
        print(f"警告: 未找到 ffmpeg，视频音频可能无法合并")

    # 格式选择
    formats = {
        '4k': 'bestvideo[height<=2160]+bestaudio/best',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best',
        '720p': 'bestvideo[height<=720]+bestaudio/best',
        '480p': 'bestvideo[height<=480]+bestaudio/best',
        'best': 'bestvideo+bestaudio/best',
    }
    format_str = formats.get(quality, 'bestvideo+bestaudio/best')

    # 构建命令
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        *cookies_arg,
        *deno_arg,
        *ffmpeg_arg,
        '-f', format_str,
        '-o', str(output_path / '%(title)s.%(ext)s'),
        '--merge-output-format', 'mp4',
        '--audio-format', 'aac',
        '--postprocessor-args', 'ffmpeg:-acodec aac -strict experimental',
        url
    ]

    print(f"正在下载: {url}")
    print(f"质量: {quality}")
    print("-" * 50)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n用户取消")
        return False

def main():
    print("=" * 60)
    print("           YouTube 视频下载器")
    print("=" * 60)

    print("\n提示: 确保 cookies.txt 文件在当前目录")

    while True:
        print("\n" + "-" * 60)
        url = input("输入YouTube链接 (q退出): ").strip()

        if url.lower() == 'q':
            break

        if not url:
            continue

        # 选择质量
        print("\n选择质量:")
        print("  0 - 最佳")
        print("  1 - 4K")
        print("  2 - 1440p")
        print("  3 - 1080p")
        print("  4 - 720p")
        print("  5 - 480p")

        choice = input("选择 (直接回车=最佳): ").strip()
        qualities = {'0': 'best', '1': '4k', '2': '1440p', '3': '1080p', '4': '720p', '5': '480p'}
        quality = qualities.get(choice, 'best')

        # 下载
        success = download_video(url, './downloads', quality)

        if success:
            print("\n✓ 下载完成!")
        else:
            print("\n✗ 下载失败")

if __name__ == "__main__":
    main()
