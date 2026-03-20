# dify_worker.py (最终健壮版)
# 修正了ffmpeg命令中的拼写错误，并增强了日志记录

from flask import Flask, request, jsonify
from threading import Thread
import os
import logging
import sys
from pathlib import Path
import subprocess
import yt_dlp
from deep_translator import GoogleTranslator
import whisper
import re
import traceback

# --- 日志设置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('dify_worker.log', encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- FFmpeg路径检测 ---
def find_ffmpeg() -> str:
    common_paths = ["ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", "C:\\FFmpeg\\bin\\ffmpeg.exe"]
    for path in common_paths:
        try:
            subprocess.run([path, "-version"], capture_output=True, check=True, timeout=5)
            logger.info(f"成功找到FFmpeg: {path}")
            return path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    raise FileNotFoundError("错误：未找到FFmpeg。请使用 'winget install Gyan.FFmpeg' 安装。")

# --- 核心处理类 ---
class YouTubeDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.whisper_model = None
        self.ffmpeg_path = find_ffmpeg()

    def load_whisper_model(self, model_size: str = "base"):
        if self.whisper_model is None:
            try:
                logger.info(f"正在加载Whisper AI模型: '{model_size}'...")
                self.whisper_model = whisper.load_model(model_size)
                logger.info(f"Whisper AI模型 '{model_size}' 加载成功。")
            except Exception as e:
                logger.error(f"加载Whisper模型失败: {e}")
                raise

    def download_video_and_subs(self, url: str, quality: str) -> dict:
        logger.info("步骤 1/5: 开始下载视频和字幕...")
        ydl_opts = {
            'format': f'bestvideo[height<={quality.replace("p","")}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'zh-Hans'],
            'noplaylist': True,
            'postprocessors': [{'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'}],
            'merge_output_format': 'mp4',
            'ignoreerrors': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            logger.info(f"视频 '{info.get('title', '未知标题')}' 下载完成。")
            return info

    def get_subtitle_path(self, info: dict) -> str | None:
        if 'requested_subtitles' in info and info['requested_subtitles']:
            for lang in ['en', 'zh-Hans']:
                if lang in info['requested_subtitles']:
                    sub_info = info['requested_subtitles'][lang]
                    if sub_info.get('filepath') and sub_info['filepath'].endswith('.srt'):
                        srt_path = Path(sub_info['filepath'])
                        if srt_path.exists():
                            logger.info(f"成功找到已下载的 '{lang}' 字幕文件: {srt_path}")
                            return str(srt_path)
        
        base_filename = yt_dlp.utils.sanitize_filename(info.get('title'))
        for lang_code in ['.en.srt', '.zh-Hans.srt', '.srt']:
             for path in self.output_dir.glob(f"{base_filename}*{lang_code}"):
                logger.info(f"通过文件名匹配找到字幕: {path}")
                return str(path)
                
        logger.warning("警告：未找到任何YouTube提供的字幕文件。")
        return None

    def generate_subtitles_with_whisper(self, video_path: str, model_size: str) -> str:
        logger.info("步骤 2/5: 未找到现有字幕，启动Whisper AI生成...")
        self.load_whisper_model(model_size)
        result = self.whisper_model.transcribe(video_path, verbose=False)
        srt_path = Path(video_path).with_suffix('.ai.srt')
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result['segments'], 1):
                start = int(segment['start'] * 1000)
                end = int(segment['end'] * 1000)
                text = segment['text'].strip()
                f.write(f"{i}\n{self.format_timestamp(start)} --> {self.format_timestamp(end)}\n{text}\n\n")
        logger.info(f"Whisper AI字幕生成成功: {srt_path}")
        return str(srt_path)

    def translate_subtitles(self, srt_path: str, target_lang: str) -> str:
        logger.info(f"步骤 3/5: 开始将字幕翻译为 '{target_lang}'...")
        srt_path_obj = Path(srt_path)
        translated_path = srt_path_obj.with_name(f"{srt_path_obj.stem}_translated_{target_lang}.srt")

        with open(srt_path, 'r', encoding='utf-8') as f_in, open(translated_path, 'w', encoding='utf-8') as f_out:
            lines = f_in.readlines()
            text_to_translate = [line for line in lines if not line.strip().isdigit() and '-->' not in line and line.strip()]
            
            if not text_to_translate:
                logger.warning("字幕文件中没有需要翻译的文本。")
                f_out.writelines(lines) # 如果没有文本，直接复制原文件
                return str(translated_path)

            try:
                translated_texts = GoogleTranslator(source='auto', target=target_lang).translate_batch(text_to_translate)
                
                text_idx = 0
                for line in lines:
                    if not line.strip().isdigit() and '-->' not in line and line.strip():
                        if text_idx < len(translated_texts):
                            f_out.write(translated_texts[text_idx] + '\n')
                            text_idx += 1
                    else:
                        f_out.write(line)
            except Exception as e:
                logger.error(f"批量翻译失败: {e}，将复制原始字幕。")
                f_in.seek(0)
                f_out.writelines(f_in.readlines())
        
        logger.info(f"字幕翻译成功: {translated_path}")
        return str(translated_path)

    def embed_subtitles_to_video(self, video_path: str, subtitle_path: str) -> str:
        logger.info("步骤 4/5: 开始将字幕嵌入视频...")
        video_path_obj = Path(video_path)
        output_path = video_path_obj.with_name(f"{video_path_obj.stem}_with_subs.mp4")
        subtitle_escaped_path = str(Path(subtitle_path)).replace('\\', '/')
        
        # --- 这是修正后的命令 ---
        cmd = [
            self.ffmpeg_path, '-i', str(video_path),
            '-vf', f"subtitles='{subtitle_escaped_path}'",
            '-c:a', 'copy', '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            str(output_path), '-y'
        ]
        # -------------------------
        
        try:
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            logger.info(f"字幕嵌入成功: {output_path}")
            return str(output_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"字幕嵌入失败。FFmpeg错误日志:\n--- FFMPEG STDERR ---\n{e.stderr}\n--- END FFMPEG STDERR ---")
            raise

    @staticmethod
    def format_timestamp(milliseconds: int) -> str:
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

# --- Flask App ---
app = Flask(__name__)
tasks = {}

def process_video_task(url, task_id):
    logger.info(f"✅ 后台任务 '{task_id}' 已启动，正在处理URL: {url}")
    try:
        output_dir = "downloads"
        downloader = YouTubeDownloader(output_dir)
        
        info = downloader.download_video_and_subs(url, "720p")
        
        video_filename = yt_dlp.utils.sanitize_filename(info['title'])
        video_path = next(Path(output_dir).glob(f"{video_filename}.*mp4"), None)
        if not video_path:
             raise FileNotFoundError(f"找不到下载的视频文件: {video_filename}")

        subtitle_path = downloader.get_subtitle_path(info)
        if not subtitle_path:
            subtitle_path = downloader.generate_subtitles_with_whisper(str(video_path), "base")
            
        translated_subtitle_path = downloader.translate_subtitles(subtitle_path, "zh-cn")
        final_video_path = downloader.embed_subtitles_to_video(str(video_path), translated_subtitle_path)
        
        final_file_info = f"处理成功！最终文件位于: {final_video_path}"
        tasks[task_id] = {"status": "success", "result": final_file_info}
        logger.info(f"✅ 任务 '{task_id}' 处理成功。")

    except Exception:
        error_details = traceback.format_exc()
        logger.error(f"❌ 任务 '{task_id}' 失败! 详细错误:\n{error_details}")
        tasks[task_id] = {"status": "error", "result": error_details}

@app.route('/process_video', methods=['POST'])
def handle_process_video():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "请求体中缺少 'url' 参数"}), 400

        video_url = data['url']
        task_id = Path(video_url).stem
        
        logger.info(f"收到Dify的请求，任务ID: '{task_id}', URL: {video_url}")
        
        tasks[task_id] = {"status": "processing", "result": "任务已开始..."}
        thread = Thread(target=process_video_task, args=(video_url, task_id))
        thread.start()
        
        return jsonify({"message": "任务已在后台启动", "task_id": task_id}), 200
    except Exception:
        # 捕获主线程中的任何意外错误
        error_details = traceback.format_exc()
        logger.error(f"❌ 处理Dify请求时发生严重错误:\n{error_details}")
        return jsonify({"error": "服务器内部错误，请检查后端日志。"}), 500

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    logger.info("启动Dify工作流后端API服务...")
    app.run(host='0.0.0.0', port=5000)
