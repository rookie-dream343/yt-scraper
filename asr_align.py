#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Whisper ASR的字幕时间轴自动对齐模块

原理：
1. 使用Whisper识别视频音频，获取带时间戳的文本
2. 将Whisper识别结果与字幕文本进行模糊匹配
3. 根据匹配结果修正字幕时间轴
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

try:
    import whisper
except ImportError:
    print("请安装 whisper: pip install openai-whisper")
    sys.exit(1)

try:
    from config import FFMPEG_PATH
except ImportError:
    FFMPEG_PATH = "ffmpeg"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('asr_align.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def time_to_seconds(time_str: str) -> float:
    """将SRT时间格式转换为秒"""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(seconds: float) -> str:
    """将秒转换为SRT时间格式"""
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def extract_audio_from_video(video_path: str, output_audio: str = None) -> Optional[str]:
    """从视频中提取音频"""
    if output_audio is None:
        video_path_obj = Path(video_path)
        output_audio = str(video_path_obj.parent / f"{video_path_obj.stem}.wav")

    if os.path.exists(output_audio):
        logger.info(f"音频文件已存在: {output_audio}")
        return output_audio

    logger.info(f"从视频提取音频...")

    import subprocess
    cmd = [
        FFMPEG_PATH,
        '-i', video_path,
        '-vn',  # 不处理视频
        '-acodec', 'pcm_s16le',  # 16位PCM
        '-ar', '16000',  # 16kHz采样率（Whisper推荐）
        '-ac', '1',  # 单声道
        '-y',
        output_audio
    ]

    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        logger.info(f"音频提取完成: {output_audio}")
        return output_audio
    else:
        logger.error(f"音频提取失败: {result.stderr.decode('utf-8', errors='ignore')}")
        return None


def transcribe_with_whisper(audio_path: str, model_size: str = 'base') -> List[Dict]:
    """使用Whisper转录音频，返回带时间戳的片段

    Args:
        audio_path: 音频文件路径
        model_size: Whisper模型大小 (tiny, base, small, medium, large)

    Returns:
        转录结果列表，每项包含 {start, end, text}
    """
    import os

    # 检查是否有可用的代理
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')

    logger.info(f"加载Whisper模型 ({model_size})...")

    # 尝试多种方式加载模型
    model = None
    load_attempts = []

    # 方式1: 直接加载（使用缓存）
    load_attempts.append(('直接加载', lambda: whisper.load_model(model_size)))

    # 方式2: 使用HuggingFace镜像
    if not proxy:
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        load_attempts.append(('使用HF镜像', lambda: whisper.load_model(model_size)))

    # 方式3: 使用代理
    if proxy:
        load_attempts.insert(0, (f'使用代理 {proxy}', lambda: whisper.load_model(model_size)))

    last_error = None
    for desc, attempt_func in load_attempts:
        try:
            logger.info(f"尝试{desc}...")
            model = attempt_func()
            break
        except Exception as e:
            last_error = e
            logger.warning(f"{desc}失败: {e}")
            # 清理环境变量
            if 'HF_ENDPOINT' in os.environ:
                del os.environ['HF_ENDPOINT']
            continue

    if model is None:
        logger.error("=" * 50)
        logger.error("Whisper模型加载失败！")
        logger.error("=" * 50)
        logger.error("可能的原因:")
        logger.error("1. 网络连接问题（SSL错误）")
        logger.error("2. 需要代理访问HuggingFace")
        logger.error("3. 防火墙阻止了连接")
        logger.error("")
        logger.error("解决方案:")
        logger.error("A. 配置代理后重试")
        logger.error("   set HTTPS_PROXY=http://127.0.0.1:7890")
        logger.error("")
        logger.error("B. 手动下载模型文件:")
        logger.error("   1. 访问 https://hf-mirror.com/gpt-openai/whisper-tiny")
        logger.error("   2. 下载 pytorch_model.bin")
        logger.error("   3. 保存到: C:\\Users\\Zamateur\\.cache\\whisper\\tiny.pt")
        logger.error("")
        logger.error("C. 暂时禁用ASR对齐，使用改进的合并算法")
        logger.error("   设置 config.py: ENABLE_ASR_ALIGNMENT = False")
        logger.error("=" * 50)
        raise Exception("无法加载Whisper模型")

    logger.info(f"开始转录音频...")

    result = model.transcribe(
        audio_path,
        language='en',  # 假设视频是英文
        word_timestamps=True,  # 获取单词级时间戳
        verbose=False
    )

    segments = []
    for segment in result['segments']:
        segments.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip()
        })

    logger.info(f"转录完成，共 {len(segments)} 个片段")
    return segments


def normalize_text(text: str) -> str:
    """标准化文本用于匹配"""
    # 转小写
    text = text.lower()
    # 移除标点符号
    text = re.sub(r'[^\w\s]', '', text)
    # 移除多余空格
    text = ' '.join(text.split())
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（0-1）"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if not norm1 or not norm2:
        return 0.0

    return SequenceMatcher(None, norm1, norm2).ratio()


def align_subtitle_to_asr(subtitle_entries: List[Dict], asr_segments: List[Dict],
                           min_similarity: float = 0.5) -> List[Dict]:
    """将字幕时间轴对齐到ASR识别结果

    策略：
    1. 对每条字幕，在ASR结果中找到最匹配的片段
    2. 使用ASR片段的时间戳更新字幕时间
    3. 如果找不到匹配，保持原时间

    Args:
        subtitle_entries: 字幕条目列表 {start, end, text_en, text_zh, ...}
        asr_segments: ASR识别片段列表 {start, end, text}
        min_similarity: 最小相似度阈值

    Returns:
        时间轴调整后的字幕条目
    """
    logger.info(f"开始对齐 {len(subtitle_entries)} 条字幕到 {len(asr_segments)} 个ASR片段...")

    aligned = []
    matched_count = 0

    for entry in subtitle_entries:
        subtitle_text = entry['text_en']

        # 寻找最佳匹配的ASR片段
        best_match = None
        best_similarity = 0
        best_idx = -1

        for i, segment in enumerate(asr_segments):
            # 检查时间窗口是否接近（前后5秒内）
            time_diff = abs(segment['start'] - entry['start_sec'])
            if time_diff > 5:
                continue

            similarity = calculate_similarity(subtitle_text, segment['text'])

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = segment
                best_idx = i

        # 如果找到足够好的匹配，使用ASR时间
        if best_match and best_similarity >= min_similarity:
            # 使用ASR片段的时间，但保留一些缓冲
            aligned.append({
                **entry,
                'start': seconds_to_time(best_match['start']),
                'end': seconds_to_time(best_match['end']),
                'start_sec': best_match['start'],
                'end_sec': best_match['end'],
                'similarity': best_similarity
            })
            matched_count += 1
        else:
            # 未找到匹配，保持原时间
            aligned.append({
                **entry,
                'similarity': 0
            })

    logger.info(f"对齐完成: {matched_count}/{len(subtitle_entries)} 条字幕已匹配")

    return aligned


def align_subtitle_file(video_file: str, subtitle_file: str,
                        output_file: str = None, model_size: str = 'base') -> bool:
    """对齐字幕文件到视频音频

    Args:
        video_file: 视频文件路径
        subtitle_file: 字幕文件路径 (.zh_cn.srt)
        output_file: 输出字幕文件路径 (可选)
        model_size: Whisper模型大小

    Returns:
        是否成功
    """
    video_path = Path(video_file)
    srt_path = Path(subtitle_file)

    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_file}")
        return False

    if not srt_path.exists():
        logger.error(f"字幕文件不存在: {subtitle_file}")
        return False

    if output_file is None:
        output_file = str(srt_path)

    # 1. 提取音频
    audio_file = extract_audio_from_video(str(video_path))
    if not audio_file:
        return False

    # 2. Whisper转录
    asr_segments = transcribe_with_whisper(audio_file, model_size)
    if not asr_segments:
        logger.error("ASR转录失败")
        return False

    # 3. 解析字幕文件
    entries = []
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.+?)\n(.+?)(?=\n\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)

    for match in matches:
        idx, start, end, text_en, text_zh = match
        entries.append({
            'index': int(idx),
            'start': start,
            'end': end,
            'start_sec': time_to_seconds(start),
            'end_sec': time_to_seconds(end),
            'text_en': text_en.strip(),
            'text_zh': text_zh.strip()
        })

    # 4. 对齐时间轴
    aligned_entries = align_subtitle_to_asr(entries, asr_segments)

    # 5. 写入对齐后的字幕
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(aligned_entries, 1):
            f.write(f"{i}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text_en']}\n")
            f.write(f"{entry['text_zh']}\n\n")

    logger.info(f"对齐完成，保存到: {output_file}")

    # 清理音频文件
    if os.path.exists(audio_file):
        os.remove(audio_file)

    return True


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="基于Whisper ASR的字幕时间轴对齐工具")
    parser.add_argument("video", help="视频文件路径")
    parser.add_argument("--subtitle", help="字幕文件路径 (.zh_cn.srt)")
    parser.add_argument("--model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper模型大小 (默认: base)")
    parser.add_argument("--output", help="输出字幕文件路径")

    args = parser.parse_args()

    # 如果没有指定字幕文件，自动查找
    if not args.subtitle:
        video_path = Path(args.video)
        srt_file = video_path.parent / f"{video_path.stem}.zh_cn.srt"
        if not srt_file.exists():
            print(f"未找到字幕文件: {srt_file}")
            return
        args.subtitle = str(srt_file)

    print(f"视频: {args.video}")
    print(f"字幕: {args.subtitle}")
    print(f"模型: {args.model}")

    success = align_subtitle_file(
        args.video,
        args.subtitle,
        args.output,
        args.model
    )

    if success:
        print("\n✓ 对齐完成!")

        # 询问是否重新压制
        from pathlib import Path
        video_path = Path(args.video)
        output_video = video_path.parent / f"{video_path.stem}_zh_cn{video_path.suffix}"

        burn_choice = input(f"\n是否重新压制视频到 {output_video.name}? (y/n): ").strip().lower()
        if burn_choice == 'y':
            try:
                from burn_subtitles import burn_subtitles
                if burn_subtitles(args.video, args.subtitle, str(output_video)):
                    print(f"✓ 视频已保存: {output_video}")
            except ImportError:
                print("无法导入压制模块")
    else:
        print("\n✗ 对齐失败")


if __name__ == "__main__":
    main()
