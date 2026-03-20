
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版YouTube视频下载工具
先实现基本的下载和字幕功能，后续可以添加翻译
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import subprocess
from typing import Optional, List, Dict

import yt_dlp
import whisper
from datetime import datetime
import re

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
        logging.FileHandler('youtube_downloader.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SimpleYouTubeDownloader:
    def __init__(self, output_dir: str = "downloads"):
        """
        初始化简化版YouTube下载器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.whisper_model = None
        
        # 查找FFmpeg路径
        try:
            self.ffmpeg_path = find_ffmpeg()
            logger.info(f"找到FFmpeg: {self.ffmpeg_path}")
        except FileNotFoundError as e:
            logger.error(f"FFmpeg未找到: {e}")
            raise
        
    def load_whisper_model(self, model_size: str = "base"):
        """
        加载Whisper模型用于语音识别
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large)
        """
        try:
            logger.info(f"正在加载Whisper模型: {model_size}")
            self.whisper_model = whisper.load_model(model_size)
            logger.info("Whisper模型加载成功")
        except Exception as e:
            logger.error(f"加载Whisper模型失败: {e}")
            
    def download_video(self, url: str, quality: str = "best") -> Dict:
        """
        下载YouTube视频
        
        Args:
            url: YouTube视频URL
            quality: 视频质量 (best, worst, 720p, 480p等)
            
        Returns:
            包含视频信息的字典
        """
        try:
            # 配置yt-dlp选项
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
                'writesubtitles': True,  # 下载字幕
                'writeautomaticsub': True,  # 下载自动生成的字幕
                'subtitleslangs': ['zh-Hans', 'zh', 'en', 'auto'],  # 字幕语言
                'extract_flat': False,
                'ignoreerrors': True,  # 忽略字幕下载错误
                'merge_output_format': 'mp4',  # 确保输出为mp4格式
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'prefer_ffmpeg': True,  # 优先使用ffmpeg
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown')
                logger.info(f"准备下载视频: {video_title}")
                
                # 下载视频
                ydl.download([url])
                
                # 返回视频信息
                return {
                    'title': video_title,
                    'id': info.get('id'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date')
                }
                
        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            raise
            
    def extract_audio_for_whisper(self, video_path: str) -> str:
        """
        从视频中提取音频用于Whisper识别
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            音频文件路径
        """
        try:
            video_path = Path(video_path)
            audio_path = video_path.with_suffix('.wav')
            
            # 使用ffmpeg提取音频
            cmd = [
                self.ffmpeg_path, '-i', str(video_path),
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                str(audio_path), '-y'
            ]
            
            logger.info("正在提取音频...")
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"音频提取完成: {audio_path}")
            
            return str(audio_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"音频提取失败: {e}")
            raise
            
    def generate_subtitles_with_whisper(self, audio_path: str) -> str:
        """
        使用Whisper生成字幕
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            字幕文件路径
        """
        try:
            if self.whisper_model is None:
                self.load_whisper_model()
                
            logger.info("正在使用Whisper生成字幕...")
            result = self.whisper_model.transcribe(audio_path)
            
            # 生成SRT格式字幕
            audio_path = Path(audio_path)
            srt_path = audio_path.with_suffix('.srt')
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result['segments'], 1):
                    start_time = self.format_timestamp(segment['start'])
                    end_time = self.format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                    
            logger.info(f"字幕生成完成: {srt_path}")
            return str(srt_path)
            
        except Exception as e:
            logger.error(f"字幕生成失败: {e}")
            raise
            
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        将秒数转换为SRT时间格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT格式时间戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
    def embed_subtitles_to_video(self, video_path: str, subtitle_path: str) -> str:
        """
        将字幕嵌入到视频中
        
        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径
            
        Returns:
            带字幕视频文件路径
        """
        try:
            video_path = Path(video_path)
            subtitle_path = Path(subtitle_path)
            output_path = video_path.with_name(f"{video_path.stem}_with_subtitles{video_path.suffix}")
            
            logger.info("正在将字幕嵌入视频...")
            
            # 使用ffmpeg嵌入字幕
            cmd = [
                self.ffmpeg_path, '-i', str(video_path),
                '-vf', f"subtitles='{subtitle_path}'",
                '-c:a', 'copy',
                str(output_path), '-y'
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"字幕嵌入完成: {output_path}")
            
            return str(output_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"字幕嵌入失败: {e}")
            raise
            
    def process_video(self, url: str, quality: str = "best", embed_subtitles: bool = True):
        """
        处理视频的完整流程
        
        Args:
            url: YouTube视频URL
            quality: 视频质量
            embed_subtitles: 是否将字幕嵌入视频
        """
        try:
            logger.info(f"开始处理视频: {url}")
            
            # 1. 下载视频
            video_info = self.download_video(url, quality)
            video_title = video_info['title']
            
            # 查找下载的视频文件
            video_files = list(self.output_dir.glob(f"{video_title}.*"))
            video_file = None
            for file in video_files:
                if file.suffix in ['.mp4', '.mkv', '.avi', '.webm']:
                    video_file = file
                    break
                    
            if not video_file:
                raise FileNotFoundError("找不到下载的视频文件")
                
            logger.info(f"视频文件: {video_file}")
            
            # 2. 查找现有字幕文件
            subtitle_files = list(self.output_dir.glob(f"{video_title}*.srt"))
            original_subtitle = None
            
            if subtitle_files:
                # 优先使用中文字幕，然后是英文字幕
                for sub_file in subtitle_files:
                    if 'zh' in sub_file.stem.lower():
                        original_subtitle = sub_file
                        break
                    elif 'en' in sub_file.stem.lower():
                        original_subtitle = sub_file
                        
                if not original_subtitle:
                    original_subtitle = subtitle_files[0]
                    
            # 3. 如果没有字幕，使用Whisper生成
            if not original_subtitle:
                logger.info("未找到字幕文件，使用Whisper生成字幕...")
                audio_file = self.extract_audio_for_whisper(str(video_file))
                original_subtitle = self.generate_subtitles_with_whisper(audio_file)
                
                # 清理临时音频文件
                os.remove(audio_file)
                
            logger.info(f"使用字幕文件: {original_subtitle}")
            
            # 4. 嵌入字幕到视频（可选）
            if embed_subtitles:
                final_video = self.embed_subtitles_to_video(str(video_file), str(original_subtitle))
                logger.info(f"最终视频文件: {final_video}")
            else:
                logger.info(f"字幕已保存: {original_subtitle}")
                
            logger.info("视频处理完成！")
            
        except Exception as e:
            logger.error(f"视频处理失败: {e}")
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="简化版YouTube视频下载工具")
    parser.add_argument("url", help="YouTube视频URL")
    parser.add_argument("-q", "--quality", default="best", 
                       help="视频质量 (默认: best)")
    parser.add_argument("-o", "--output", default="downloads", 
                       help="输出目录 (默认: downloads)")
    parser.add_argument("--no-embed", action="store_true", 
                       help="不将字幕嵌入视频")
    parser.add_argument("--whisper-model", default="base", 
                       help="Whisper模型大小 (默认: base)")
    
    args = parser.parse_args()
    
    try:
        # 创建下载器实例
        downloader = SimpleYouTubeDownloader(args.output)
        
        # 预加载Whisper模型
        downloader.load_whisper_model(args.whisper_model)
        
        # 处理视频
        downloader.process_video(
            url=args.url,
            quality=args.quality,
            embed_subtitles=not args.no_embed
        )
        
        print("处理完成！")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 