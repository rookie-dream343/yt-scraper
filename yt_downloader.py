#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频下载工具
需要: cookies.txt, deno
功能: 视频下载 + 字幕翻译 + 硬字幕压制
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

try:
    from config import DEEPL_API_KEY, FFMPEG_PATH, DENO_PATH, COOKIES_FILE, SUBTITLE_STYLE, COOKIES_FROM_BROWSER
except ImportError:
    print("警告: 无法导入config.py，使用默认配置")
    DEEPL_API_KEY = ""
    DENO_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe\deno.exe"
    FFMPEG_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
    COOKIES_FILE = "cookies.txt"
    COOKIES_FROM_BROWSER = "chrome"
    SUBTITLE_STYLE = {}

def get_latest_video(output_dir: Path) -> Optional[Path]:
    """获取下载目录中最新修改的视频文件"""
    video_files = list(output_dir.glob("*.mp4")) + list(output_dir.glob("*.mkv")) + list(output_dir.glob("*.webm"))
    if not video_files:
        return None
    return max(video_files, key=lambda f: f.stat().st_mtime)

def download_video(url: str, output_dir: str = './downloads', quality: str = 'best') -> Optional[Path]:
    """下载视频"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Cookies处理
    cookies_arg = []
    cookies_path = Path(COOKIES_FILE)

    if cookies_path.exists():
        cookies_arg = ['--cookies', str(cookies_path)]
        print(f"使用cookies文件: {COOKIES_FILE}")
    else:
        print(f"警告: 未找到 {COOKIES_FILE}")
        print(f"请手动导出cookies.txt到当前目录")
        print(f"推荐扩展: 'Get cookies.txt LOCALLY' 或 'Cookie-Editor'")
        return None

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
        if result.returncode == 0:
            # 返回下载的视频文件路径
            video_file = get_latest_video(output_path)
            if video_file:
                print(f"\n视频已保存: {video_file.name}")
                return video_file
        return None
    except KeyboardInterrupt:
        print("\n用户取消")
        return None

def process_subtitles(url: str, video_file: Path, output_dir: Path):
    """处理字幕：提取、翻译、压制"""
    try:
        from subtitle_burner import process_video_with_subtitles
    except ImportError:
        print("\n✗ 无法导入subtitle_burner模块")
        return None

    if not DEEPL_API_KEY:
        print("\n✗ 请先在config.py中配置DEEPL_API_KEY")
        return None

    print("\n" + "=" * 50)
    print("开始处理字幕...")
    print("=" * 50)

    # 检查cookies文件
    cookies_file = None
    if Path(COOKIES_FILE).exists():
        cookies_file = COOKIES_FILE
        print(f"使用cookies: {COOKIES_FILE}")

    srt_file, final_video = process_video_with_subtitles(
        url, video_file, DEEPL_API_KEY, FFMPEG_PATH, output_dir, cookies_file
    )

    if final_video:
        print(f"\n✓ 字幕处理完成!")
        print(f"  中英对照字幕: {srt_file}")
        print(f"  硬字幕视频: {final_video}")
        return final_video
    else:
        print(f"\n⚠ 字幕处理部分完成")
        print(f"  字幕文件: {srt_file}")
        return None

def main():
    print("=" * 60)
    print("       YouTube 视频下载器 + 字幕翻译")
    print("=" * 60)

    # 检查API配置
    if not DEEPL_API_KEY:
        print("\n⚠ 警告: 未配置DEEPL_API_KEY，字幕翻译功能不可用")
        print("  请在config.py中填入您的DeepL API密钥")
    else:
        print(f"\n✓ DeepL API已配置")

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

        # 询问是否处理字幕
        print("\n是否处理字幕?")
        print("  0 - 不处理字幕")
        print("  1 - 下载并翻译字幕，硬字幕压制")

        subtitle_choice = input("选择 (直接回车=不处理): ").strip()

        output_dir = Path('./downloads')
        # 下载视频
        video_file = download_video(url, str(output_dir), quality)

        if not video_file:
            print("\n✗ 下载失败")
            continue

        print("\n✓ 视频下载完成!")

        # 处理字幕
        if subtitle_choice == '1':
            process_subtitles(url, video_file, output_dir)
        else:
            print("\n跳过字幕处理")

if __name__ == "__main__":
    main()
