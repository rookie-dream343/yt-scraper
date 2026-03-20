@echo off
chcp 65001 > nul
title YouTube视频下载工具
color 0A

echo ================================
echo     YouTube视频下载工具
echo ================================
echo.

:main
echo 请输入YouTube视频链接:
echo 例如: https://www.youtube.com/watch?v=dQw4w9WgXcQ
echo.
set /p video_url="视频链接: "

if "%video_url%"=="" (
    echo 请输入有效的视频链接！
    echo.
    goto main
)

echo.
echo 选择下载模式:
echo 1. 视频+字幕
echo 2. 仅下载视频
echo 3. 仅下载字幕
echo.
set /p mode_choice="请选择 (1-3, 默认1): "

set extra_args=
if "%mode_choice%"=="2" set extra_args=--video-only
if "%mode_choice%"=="3" set extra_args=--subtitle-only

echo.
echo 选择视频质量:
echo 1. 4K超高清 (2160p) - 最高画质
echo 2. 1080p高清 - 推荐选择  
echo 3. 720p高清
echo 4. 480p标清
echo 5. 最低质量 (节省空间)
echo 6. 自动最佳 (让程序选择)
echo.
set /p quality_choice="请选择 (1-6, 默认2): "

if "%quality_choice%"=="1" set quality=4k
if "%quality_choice%"=="2" set quality=1080p
if "%quality_choice%"=="3" set quality=720p
if "%quality_choice%"=="4" set quality=480p
if "%quality_choice%"=="5" set quality=worst
if "%quality_choice%"=="6" set quality=best
if "%quality_choice%"=="" set quality=1080p

echo.
echo 选择字幕语言:
echo 1. 英语 (en)
echo 2. 简体中文 (zh-Hans)
echo 3. 繁体中文 (zh)
echo 4. 日语 (ja)
echo 5. 自动字幕 (auto)
echo 6. 所有语言
echo.
set /p language_choice="请选择 (1-6, 默认6): "

if "%language_choice%"=="1" set languages=en
if "%language_choice%"=="2" set languages=zh-Hans
if "%language_choice%"=="3" set languages=zh
if "%language_choice%"=="4" set languages=ja
if "%language_choice%"=="5" set languages=auto
if "%language_choice%"=="6" set languages=en zh-Hans zh ja auto
if "%language_choice%"=="" set languages=en zh-Hans zh ja auto

echo.
echo 是否嵌入字幕到视频中？
echo 1. 是 (推荐)
echo 2. 否 (只生成字幕文件)
echo.
set /p subtitle_choice="请选择 (1-2, 默认1): "

set embed_option=
if "%subtitle_choice%"=="2" set embed_option=--no-embed

rem 仅当不是“仅视频”时，允许设置字幕时间偏移
if not "%mode_choice%"=="2" (
  echo.
  echo 可选：设置字幕整体時間偏移(毫秒，可為負，直接回車不偏移)
  set /p offset_ms="字幕偏移(ms): "
  if not "%offset_ms%"=="" set extra_args=%extra_args% --subtitle-offset-ms %offset_ms%
)

echo.
echo 开始下载...
echo 视频链接: %video_url%
echo 视频质量: %quality%
echo.

python simple_video_downloader.py "%video_url%" -q %quality% --languages %languages% %embed_option% %extra_args%

echo.
echo ================================
echo 下载完成！文件保存在 downloads 文件夹中
echo ================================
echo.

:ask_continue
echo 是否继续下载其他视频？(y/n)
set /p continue_choice="请选择: "

if /i "%continue_choice%"=="y" (
    echo.
    goto main
)
if /i "%continue_choice%"=="yes" (
    echo.
    goto main
)

echo 感谢使用！
pause 