#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕翻译与硬字幕压制模块
功能：
1. 从YouTube视频提取字幕
2. 使用DeepL API翻译字幕
3. 生成中英对照字幕
4. 使用FFmpeg硬字幕压制到视频
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import subprocess

try:
    import yt_dlp
except ImportError:
    print("请安装 yt-dlp: pip install yt-dlp")
    sys.exit(1)

try:
    import deepl
except ImportError:
    print("请安装 deepl: pip install deepl")
    sys.exit(1)

# 导入配置
try:
    from config import PROXY_URL, NETWORK_TIMEOUT
except ImportError:
    PROXY_URL = ""
    NETWORK_TIMEOUT = 60

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subtitle_burner.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ==================== SRT 解析与生成 ====================

class SubtitleEntry:
    """字幕条目"""
    def __init__(self, index: int, start: str, end: str, text: str):
        self.index = index
        self.start = start
        self.end = end
        self.text = text

    def __repr__(self):
        return f"SubtitleEntry({self.index}, {self.start} --> {self.end}, {self.text[:20]}...)"


def parse_srt(srt_file: Path) -> List[SubtitleEntry]:
    """解析SRT字幕文件"""
    entries = []

    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按空行分割字幕块
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        # 第一行是序号
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # 第二行是时间轴
        time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
        if not time_match:
            continue
        start, end = time_match.groups()

        # 剩余行是字幕文本
        text = '\n'.join(lines[2:]).strip()
        # 清理HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        entries.append(SubtitleEntry(index, start, end, text))

    logger.info(f"解析SRT文件: {len(entries)} 条字幕")
    return entries


def write_bilingual_srt(entries: List[Dict], output_file: Path):
    """写入中英对照SRT文件

    Args:
        entries: 字幕条目列表，每个包含 text_en 和 text_zh
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(entries, 1):
            f.write(f"{i}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text_en']}\n")
            f.write(f"{entry['text_zh']}\n")
            f.write("\n")

    logger.info(f"中英对照字幕已保存: {output_file}")


# ==================== 字幕提取 ====================

def get_available_subtitles(url: str, cookies_file: str = None, proxy: str = None) -> Dict:
    """获取视频可用的字幕列表"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': NETWORK_TIMEOUT,
        }

        # 添加代理支持
        if proxy:
            ydl_opts['proxy'] = proxy
            logger.info(f"使用代理: {proxy}")

        # 添加cookies支持 - 使用绝对路径
        if cookies_file:
            cookies_path = Path(cookies_file)
            if cookies_path.exists():
                ydl_opts['cookiefile'] = str(cookies_path.absolute())
                logger.info(f"使用cookies文件: {cookies_path.absolute()}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            subtitles = info.get('subtitles', {})
            auto_subtitles = info.get('automatic_captions', {})

            logger.info(f"手动字幕: {list(subtitles.keys())}")
            logger.info(f"自动字幕: {list(auto_subtitles.keys())}")

            return {
                'manual': subtitles,
                'auto': auto_subtitles,
                'title': info.get('title', 'Unknown'),
                'id': info.get('id')
            }
    except Exception as e:
        logger.error(f"获取字幕信息失败: {e}")
        return {}


def extract_subtitles(url: str, output_dir: Path, languages: List[str] = None,
                     cookies_file: str = None, proxy: str = None) -> Optional[Path]:
    """从YouTube视频提取字幕

    Args:
        url: YouTube视频URL
        output_dir: 输出目录
        languages: 要下载的字幕语言列表
        cookies_file: cookies文件路径
        proxy: 代理地址

    Returns:
        下载的字幕文件路径，失败返回None
    """
    if languages is None:
        languages = ['en']

    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取视频信息
    subtitle_info = get_available_subtitles(url, cookies_file, proxy)
    if not subtitle_info:
        logger.error("无法获取字幕信息")
        return None

    video_title = subtitle_info.get('title', 'video')
    # 清理文件名
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
    output_template = str(output_dir / f'{safe_title}.%(ext)s')

    # 配置下载选项
    ydl_opts = {
        'outtmpl': output_template,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': languages,
        'skip_download': True,  # 只下载字幕
        'ignoreerrors': True,
        'subtitlesformat': 'srt',
        'quiet': False,
        'socket_timeout': NETWORK_TIMEOUT,
    }

    # 添加代理支持
    if proxy:
        ydl_opts['proxy'] = proxy
        logger.info(f"使用代理: {proxy}")

    # 添加cookies支持 - 使用绝对路径
    if cookies_file:
        cookies_path = Path(cookies_file)
        if cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path.absolute())
            logger.info(f"使用cookies文件: {cookies_path.absolute()}")

    logger.info(f"开始下载字幕，语言: {languages}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 查找下载的字幕文件
        srt_files = list(output_dir.glob(f"{safe_title}*.srt"))

        if srt_files:
            logger.info(f"字幕下载成功: {srt_files[0]}")
            return srt_files[0]
        else:
            # 尝试匹配视频ID
            video_id = subtitle_info.get('id')
            srt_files = list(output_dir.glob(f"*{video_id}*.srt"))
            if srt_files:
                logger.info(f"字幕下载成功: {srt_files[0]}")
                return srt_files[0]

        logger.warning("未找到下载的字幕文件")
        return None

    except Exception as e:
        logger.error(f"字幕下载失败: {e}")
        return None


# ==================== 字幕翻译 ====================

def translate_subtitles(entries: List[SubtitleEntry], api_key: str,
                        target_lang: str = 'ZH-HANS') -> List[Dict]:
    """使用DeepL API翻译字幕

    Args:
        entries: 字幕条目列表
        api_key: DeepL API密钥
        target_lang: 目标语言

    Returns:
        中英对照字幕条目列表
    """
    if not api_key:
        raise ValueError("请先配置 DEEPL_API_KEY")

    translator = deepl.Translator(api_key)

    # 提取所有待翻译文本
    texts = [entry.text for entry in entries]

    logger.info(f"开始翻译 {len(texts)} 条字幕...")

    # 批量翻译
    try:
        results = translator.translate_text(
            texts,
            source_lang='EN',
            target_lang=target_lang
        )

        bilingual_entries = []
        for entry, result in zip(entries, results):
            bilingual_entries.append({
                'start': entry.start,
                'end': entry.end,
                'text_en': entry.text,
                'text_zh': result.text
            })

        logger.info(f"翻译完成")
        return bilingual_entries

    except Exception as e:
        logger.error(f"翻译失败: {e}")
        raise


# ==================== 硬字幕压制 ====================

def burn_subtitles(video_file: Path, subtitle_file: Path,
                   ffmpeg_path: str, style: Dict = None) -> Optional[Path]:
    """使用FFmpeg硬字幕压制到视频

    Args:
        video_file: 视频文件路径
        subtitle_file: 字幕文件路径
        ffmpeg_path: FFmpeg可执行文件路径
        style: 字幕样式配置

    Returns:
        输出视频文件路径
    """
    if not os.path.exists(ffmpeg_path):
        logger.error(f"FFmpeg不存在: {ffmpeg_path}")
        return None

    if not video_file.exists():
        logger.error(f"视频文件不存在: {video_file}")
        return None

    if not subtitle_file.exists():
        logger.error(f"字幕文件不存在: {subtitle_file}")
        return None

    # 默认样式
    if style is None:
        style = {
            'FontName': 'Microsoft YaHei,Arial',
            'FontSize': 18,
            'PrimaryColour': '&HFFFFFF',
            'OutlineColour': '&H000000',
            'Outline': 2,
            'Alignment': 2,
            'MarginV': 30,
            'BorderStyle': 1,
        }

    # 构建样式字符串
    style_str = ','.join(f"{k}={v}" for k, v in style.items())

    # 输出文件路径
    output_file = video_file.parent / f"{video_file.stem}_zh_cn{video_file.suffix}"

    # Windows路径需要转义
    subtitle_path = str(subtitle_file).replace('\\', '\\\\').replace(':', '\\:')

    cmd = [
        ffmpeg_path,
        '-i', str(video_file),
        '-vf', f"subtitles={subtitle_path}:force_style='{style_str}'",
        '-c:a', 'copy',  # 音频不重新编码
        '-y',
        str(output_file)
    ]

    logger.info(f"开始压制字幕...")
    logger.info(f"输出文件: {output_file}")

    try:
        # Windows上需要指定编码避免UnicodeDecodeError
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            logger.info(f"硬字幕压制完成: {output_file}")
            return output_file
        else:
            logger.error(f"FFmpeg错误: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"压制失败: {e}")
        return None


# ==================== 完整流程 ====================

def process_video_with_subtitles(url: str, video_file: Path,
                                 api_key: str, ffmpeg_path: str,
                                 output_dir: Path = None,
                                 cookies_file: str = None,
                                 proxy: str = None) -> Tuple[Optional[Path], Optional[Path]]:
    """完整流程：下载字幕、翻译、压制

    Args:
        url: YouTube视频URL
        video_file: 已下载的视频文件
        api_key: DeepL API密钥
        ffmpeg_path: FFmpeg路径
        output_dir: 字幕输出目录
        cookies_file: cookies文件路径
        proxy: 代理地址

    Returns:
        (字幕文件路径, 硬字幕视频路径)
    """
    if output_dir is None:
        output_dir = video_file.parent

    # 1. 提取字幕
    logger.info("=" * 50)
    logger.info("步骤 1/4: 提取字幕")
    srt_file = extract_subtitles(url, output_dir, cookies_file=cookies_file, proxy=proxy)

    if not srt_file:
        logger.error("字幕提取失败")
        return None, None

    # 保存原始英文字幕副本
    en_srt_backup = output_dir / f"{video_file.stem}.en.srt"
    import shutil
    shutil.copy(srt_file, en_srt_backup)
    logger.info(f"英文字幕已保存: {en_srt_backup}")

    # 2. 解析字幕
    logger.info("=" * 50)
    logger.info("步骤 2/4: 解析字幕")
    entries = parse_srt(srt_file)

    # 3. 翻译字幕
    logger.info("=" * 50)
    logger.info("步骤 3/4: 翻译字幕")
    try:
        bilingual_entries = translate_subtitles(entries, api_key)
    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return en_srt_backup, None

    # 4. 生成中英对照字幕
    bilingual_srt = output_dir / f"{video_file.stem}.zh_cn.srt"
    write_bilingual_srt(bilingual_entries, bilingual_srt)

    # 5. 硬字幕压制
    logger.info("=" * 50)
    logger.info("步骤 4/4: 硬字幕压制")
    final_video = burn_subtitles(video_file, bilingual_srt, ffmpeg_path)

    return bilingual_srt, final_video


# ==================== 命令行接口 ====================

def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="字幕翻译与硬字幕压制工具")
    parser.add_argument("url", help="YouTube视频URL")
    parser.add_argument("--video", help="已下载的视频文件路径")
    parser.add_argument("--api-key", help="DeepL API密钥")
    parser.add_argument("--ffmpeg", help="FFmpeg路径")
    parser.add_argument("--output-dir", default="./downloads", help="输出目录")
    parser.add_argument("--extract-only", action="store_true", help="只提取字幕")
    parser.add_argument("--translate-only", action="store_true", help="只翻译已有字幕")
    parser.add_argument("--burn-only", action="store_true", help="只压制已有字幕")

    args = parser.parse_args()

    # 从配置文件读取
    try:
        from config import DEEPL_API_KEY, FFMPEG_PATH
    except ImportError:
        DEEPL_API_KEY = ""
        FFMPEG_PATH = "ffmpeg"

    api_key = args.api_key or DEEPL_API_KEY
    ffmpeg_path = args.ffmpeg or FFMPEG_PATH
    output_dir = Path(args.output_dir)

    if not api_key:
        print("错误: 请配置 DEEPL_API_KEY")
        return

    if args.extract_only:
        # 只提取字幕
        srt_file = extract_subtitles(args.url, output_dir)
        if srt_file:
            print(f"字幕已保存: {srt_file}")
        return

    if args.translate_only:
        # 只翻译
        if not args.video:
            print("错误: 请指定 --video 参数")
            return
        srt_file = Path(args.video)
        entries = parse_srt(srt_file)
        bilingual = translate_subtitles(entries, api_key)
        output_file = srt_file.parent / f"{srt_file.stem}.zh_cn.srt"
        write_bilingual_srt(bilingual, output_file)
        print(f"翻译字幕已保存: {output_file}")
        return

    if args.burn_only:
        # 只压制
        if not args.video:
            print("错误: 请指定 --video 参数")
            return
        video_file = Path(args.video)
        # 查找对应的字幕文件
        srt_file = video_file.parent / f"{video_file.stem}.zh_cn.srt"
        if not srt_file.exists():
            print(f"错误: 字幕文件不存在: {srt_file}")
            return
        result = burn_subtitles(video_file, srt_file, ffmpeg_path)
        if result:
            print(f"硬字幕视频已保存: {result}")
        return

    # 完整流程
    if not args.video:
        print("错误: 请指定 --video 参数（已下载的视频文件路径）")
        print("提示: 请先用 yt_downloader.py 下载视频")
        return

    video_file = Path(args.video)
    if not video_file.exists():
        print(f"错误: 视频文件不存在: {video_file}")
        return

    srt, video = process_video_with_subtitles(
        args.url, video_file, api_key, ffmpeg_path, output_dir
    )

    if video:
        print(f"\n完成!")
        print(f"中英对照字幕: {srt}")
        print(f"硬字幕视频: {video}")
    else:
        print(f"\n部分完成")
        print(f"中英对照字幕: {srt}")


if __name__ == "__main__":
    main()
