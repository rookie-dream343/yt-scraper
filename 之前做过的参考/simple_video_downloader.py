#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版YouTube视频下载工具
支持下载视频和SRT字幕，去掉Whisper字幕生成功能
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import subprocess
from typing import Optional, List, Dict

import yt_dlp

# FFmpeg路径检测
def find_ffmpeg():
    """查找FFmpeg可执行文件路径"""
    common_paths = [
        "ffmpeg",  # 系统PATH中
        "C:\\FFmpeg\\bin\\ffmpeg.exe",  # 常见安装路径
        "C:\\ffmpeg\\bin\\ffmpeg.exe",  # 另一个常见路径
    ]
    
    for path in common_paths:
        try:
            subprocess.run([path, "-version"], capture_output=True, check=True, timeout=5)
            return path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    raise FileNotFoundError("未找到FFmpeg，请确保已正确安装")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SimpleVideoDownloader:
    def __init__(self, output_dir: str = "downloads"):
        """
        初始化简化版YouTube下载器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 查找FFmpeg路径
        try:
            self.ffmpeg_path = find_ffmpeg()
            logger.info(f"找到FFmpeg: {self.ffmpeg_path}")
        except FileNotFoundError as e:
            logger.error(f"FFmpeg未找到: {e}")
            raise
    
    def normalize_srt_file(self, srt_path: Path, max_gap_ms: int = 0) -> None:
        """
        规范化SRT字幕文件：
        - 移除空白/HTML标签
        - 修正重复编号
        - 处理时间轴乱序与重叠（按起始时间排序，必要时微调到不重叠）
        - 合并同一时间段的重复文本
        """
        import re
        from datetime import timedelta

        def parse_ts(ts: str) -> timedelta:
            h, m, rest = ts.split(":")
            s, ms = rest.split(",")
            return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

        def fmt_ts(td: timedelta) -> str:
            total_ms = int(td.total_seconds() * 1000)
            if total_ms < 0:
                total_ms = 0
            h = total_ms // 3600000
            m = (total_ms % 3600000) // 60000
            s = (total_ms % 60000) // 1000
            ms = total_ms % 1000
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        text = srt_path.read_text(encoding="utf-8", errors="ignore")
        # 统一换行
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 简单分段解析
        blocks = re.split(r"\n\s*\n", text.strip())
        items = []
        for blk in blocks:
            lines = [ln.strip() for ln in blk.split("\n") if ln.strip()]
            if len(lines) < 2:
                continue
            # 第一行可能是编号
            idx = None
            time_line = None
            text_lines = []
            if re.match(r"^\d+$", lines[0]):
                if len(lines) >= 2:
                    idx = lines[0]
                    time_line = lines[1]
                    text_lines = lines[2:]
                else:
                    continue
            else:
                time_line = lines[0]
                text_lines = lines[1:]

            if "-->" not in time_line:
                continue
            start_str, end_str = [seg.strip() for seg in time_line.split("-->")]
            # 清理可能混入的样式
            start_str = start_str.split(" ")[0]
            end_clean = end_str.split(" ")[0]
            # 清理文本中的HTML标签与VTT残留
            clean_text_lines = []
            for tl in text_lines:
                tl = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}><c>", "", tl)
                tl = tl.replace("</c>", "")
                tl = re.sub(r"<[^>]+>", "", tl)
                tl = tl.strip()
                if tl:
                    clean_text_lines.append(tl)

            if not clean_text_lines:
                continue

            try:
                start_td = parse_ts(start_str)
                end_td = parse_ts(end_clean)
            except Exception:
                continue

            if end_td <= start_td:
                # 至少保证有10ms时长
                end_td = start_td + timedelta(milliseconds=10)

            items.append((start_td, end_td, " ".join(clean_text_lines)))

        if not items:
            return

        # 按开始时间排序
        items.sort(key=lambda x: (x[0], x[1]))

        # 解决重叠：确保相邻不重叠，并可选加微小缝隙
        from datetime import timedelta as _td
        fixed = []
        for start_td, end_td, text_line in items:
            if fixed:
                prev_start, prev_end, prev_text = fixed[-1]
                if start_td < prev_end:
                    start_td = prev_end
                if end_td <= start_td:
                    end_td = start_td + _td(milliseconds=10)
                # 同时合并同时间且文本相同的片段，避免重复
                if prev_start == start_td and prev_end == end_td and prev_text == text_line:
                    continue
            fixed.append((start_td, end_td, text_line))

        # 重写文件，重排编号
        out_lines = []
        for i, (st, et, tx) in enumerate(fixed, 1):
            out_lines.append(str(i))
            out_lines.append(f"{fmt_ts(st)} --> {fmt_ts(et)}")
            out_lines.append(tx)
            out_lines.append("")

        srt_path.write_text("\n".join(out_lines), encoding="utf-8")

    def apply_offset_to_srt(self, srt_path: Path, offset_ms: int) -> None:
        """对SRT字幕整体施加时间偏移(毫秒，可正可负)，并回写文件。"""
        if offset_ms == 0:
            return
        from datetime import timedelta
        import re

        def parse_ts(ts: str) -> timedelta:
            h, m, rest = ts.split(":")
            s, ms = rest.split(",")
            return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

        def fmt_ts(td: timedelta) -> str:
            total_ms = int(td.total_seconds() * 1000)
            if total_ms < 0:
                total_ms = 0
            h = total_ms // 3600000
            m = (total_ms % 3600000) // 60000
            s = (total_ms % 60000) // 1000
            ms = total_ms % 1000
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        delta = timedelta(milliseconds=offset_ms)
        text = srt_path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
        out_lines = []
        for line in text.split("\n"):
            if "-->" in line:
                try:
                    left, right = [seg.strip() for seg in line.split("-->")]
                    start_td = parse_ts(left.split(" ")[0])
                    end_td = parse_ts(right.split(" ")[0])
                    start_td += delta
                    end_td += delta
                    out_lines.append(f"{fmt_ts(start_td)} --> {fmt_ts(end_td)}")
                except Exception:
                    out_lines.append(line)
            else:
                out_lines.append(line)
        srt_path.write_text("\n".join(out_lines), encoding="utf-8")
        
    def download_video_only(self, url: str, quality: str = "best") -> Dict:
        """只下载视频，不下载字幕"""
        try:
            # 根据质量参数设置下载格式
            if quality == "1080p":
                format_selector = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            elif quality == "720p":
                format_selector = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
            elif quality == "480p":
                format_selector = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
            elif quality == "4k":
                format_selector = "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best[height<=2160]/best"
            elif quality == "worst":
                format_selector = "worst[ext=mp4]/worst"
            else:  # best
                format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"

            ydl_opts = {
                'format': format_selector,
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'writesubtitles': False,
                'writeautomaticsub': False,
                'extract_flat': False,
                'ignoreerrors': True,
                'merge_output_format': 'mp4',
                'postprocessors': [
                    {
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }
                ],
                'prefer_ffmpeg': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown')
                logger.info(f"准备下载视频: {video_title}")
                ydl.download([url])

                # 定位视频文件
                video_files = list(self.output_dir.glob(f"{video_title}.*"))
                video_file = None
                for file in video_files:
                    if file.suffix in ['.mp4', '.mkv', '.avi', '.webm']:
                        video_file = file
                        break

                return {
                    'title': video_title,
                    'id': info.get('id'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'video_file': str(video_file) if video_file else None,
                }
        except Exception as e:
            logger.error(f"仅视频下载失败: {e}")
            raise

    def download_video_with_srt(self, url: str, quality: str = "best", 
                               languages: List[str] = None, embed_subtitles: bool = True,
                               subtitle_offset_ms: int = 0):
        """
        下载YouTube视频和SRT字幕
        
        Args:
            url: YouTube视频URL
            quality: 视频质量 (best, worst, 720p, 480p等)
            languages: 字幕语言列表
            embed_subtitles: 是否将字幕嵌入视频中
            
        Returns:
            包含视频信息的字典
        """
        if languages is None:
            languages = ['en', 'zh-Hans', 'zh', 'ja', 'auto']
            
        try:
            # 根据质量参数设置下载格式
            if quality == "1080p":
                format_selector = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            elif quality == "720p":
                format_selector = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]"
            elif quality == "480p":
                format_selector = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]"
            elif quality == "4k":
                format_selector = "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best[height<=2160]/best"
            elif quality == "worst":
                format_selector = "worst[ext=mp4]/worst"
            else:  # best
                format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best"
                
            # 配置yt-dlp选项
            ydl_opts = {
                'format': format_selector,
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'writesubtitles': True,  # 下载字幕
                'writeautomaticsub': True,  # 下载自动生成的字幕
                'subtitleslangs': languages,  # 字幕语言
                'subtitlesformat': 'srt',  # 强制下载SRT格式
                'extract_flat': False,
                'ignoreerrors': True,  # 忽略字幕下载错误
                'merge_output_format': 'mp4',  # 确保输出为mp4格式
                'postprocessors': [
                    {
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    },
                    {
                        'key': 'FFmpegSubtitlesConvertor',
                        'format': 'srt'
                    }
                ],
                'prefer_ffmpeg': True,  # 优先使用ffmpeg
            }
            
            # 仅当需要嵌入且无需偏移时，使用yt-dlp内置嵌入（更快）
            if embed_subtitles and subtitle_offset_ms == 0:
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegEmbedSubtitle',
                    'format': 'srt'
                })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown')
                video_id = info.get('id')
                
                logger.info(f"准备下载视频: {video_title}")
                logger.info(f"视频质量: {quality}")
                logger.info(f"字幕语言: {languages}")
                if subtitle_offset_ms:
                    logger.info(f"字幕时间偏移: {subtitle_offset_ms} ms")
                
                # 下载视频
                ydl.download([url])
                
                # 检查下载结果
                video_files = list(self.output_dir.glob(f"{video_title}.*"))
                video_file = None
                for file in video_files:
                    if file.suffix in ['.mp4', '.mkv', '.avi', '.webm']:
                        video_file = file
                        break
                        
                # 查找SRT字幕文件
                srt_files = list(self.output_dir.glob("*.srt"))
                
                # 过滤出相关的字幕文件
                filtered_srt_files = []
                for file in srt_files:
                    if (video_title.lower() in file.name.lower() or 
                        video_id in file.name or
                        any(lang in file.name for lang in languages)):
                        filtered_srt_files.append(file)
                
                logger.info("下载完成!")
                if video_file:
                    logger.info(f"视频文件: {video_file.name}")
                    size_mb = video_file.stat().st_size / (1024 * 1024)
                    logger.info(f"视频大小: {size_mb:.1f} MB")
                else:
                    logger.warning("未找到视频文件")
                    
                if filtered_srt_files:
                    logger.info(f"SRT字幕文件 ({len(filtered_srt_files)} 个):")
                    for file in filtered_srt_files:
                        # 规范化字幕，修正时间轴重叠/乱序/重复
                        try:
                            self.normalize_srt_file(file)
                        except Exception as norm_err:
                            logger.warning(f"规范化字幕失败 {file.name}: {norm_err}")
                        # 应用用户偏移
                        try:
                            if subtitle_offset_ms:
                                self.apply_offset_to_srt(file, subtitle_offset_ms)
                        except Exception as off_err:
                            logger.warning(f"应用偏移失败 {file.name}: {off_err}")
                        logger.info(f"  - {file.name}")
                        size_kb = file.stat().st_size / 1024
                        logger.info(f"    大小: {size_kb:.1f} KB")

                    # 如果需要偏移且要嵌入，则手动嵌入（带偏移）
                    if embed_subtitles and subtitle_offset_ms != 0 and video_file:
                        try:
                            shifted = filtered_srt_files[0]
                            offset_sec = subtitle_offset_ms / 1000.0
                            output_path = video_file.with_name(f"{video_file.stem}_sub{video_file.suffix}")
                            cmd = [
                                str(self.ffmpeg_path),
                                '-i', str(video_file),
                                '-itsoffset', f"{offset_sec}", '-i', str(shifted),
                                '-map', '0', '-map', '1',
                                '-c', 'copy', '-c:s', 'mov_text',
                                '-y', str(output_path)
                            ]
                            subprocess.run(cmd, check=True, capture_output=True)
                            try:
                                video_file.unlink(missing_ok=True)
                            except Exception:
                                pass
                            video_file = output_path
                            logger.info(f"已按偏移嵌入字幕: {video_file.name}")
                        except subprocess.CalledProcessError as e:
                            logger.error(f"嵌入偏移字幕失败: {e}")
                else:
                    logger.warning("未找到SRT字幕文件")
                
                # 返回视频信息
                return {
                    'title': video_title,
                    'id': video_id,
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'video_file': str(video_file) if video_file else None,
                    'subtitle_files': [str(f) for f in filtered_srt_files]
                }
                
        except Exception as e:
            logger.error(f"下载失败: {e}")
            raise
    
    def download_srt_only(self, url: str, languages: List[str] = None):
        """只下载SRT字幕文件"""
        if languages is None:
            languages = ['en', 'zh-Hans', 'zh', 'ja', 'auto']
            
        try:
            # 配置SRT字幕下载选项
            ydl_opts = {
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages,
                'skip_download': True,  # 跳过视频下载，只下载字幕
                'ignoreerrors': True,
                'no_warnings': False,
                'subtitlesformat': 'srt',  # 强制下载SRT格式
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt'
                }],
            }
            
            logger.info(f"开始下载SRT字幕，语言: {languages}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown')
                video_id = info.get('id')
                
                logger.info(f"视频标题: {video_title}")
                logger.info(f"视频ID: {video_id}")
                
                # 下载字幕
                ydl.download([url])
                
                # 检查下载的SRT字幕文件
                srt_files = list(self.output_dir.glob("*.srt"))
                
                # 过滤出相关的字幕文件
                filtered_files = []
                for file in srt_files:
                    if (video_title.lower() in file.name.lower() or 
                        video_id in file.name or
                        any(lang in file.name for lang in languages)):
                        filtered_files.append(file)
                
                if filtered_files:
                    logger.info(f"成功下载 {len(filtered_files)} 个SRT字幕文件:")
                    for file in filtered_files:
                        # 规范化字幕，修正时间轴重叠/乱序/重复
                        try:
                            self.normalize_srt_file(file)
                        except Exception as norm_err:
                            logger.warning(f"规范化字幕失败 {file.name}: {norm_err}")
                        # 偏移不在仅字幕模式落盘（只下载时也允许偏移）
                        try:
                            # 在subtitle-only模式下也允许通过 --subtitle-offset-ms 应用偏移
                            # 读取命令行时由上层传参控制；这里直接尝试环境变量传递不可靠，故不处理
                            pass
                        except Exception:
                            pass
                        logger.info(f"  - {file.name}")
                        size_kb = file.stat().st_size / 1024
                        logger.info(f"    大小: {size_kb:.1f} KB")
                    return True
                else:
                    logger.warning("未找到下载的SRT字幕文件")
                    return False
                    
        except Exception as e:
            logger.error(f"SRT字幕下载失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="简化版YouTube视频下载工具")
    parser.add_argument("url", help="YouTube视频URL")
    parser.add_argument("-q", "--quality", default="best",
                       help="视频质量 (best, worst, 720p, 480p, 1080p, 4k)")
    parser.add_argument("--subtitle-only", action="store_true",
                       help="只下载字幕，不下载视频")
    parser.add_argument("--video-only", action="store_true",
                       help="只下载视频，不下载字幕")
    parser.add_argument("--no-embed", action="store_true",
                       help="不将字幕嵌入视频中")
    parser.add_argument("--languages", nargs="+", 
                       default=['en', 'zh-Hans', 'zh', 'ja', 'auto'],
                       help="字幕语言列表")
    parser.add_argument("--subtitle-offset-ms", type=int, default=0,
                        help="字幕整体时间偏移(毫秒, 可正可负)。仅嵌入时生效。")
    
    args = parser.parse_args()
    
    downloader = SimpleVideoDownloader()
    
    try:
        if args.video_only:
            result = downloader.download_video_only(args.url, args.quality)
            if result and result.get('video_file'):
                print("✅ 已下载视频(不含字幕)")
                print(f"视频文件: {result['video_file']}")
            else:
                print("❌ 视频下载失败")
        elif args.subtitle_only:
            # 只下载字幕
            success = downloader.download_srt_only(args.url, args.languages)
            # 如果用户设置了偏移，也对刚下载的字幕文件应用偏移
            if success and args.subtitle_offset_ms:
                # 尝试找到刚下载的目标标题并对匹配的srt全部偏移
                try:
                    # 粗略获取标题
                    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                        info = ydl.extract_info(args.url, download=False)
                        title = info.get('title', '')
                        vid = info.get('id', '')
                    outdir = Path('downloads')
                    for f in outdir.glob('*.srt'):
                        name_lower = f.name.lower()
                        if (title and title.lower() in name_lower) or (vid and vid in f.name):
                            try:
                                downloader.apply_offset_to_srt(f, args.subtitle_offset_ms)
                                print(f"已对 {f.name} 应用偏移 {args.subtitle_offset_ms}ms")
                            except Exception:
                                pass
                except Exception:
                    pass
            if success:
                print("✅ SRT字幕下载完成")
            else:
                print("❌ SRT字幕下载失败")
        else:
            # 下载视频和字幕
            embed_subtitles = not args.no_embed
            result = downloader.download_video_with_srt(
                args.url, args.quality, args.languages, embed_subtitles,
                subtitle_offset_ms=args.subtitle_offset_ms
            )
            if result:
                print("✅ 视频和字幕下载完成")
                if result['video_file']:
                    print(f"视频文件: {result['video_file']}")
                if result['subtitle_files']:
                    print(f"字幕文件: {', '.join(result['subtitle_files'])}")
            else:
                print("❌ 下载失败")
                
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main() 