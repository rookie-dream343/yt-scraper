@echo off
chcp 65001 >nul
title 增强字幕下载工具

echo ========================================
echo 增强字幕下载工具
echo ========================================
echo.

:menu
echo 请选择操作:
echo 1. 列出可用字幕语言
echo 2. 只下载字幕文件
echo 3. 下载视频和字幕
echo 4. 转换VTT文件为SRT
echo 5. 退出
echo.
set /p choice=请输入选择 (1-5): 

if "%choice%"=="1" goto list_languages
if "%choice%"=="2" goto subtitle_only
if "%choice%"=="3" goto video_subtitle
if "%choice%"=="4" goto convert_vtt
if "%choice%"=="5" goto exit
echo 无效选择，请重新输入
goto menu

:list_languages
echo.
set /p url=请输入YouTube视频URL: 
python enhanced_subtitle_downloader.py "%url%" --list-languages
echo.
pause
goto menu

:subtitle_only
echo.
set /p url=请输入YouTube视频URL: 
echo 可选字幕语言: en, zh-Hans, zh, auto
set /p languages=请输入字幕语言 (用空格分隔，直接回车使用默认): 
if "%languages%"=="" (
    python enhanced_subtitle_downloader.py "%url%" --subtitle-only
) else (
    python enhanced_subtitle_downloader.py "%url%" --subtitle-only --languages %languages%
)
echo.
pause
goto menu

:video_subtitle
echo.
set /p url=请输入YouTube视频URL: 
echo 视频质量选项: best, worst, 720p, 480p, 360p
set /p quality=请输入视频质量 (直接回车使用best): 
if "%quality%"=="" set quality=best
echo 可选字幕语言: en, zh-Hans, zh, auto
set /p languages=请输入字幕语言 (用空格分隔，直接回车使用默认): 
if "%languages%"=="" (
    python enhanced_subtitle_downloader.py "%url%" --quality %quality%
) else (
    python enhanced_subtitle_downloader.py "%url%" --quality %quality% --languages %languages%
)
echo.
pause
goto menu

:convert_vtt
echo.
echo 转换VTT文件为SRT格式...
python enhanced_subtitle_downloader.py --convert-vtt
echo.
pause
goto menu

:exit
echo 感谢使用！
pause 