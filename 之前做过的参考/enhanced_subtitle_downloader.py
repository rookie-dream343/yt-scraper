#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强字幕下载工具
专门解决YouTube字幕下载失败的问题
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import subprocess
from typing import Optional, List, Dict
import re

import yt_dlp

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subtitle_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnhancedSubtitleDownloader:
    def __init__(self, output_dir: str = "downloads"):
        """初始化字幕下载器"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def get_available_subtitles(self, url: str) -> Dict:
        """获取视频可用的字幕列表"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # 获取字幕信息
                subtitles = info.get('subtitles', {})
                auto_subtitles = info.get('automatic_captions', {})
                
                logger.info(f"找到 {len(subtitles)} 种手动字幕")
                logger.info(f"找到 {len(auto_subtitles)} 种自动字幕")
                
                return {
                    'manual': subtitles,
                    'auto': auto_subtitles,
                    'title': info.get('title', 'Unknown'),
                    'id': info.get('id')
                }
                
        except Exception as e:
            logger.error(f"获取字幕信息失败: {e}")
            return {}
    
    def download_subtitles_only(self, url: str, languages: List[str] = None):
        """只下载字幕文件"""
        if languages is None:
            languages = ['en', 'zh-Hans', 'zh', 'auto']
            
        try:
            # 获取字幕信息
            subtitle_info = self.get_available_subtitles(url)
            if not subtitle_info:
                logger.error("无法获取字幕信息")
                return False
                
            video_title = subtitle_info['title']
            video_id = subtitle_info['id']
            
            logger.info(f"视频标题: {video_title}")
            logger.info(f"视频ID: {video_id}")
            
            # 配置字幕下载选项
            ydl_opts = {
                'outtmpl': str(self.output_dir / f'{video_title}.%(ext)s'),
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages,
                'skip_download': True,  # 跳过视频下载，只下载字幕
                'ignoreerrors': True,
                'no_warnings': False,
                'subtitlesformat': 'srt',  # 优先下载SRT格式
            }
            
            logger.info(f"开始下载字幕，语言: {languages}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # 检查下载的字幕文件
            # 使用更宽泛的搜索模式，因为yt-dlp可能会修改文件名
            subtitle_files = list(self.output_dir.glob("*.srt"))
            subtitle_files.extend(list(self.output_dir.glob("*.vtt")))
            
            # 过滤出包含视频标题或视频ID的文件
            filtered_files = []
            for file in subtitle_files:
                if (video_title.lower() in file.name.lower() or 
                    video_id in file.name or
                    any(lang in file.name for lang in languages)):
                    filtered_files.append(file)
            
            if filtered_files:
                logger.info(f"成功下载 {len(filtered_files)} 个字幕文件:")
                for file in filtered_files:
                    logger.info(f"  - {file.name}")
                return True
            else:
                logger.warning("未找到下载的字幕文件")
                # 列出所有文件以便调试
                all_files = list(self.output_dir.glob("*"))
                if all_files:
                    logger.info("下载目录中的所有文件:")
                    for file in all_files:
                        logger.info(f"  - {file.name}")
                return False
                
        except Exception as e:
            logger.error(f"字幕下载失败: {e}")
            return False
    
    def download_video_with_subtitles(self, url: str, quality: str = "best", 
                                     languages: List[str] = None):
        """下载视频和字幕"""
        if languages is None:
            languages = ['en', 'zh-Hans', 'zh', 'auto']
            
        try:
            # 获取视频信息
            subtitle_info = self.get_available_subtitles(url)
            if not subtitle_info:
                logger.error("无法获取视频信息")
                return False
                
            video_title = subtitle_info['title']
            video_id = subtitle_info['id']
            
            # 配置下载选项
            ydl_opts = {
                'format': quality,
                'outtmpl': str(self.output_dir / f'{video_title}.%(ext)s'),
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': languages,
                'subtitlesformat': 'srt',  # 优先下载SRT格式
                'ignoreerrors': True,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'prefer_ffmpeg': True,
            }
            
            logger.info(f"开始下载视频和字幕...")
            logger.info(f"视频质量: {quality}")
            logger.info(f"字幕语言: {languages}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # 检查下载结果
            video_files = list(self.output_dir.glob(f"{video_title}.*"))
            video_file = None
            for file in video_files:
                if file.suffix in ['.mp4', '.mkv', '.avi', '.webm']:
                    video_file = file
                    break
                    
            # 使用更宽泛的搜索模式查找字幕文件
            subtitle_files = list(self.output_dir.glob("*.srt"))
            subtitle_files.extend(list(self.output_dir.glob("*.vtt")))
            
            # 过滤出相关的字幕文件
            filtered_subtitle_files = []
            for file in subtitle_files:
                if (video_title.lower() in file.name.lower() or 
                    video_id in file.name or
                    any(lang in file.name for lang in languages)):
                    filtered_subtitle_files.append(file)
            
            logger.info("下载完成!")
            if video_file:
                logger.info(f"视频文件: {video_file.name}")
            else:
                logger.warning("未找到视频文件")
                
            if filtered_subtitle_files:
                logger.info(f"字幕文件 ({len(filtered_subtitle_files)} 个):")
                for file in filtered_subtitle_files:
                    logger.info(f"  - {file.name}")
            else:
                logger.warning("未找到字幕文件")
                
            return True
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
    
    def list_subtitle_languages(self, url: str):
        """列出所有可用的字幕语言"""
        try:
            subtitle_info = self.get_available_subtitles(url)
            if not subtitle_info:
                return
                
            print(f"\n视频: {subtitle_info['title']}")
            print("=" * 50)
            
            # 手动字幕
            manual_subtitles = subtitle_info['manual']
            if manual_subtitles:
                print("\n📝 手动字幕:")
                for lang, formats in manual_subtitles.items():
                    print(f"  {lang}: {list(formats.keys())}")
            else:
                print("\n❌ 没有手动字幕")
                
            # 自动字幕
            auto_subtitles = subtitle_info['auto']
            if auto_subtitles:
                print("\n🤖 自动字幕:")
                for lang, formats in auto_subtitles.items():
                    print(f"  {lang}: {list(formats.keys())}")
            else:
                print("\n❌ 没有自动字幕")
                
        except Exception as e:
            logger.error(f"获取字幕语言失败: {e}")
    
    def convert_vtt_to_srt(self, vtt_file: Path):
        """将VTT字幕转换为SRT格式"""
        try:
            srt_file = vtt_file.with_suffix('.srt')
            
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 改进的VTT到SRT转换
            lines = content.split('\n')
            srt_lines = []
            subtitle_index = 1
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # 跳过WEBVTT头部
                if line == 'WEBVTT' or line.startswith('NOTE'):
                    i += 1
                    continue
                    
                # 查找时间线
                if '-->' in line:
                    # 提取时间信息，移除样式信息
                    time_parts = line.split('-->')
                    if len(time_parts) == 2:
                        start_time = time_parts[0].strip()
                        end_time = time_parts[1].strip()
                        
                        # 移除样式信息
                        if ' ' in end_time:
                            end_time = end_time.split(' ')[0]
                        
                        # 转换时间格式
                        time_line = f"{start_time.replace('.', ',')} --> {end_time.replace('.', ',')}"
                        
                        srt_lines.append(str(subtitle_index))
                        srt_lines.append(time_line)
                        subtitle_index += 1
                        i += 1
                        
                        # 收集字幕文本
                        text_lines = []
                        while i < len(lines) and lines[i].strip() != '':
                            text_line = lines[i].strip()
                            
                            # 清理VTT标记
                            # 移除时间标记 <00:00:03.280><c>text</c>
                            import re
                            text_line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}><c>', '', text_line)
                            text_line = re.sub(r'</c>', '', text_line)
                            
                            # 移除其他VTT标记
                            text_line = re.sub(r'<[^>]+>', '', text_line)
                            
                            if text_line.strip():
                                text_lines.append(text_line.strip())
                            i += 1
                        
                        if text_lines:
                            # 合并重复的文本行
                            merged_text = ' '.join(text_lines)
                            # 移除重复的空格
                            merged_text = ' '.join(merged_text.split())
                            srt_lines.append(merged_text)
                            srt_lines.append('')
                    else:
                        i += 1
                else:
                    i += 1
            
            # 保存SRT文件
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
                
            logger.info(f"VTT转换完成: {srt_file}")
            return str(srt_file)
            
        except Exception as e:
            logger.error(f"VTT转换失败: {e}")
            return None
    
    def process_downloads(self):
        """处理已下载的文件，转换VTT为SRT"""
        logger.info("处理已下载的字幕文件...")
        
        vtt_files = list(self.output_dir.glob("*.vtt"))
        converted_count = 0
        
        for vtt_file in vtt_files:
            try:
                srt_file = self.convert_vtt_to_srt(vtt_file)
                if srt_file:
                    converted_count += 1
            except Exception as e:
                logger.error(f"转换 {vtt_file.name} 失败: {e}")
                
        logger.info(f"转换完成: {converted_count} 个VTT文件")

def main():
    parser = argparse.ArgumentParser(description="增强字幕下载工具")
    parser.add_argument("url", nargs="?", help="YouTube视频URL")
    parser.add_argument("--subtitle-only", action="store_true", 
                       help="只下载字幕，不下载视频")
    parser.add_argument("--list-languages", action="store_true",
                       help="列出可用的字幕语言")
    parser.add_argument("--quality", default="best",
                       help="视频质量 (默认: best)")
    parser.add_argument("--languages", nargs="+", 
                       default=['en', 'zh-Hans', 'zh', 'auto'],
                       help="字幕语言列表")
    parser.add_argument("--convert-vtt", action="store_true",
                       help="转换VTT文件为SRT格式")
    
    args = parser.parse_args()
    
    downloader = EnhancedSubtitleDownloader()
    
    try:
        # 转换VTT文件
        if args.convert_vtt:
            downloader.process_downloads()
            return  # 如果是转换操作，直接返回，不执行其他操作
            
        # 检查URL是否提供
        if not args.url:
            print("❌ 错误: 请提供YouTube视频URL")
            return
            
        if args.list_languages:
            # 列出可用字幕语言
            downloader.list_subtitle_languages(args.url)
            
        elif args.subtitle_only:
            # 只下载字幕
            success = downloader.download_subtitles_only(args.url, args.languages)
            if success:
                print("✅ 字幕下载完成")
            else:
                print("❌ 字幕下载失败")
                
        else:
            # 下载视频和字幕
            success = downloader.download_video_with_subtitles(
                args.url, args.quality, args.languages
            )
            if success:
                print("✅ 视频和字幕下载完成")
            else:
                print("❌ 下载失败")
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main() 