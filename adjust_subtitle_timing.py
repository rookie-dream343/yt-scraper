#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕时间轴调整工具
用于调整已生成的中英对照字幕的时间轴
"""

import os
import sys
import re
from pathlib import Path

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

def adjust_subtitle_file(srt_file, offset_seconds):
    """调整字幕文件的时间轴

    Args:
        srt_file: 字幕文件路径
        offset_seconds: 时间偏移（秒），正数延后，负数提前

    Returns:
        是否成功
    """
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析字幕
        lines = content.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检测时间轴行
            if '-->' in line:
                time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
                if time_match:
                    start = parse_time_to_seconds(time_match.group(1))
                    end = parse_time_to_seconds(time_match.group(2))

                    # 应用偏移
                    start += offset_seconds
                    end += offset_seconds

                    # 确保时间不为负
                    if start < 0:
                        start = 0
                    if end < start + 0.5:
                        end = start + 0.5

                    new_time = f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}"
                    result.append(new_time)
                else:
                    result.append(line)
            else:
                result.append(line)

            i += 1

        # 写入文件
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result))

        return True

    except Exception as e:
        print(f"错误: {e}")
        return False

def main():
    print("=" * 60)
    print("              字幕时间轴调整工具")
    print("=" * 60)

    downloads = Path("./downloads")

    # 查找所有中英对照字幕文件
    srt_files = list(downloads.glob("*.zh_cn.srt"))

    if not srt_files:
        print("未找到中英对照字幕文件 (*.zh_cn.srt)")
        print("请确保已运行字幕翻译工具")
        return

    print(f"\n找到 {len(srt_files)} 个字幕文件:\n")

    for i, f in enumerate(srt_files, 1):
        print(f"  {i}. {f.name}")

    # 选择文件
    print("\n选择要调整的字幕文件:")
    choice = input("输入序号 (直接回车=全部): ").strip()

    if choice == "":
        selected = srt_files
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(srt_files):
                selected = [srt_files[idx]]
            else:
                print("无效选择")
                return
        except ValueError:
            print("无效输入")
            return

    # 输入偏移量
    print("\n输入时间偏移量（秒）:")
    print("  正数: 字幕延后（如字幕太快了）")
    print("  负数: 字幕提前（如字幕太慢了）")
    print("  示例: 0.5（延后0.5秒）, -0.3（提前0.3秒）")

    offset_input = input("\n偏移量 (直接回车=0.0): ").strip()

    if offset_input == "":
        offset = 0.0
    else:
        try:
            offset = float(offset_input)
        except ValueError:
            print("无效输入")
            return

    print(f"\n应用偏移: {offset:+.2f}秒")

    # 调整字幕
    success_count = 0
    for srt_file in selected:
        print(f"\n处理: {srt_file.name}")
        if adjust_subtitle_file(srt_file, offset):
            print(f"  ✓ 完成")
            success_count += 1
        else:
            print(f"  ✗ 失败")

    print(f"\n成功调整 {success_count}/{len(selected)} 个文件")

    # 询问是否重新压制视频
    if success_count > 0:
        print("\n是否重新压制视频到视频?")
        burn_choice = input("输入 y 重新压制，其他跳过: ").strip().lower()

        if burn_choice == 'y':
            try:
                from burn_subtitles import find_video_subtitle_pairs, burn_subtitles
            except ImportError:
                print("无法导入压制模块")
                return

            # 查找对应的视频和字幕对
            pairs = []
            for srt_file in selected:
                stem = srt_file.stem.replace('.zh_cn', '')
                # 查找对应的视频文件
                for ext in ['.mp4', '.mkv']:
                    video_file = downloads / f"{stem}{ext}"
                    if video_file.exists():
                        pairs.append((video_file, srt_file))
                        break

            if pairs:
                print(f"\n找到 {len(pairs)} 个视频需要重新压制")
                for video, srt in pairs:
                    output = downloads / f"{video.stem}_zh_cn{video.suffix}"
                    print(f"\n压制: {video.name}")
                    if burn_subtitles(str(video), str(srt), str(output)):
                        print(f"  ✓ 完成: {output.name}")
            else:
                print("\n未找到对应的视频文件")

if __name__ == "__main__":
    main()
