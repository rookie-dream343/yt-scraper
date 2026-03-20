#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频字幕压制工具
直接处理downloads目录中的视频和字幕文件
"""

import os
import sys
import subprocess
from pathlib import Path
import re

# FFmpeg路径
FFMPEG_PATH = r"C:\Users\zamateur\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

def parse_time_to_seconds(time_str):
    """将SRT时间转换为秒"""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds

def seconds_to_srt_time(seconds):
    """将秒转换为SRT时间格式"""
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def adjust_subtitle_timing(srt_file, output_file, gap=0.2):
    """调整字幕时间轴，避免重叠"""
    with open(srt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析字幕
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n*$)'
    matches = re.findall(pattern, content, re.DOTALL)

    entries = []
    for match in matches:
        idx, start, end, text = match
        start_sec = parse_time_to_seconds(start)
        end_sec = parse_time_to_seconds(end)
        entries.append({
            'index': int(idx),
            'start': start,
            'end': end,
            'start_sec': start_sec,
            'end_sec': end_sec,
            'text': text.strip()
        })

    # 调整时间轴
    adjusted = []
    prev_end = 0

    for entry in entries:
        start = entry['start_sec']
        end = entry['end_sec']

        if start < prev_end + gap:
            overlap = prev_end + gap - start
            # 缩短当前字幕的持续时间（如果足够长）
            if (end - start - overlap) >= 1.0:
                start = prev_end + gap
            else:
                start = prev_end + gap
                if end - start < 1.0:
                    end = start + 1.0

        entry['start'] = seconds_to_srt_time(start)
        entry['end'] = seconds_to_srt_time(end)
        entry['start_sec'] = start
        entry['end_sec'] = end

        adjusted.append(entry)
        prev_end = end

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in adjusted:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['text']}\n\n")

    print(f"调整了 {len(adjusted)} 条字幕的时间轴")
    return output_file

def burn_subtitles(video_file, subtitle_file, output_file):
    """使用FFmpeg压制字幕"""
    if not os.path.exists(FFMPEG_PATH):
        print(f"错误: FFmpeg不存在: {FFMPEG_PATH}")
        return False

    if not os.path.exists(video_file):
        print(f"错误: 视频文件不存在: {video_file}")
        return False

    if not os.path.exists(subtitle_file):
        print(f"错误: 字幕文件不存在: {subtitle_file}")
        return False

    # 使用简单名称的临时文件
    work_dir = Path(video_file).parent
    temp_video = work_dir / "__temp_video__.mp4"
    temp_subs = work_dir / "__temp_subs__.srt"

    try:
        # 复制到临时文件
        import shutil
        shutil.copy(video_file, temp_video)

        # 先调整字幕时间轴
        adjust_subtitle_timing(subtitle_file, temp_subs)

        # 获取临时文件的相对路径
        temp_video_name = temp_video.name
        temp_subs_name = temp_subs.name

        # 切换到downloads目录执行
        cmd = [
            FFMPEG_PATH,
            '-i', temp_video_name,
            '-vf', f"subtitles={temp_subs_name}",
            '-c:a', 'copy',
            '-y',
            Path(output_file).name
        ]

        print(f"正在压制字幕...")
        print(f"输入: {Path(video_file).name}")
        print(f"输出: {Path(output_file).name}")

        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            print(f"✓ 压制完成: {output_file}")
            return True
        else:
            print(f"✗ FFmpeg错误:")
            print(result.stderr[-500:] if result.stderr else "Unknown error")
            return False

    except Exception as e:
        print(f"✗ 压制失败: {e}")
        return False
    finally:
        # 清理临时文件
        if temp_video.exists():
            temp_video.unlink()
        if temp_subs.exists():
            temp_subs.unlink()

def find_video_subtitle_pairs(download_dir):
    """查找视频和字幕文件对"""
    download_dir = Path(download_dir)
    pairs = []

    # 查找所有视频文件
    video_files = []
    for ext in ['.mp4', '.mkv', '.avi', '.webm']:
        video_files.extend(list(download_dir.glob(f"*{ext}")))

    for video_file in video_files:
        # 跳过已压制的视频
        if '_zh_cn' in video_file.name or '__temp__' in video_file.name:
            continue

        # 查找对应的中英对照字幕
        stem = video_file.stem
        srt_file = download_dir / f"{stem}.zh_cn.srt"

        if srt_file.exists():
            pairs.append((video_file, srt_file))

    return pairs

def main():
    print("=" * 60)
    print("              字幕压制工具")
    print("=" * 60)

    download_dir = Path("./downloads")

    if not download_dir.exists():
        print(f"错误: downloads目录不存在")
        return

    # 查找视频和字幕对
    pairs = find_video_subtitle_pairs(download_dir)

    if not pairs:
        print("未找到需要压制的视频字幕对")
        print("请确保:")
        print("  1. 视频文件在downloads目录")
        print("  2. 对应的.zh_cn.srt字幕文件存在")
        return

    print(f"\n找到 {len(pairs)} 个待压制的视频:\n")

    for i, (video, srt) in enumerate(pairs, 1):
        print(f"  {i}. {video.name}")

    # 选择要压制的视频
    print("\n选择:")
    print("  0 - 全部压制")
    for i in range(len(pairs)):
        print(f"  {i+1} - {pairs[i][0].name[:50]}")

    choice = input("\n请选择 (直接回车=全部): ").strip()

    if choice == "" or choice == "0":
        selected = pairs
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pairs):
                selected = [pairs[idx]]
            else:
                print("无效选择")
                return
        except ValueError:
            print("无效选择")
            return

    # 开始压制
    success_count = 0
    for video_file, srt_file in selected:
        print("\n" + "-" * 50)
        output_file = video_file.parent / f"{video_file.stem}_zh_cn{video_file.suffix}"

        if burn_subtitles(str(video_file), str(srt_file), str(output_file)):
            success_count += 1

    print("\n" + "=" * 50)
    print(f"完成! 成功: {success_count}/{len(selected)}")

if __name__ == "__main__":
    main()
